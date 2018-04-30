# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__
from StringIO import StringIO
import json
import datetime
import time
import calendar
import urllib
import math
import xml.etree.cElementTree as et
from dateutil.parser import parse as dateparser

from django.views.decorators.cache import cache_page
from django.http import HttpResponse, HttpResponseNotAllowed, Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect
from django.template import RequestContext
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.urlresolvers import reverse
import pytz
import iso8601

from geocamUtil.TimeUtil import utcToTimeZone, timeZoneToUtc
from geocamUtil import geomath
from geocamUtil.loader import LazyGetModelByName
from geocamUtil.modelJson import modelsToJson, modelToJson
from geocamUtil.datetimeJsonEncoder import DatetimeJsonEncoder
from geocamUtil.KmlUtil import wrapKmlDjango, djangoResponse, wrapKml, buildNetworkLink
from geocamUtil.loader import getClassByName
from forms import ImportTrackForm

from geocamTrack.models import ResourcePosition, PastResourcePosition, Centroid, \
    AbstractResourcePositionWithHeading
import geocamTrack.models
from geocamTrack.avatar import renderAvatar
from django.conf import settings
import traceback
from trackUtil import getDatesWithPositionData
from xgds_core.util import insertIntoPath

if False and settings.XGDS_SSE:
    from sse_wrapper.events import send_event

TRACK_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_TRACK_MODEL)
POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_POSITION_MODEL)
PAST_POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)
RECENT_TIME_FUNCTION = getClassByName(settings.GEOCAM_TRACK_RECENT_TIME_FUNCTION)
VEHICLE_MODEL = LazyGetModelByName(settings.XGDS_CORE_VEHICLE_MODEL)


class ExampleError(Exception):
    pass


def getIndex(request):
    return render(request,
                  'trackingIndex.html',
                  {}
                  )


def getGeoJsonDict():
    return dict(type='FeatureCollection',
                crs=dict(type='name',
                         properties=dict(name='urn:ogc:def:crs:OGC:1.3:CRS84')),
                features=[r.getGeoJson() for r in POSITION_MODEL.get().objects.all()])


def getGeoJsonDictWithErrorHandling():
    try:
        result = getGeoJsonDict()
    except ExampleError:
        return dict(error=dict(code=-32099,
                               message='This is how we would signal an err'))
    return dict(result=result)


def getKmlNetworkLink(request, name=settings.GEOCAM_TRACK_FEED_NAME, interval=5):
    url = request.build_absolute_uri(settings.SCRIPT_NAME + 'geocamTrack/rest/latest.kml')
    return djangoResponse(buildNetworkLink(url, name, interval))


def getKmlTrack(name, positions):
    text = '<Document>\n'
    text += '  <name>%s</name>\n' % name
    for i, pos in enumerate(positions):
        text += pos.getKml(i)
    text += '</Document>\n'
    return text


def getKmlLatest(request):
    text = getKmlTrack(settings.GEOCAM_TRACK_FEED_NAME,
                       POSITION_MODEL.get().objects.all())
    return djangoResponse(text)


def dumps(obj):
    if settings.DEBUG:
        return json.dumps(obj, indent=4, sort_keys=True)  # pretty print
    else:
        return json.dumps(obj, separators=(',', ':'))  # compact


def getVehiclePositionsJson(request):
    return HttpResponse(dumps(getGeoJsonDictWithErrorHandling()),
                        content_type='application/json')


def postPosition(request):
    if request.method == 'GET':
        return HttpResponseNotAllowed('Please post a position as a GeoJSON Feature.')
    else:
        try:
            featureDict = json.loads(request.body)
        except ValueError:
            return HttpResponse('Malformed request, expected positions as a GeoJSON Feature',
                                status=400)

        vehicle = VEHICLE_MODEL.get().objects.get(id=featureDict['id'])

        # create or update ResourcePosition
        coordinates = featureDict['geometry']['coordinates']
        timestamp = iso8601.parse_date(properties['timestamp']).replace(tzinfo=None)
        attrs = dict(timestamp=timestamp,
                     longitude=coordinates[0],
                     latitude=coordinates[1])
        if len(coordinates) >= 3:
            attrs['altitude'] = coordinates[2]
        rp, created = ResourcePosition.objects.get_or_create(vehicle=vehicle,
                                                             defaults=attrs)
        if not created:
            for field, val in attrs.iteritems():
                setattr(rp, field, val)
            rp.save()

        # add a PastResourcePosition historical entry
        PastResourcePosition(vehicle=vehicle, **attrs).save()

        return HttpResponse(dumps(dict(result='ok')),
                            content_type='application/json')


def getLiveMap(request):
    userData = {'loggedIn': False}
    if request.user.is_authenticated():
        userData['loggedIn'] = True
        userData['userName'] = request.user.username

    return render(request,
                  'liveMap.html',
                  {'userData': dumps(userData)}
                  )


def getIcon(request, userName):
    return HttpResponse(renderAvatar(request, userName),
                        content_type='image/png')


def utcToDefaultTime(t):
    GEOCAM_TRACK_OPS_TZ = pytz.timezone(settings.GEOCAM_TRACK_OPS_TIME_ZONE)
    return pytz.utc.localize(t).astimezone(GEOCAM_TRACK_OPS_TZ).replace(tzinfo=None)


def defaultToUtcTime(t):
    GEOCAM_TRACK_OPS_TZ = pytz.timezone(settings.GEOCAM_TRACK_OPS_TIME_ZONE)
    return GEOCAM_TRACK_OPS_TZ.localize(t).astimezone(pytz.utc).replace(tzinfo=None)


def getDateRange(minDate, maxDate):
    dt = datetime.timedelta(1)
    d = minDate
    while d <= maxDate:
        yield d
        d += dt


def writeTrackNetworkLink(out, name,
                          trackName=None,
                          startTimeUtc=None,
                          endTimeUtc=None,
                          showIcon=1,
                          showLine=1,
                          showCompass=0,
                          recent=None,
                          caching='cached',
                          refreshInterval=None,
                          visibility=0,
                          openable=False):
    if caching == 'current':
        urlName = 'geocamTrack_tracks'
    elif caching == 'recent':
        urlName = 'geocamTrack_recentTracks'
    elif caching == 'cached':
        urlName = 'geocamTrack_cachedTracks'
    url = reverse(urlName)
    url = insertIntoPath(url)

    params = {}
    if trackName:
        params['track'] = trackName
    if startTimeUtc:
        params['start'] = str(calendar.timegm(startTimeUtc.timetuple()))
    if endTimeUtc:
        params['end'] = str(calendar.timegm(endTimeUtc.timetuple()))
    if not showIcon:
        params['icon'] = '0'
    if not showLine:
        params['line'] = '0'
    if showCompass:
        params['compass'] = '1'
    if recent:
        params['recent'] = str(recent)
    urlParams = urllib.urlencode(params)
    if urlParams:
        url += '?' + urlParams
    url = geocamTrack.models.latestRequestG.build_absolute_uri(url)
    if visibility:
        visibilityStr = ''
    else:
        visibilityStr = '<visibility>0</visibility>'
    if refreshInterval:
        refreshStr = ("""
    <refreshMode>onInterval</refreshMode>
    <refreshInterval>%s</refreshInterval>
""" % refreshInterval)
    else:
        refreshStr = ''
    if openable:
        styleStr = ''
    else:
        styleStr = ("""
  <Style>
    <ListStyle>
      <listItemType>checkHideChildren</listItemType>
    </ListStyle>
  </Style>
  """)
    out.write("""
<NetworkLink>
  <name>%(name)s</name>
  %(styleStr)s
  %(visibilityStr)s
  <Link>
    <href><![CDATA[%(url)s]]></href>
    %(refreshStr)s
  </Link>
</NetworkLink>
""" % dict(name=name,
           url=url,
           refreshStr=refreshStr,
           visibilityStr=visibilityStr,
           styleStr=styleStr))


def writeTrackIndexForDay(out, track, isToday):
    if isToday:
        out.write("""
    <Folder>
      <name>%s</name>
""" % track.name)
        writeTrackNetworkLink(out,
                              'Current Position',
                              caching='current',
                              trackName=track.name,
                              showLine=0,
                              refreshInterval=settings.GEOCAM_TRACK_CURRENT_POS_REFRESH_TIME_SECONDS)
        writeTrackNetworkLink(out,
                              'Compass Rose',
                              caching='current',
                              trackName=track.name,
                              showLine=0,
                              showIcon=0,
                              showCompass=1,
                              refreshInterval=settings.GEOCAM_TRACK_CURRENT_POS_REFRESH_TIME_SECONDS)
        writeTrackNetworkLink(out,
                              'Recent Tracks',
                              caching='recent',
                              trackName=track.name,
                              showIcon=0,
                              recent=settings.GEOCAM_TRACK_RECENT_TRACK_LENGTH_SECONDS,
                              refreshInterval=settings.GEOCAM_TRACK_RECENT_TRACK_REFRESH_TIME_SECONDS)
        writeTrackNetworkLink(out,
                              'Old Tracks',
                              caching='cached',
                              trackName=track.name,
                              showIcon=0,
                              startTimeUtc=track.pastposition_set.first().timestamp,
                              refreshInterval=settings.GEOCAM_TRACK_OLD_TRACK_REFRESH_TIME_SECONDS)
        out.write("""
    </Folder>
""")
    else:
        writeTrackNetworkLink(out,
                              '%s Track' % track.name,
                              caching='cached',
                              trackName=track.name,
                              showIcon=0,
                              startTimeUtc=track.pastposition_set.first().timestamp,
                              endTimeUtc=track.pastposition_set.last().timestamp,
                              visibility=0)


def getPositionCountForDay(day, track=None):
    dayStart = datetime.datetime.combine(day, datetime.time())
    startTimeUtc = defaultToUtcTime(dayStart)
    endTimeUtc = defaultToUtcTime(dayStart + datetime.timedelta(1))

    positions = (PAST_POSITION_MODEL.get()
                 .objects.filter
                 (timestamp__gte=startTimeUtc,
                  timestamp__lte=endTimeUtc))
    if track:
        positions = positions.filter(track=track)
    return positions.count()


def getTrackIndexKml(request):
    geocamTrack.models.latestRequestG = request
    #     dates = reversed(getDatesWithPositionData())
    tracks = TRACK_MODEL.get().objects.exclude(pastposition__isnull=True).order_by('-name')
    today = datetime.datetime.now(pytz.timezone(settings.GEOCAM_TRACK_OPS_TIME_ZONE)).date()
    todaystring = today.strftime("%Y%m%d")

    todays_tracks = []
    for track in tracks:
        if track.name.startswith(todaystring):
            todays_tracks.append(track)

    other_tracks = [t for t in tracks]
    other_tracks = other_tracks[len(todays_tracks):]
    dates = []
    for t in other_tracks:
        prefix = t.name[0:8]
        if prefix not in dates:
            dates.append(prefix)

    out = StringIO()
    out.write("""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"
     xmlns:gx="http://www.google.com/kml/ext/2.2"
     xmlns:kml="http://www.opengis.net/kml/2.2"
     xmlns:atom="http://www.w3.org/2005/Atom">
<Document>
  <name>Tracks</name>
  <open>1</open>
""")

    # do today
    if todays_tracks:
        out.write("""
      <Folder>
        <name>Today</name>
    """)
        for track in todays_tracks:
            writeTrackIndexForDay(out, track, True)
        out.write("""
      </Folder>
    """)

    if other_tracks:
        out.write('<Folder><name>Past Days</name>\n')
        lastday = None
        for track in other_tracks:
            prefix = track.name[0:8]
            if lastday == None:
                lastday = prefix
                out.write("""
        <Folder>
        <name>%s</name>
    """ % lastday)
            elif lastday != prefix:
                lastday = prefix
                out.write("""
        </Folder>
        <Folder>
        <name>%s</name>
    """ % lastday)

            writeTrackIndexForDay(out, track, False)

        out.write('</Folder>\n')
        out.write('</Folder>\n')

    out.write("""
</Document>
</kml>
""")
    return HttpResponse(out.getvalue(), content_type='application/vnd.google-earth.kml+xml')


@cache_page(0.9 * settings.GEOCAM_TRACK_CURRENT_POS_REFRESH_TIME_SECONDS)
def getCurrentPosKml(request):
    return getTracksKml(request)


@cache_page(0.9 * settings.GEOCAM_TRACK_RECENT_TRACK_REFRESH_TIME_SECONDS)
def getRecentTracksKml(request):
    return getTracksKml(request)


@cache_page(0.9 * settings.GEOCAM_TRACK_OLD_TRACK_REFRESH_TIME_SECONDS)
def getCachedTracksKml(request):
    return getTracksKml(request)


def getTracksKml(request, recent=True):
    geocamTrack.models.latestRequestG = request

    out = StringIO()
    out.write("""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">
<Document>
""")

    trackName = request.GET.get('track')
    if trackName:
        try:
            track = TRACK_MODEL.get().objects.get(name=trackName)
        except ObjectDoesNotExist:
            raise Http404('no track named %s' % trackName)
        tracks = [track]
    else:
        tracks = TRACK_MODEL.get().objects.all()

    startTime = request.GET.get('start')
    if startTime:
        startTime = datetime.datetime.utcfromtimestamp(float(startTime)).replace(tzinfo=pytz.utc)

    recent = request.GET.get('recent')
    if recent:
        recentStartFloat = RECENT_TIME_FUNCTION() - settings.GEOCAM_TRACK_RECENT_TRACK_LENGTH_SECONDS
        recentStartTime = datetime.datetime.utcfromtimestamp(recentStartFloat).replace(tzinfo=pytz.utc)
        if startTime is None or recentStartTime > startTime:
            startTime = recentStartTime

    endTime = request.GET.get('end')
    if endTime:
        endTime = datetime.datetime.utcfromtimestamp(float(endTime)).replace(tzinfo=pytz.utc)

    showLine = int(request.GET.get('line', 1))
    showIcon = int(request.GET.get('icon', 1))
    showCompass = int(request.GET.get('compass', 0))

    for track in tracks:
        if showLine:
            pastPositions = track.getPositions()
            if startTime:
                pastPositions = pastPositions.filter(timestamp__gte=startTime)
            if endTime:
                pastPositions = pastPositions.filter(timestamp__lte=endTime)
            track.writeTrackKml(out, positions=pastPositions, urlFn=request.build_absolute_uri)

        if showIcon or showCompass:
            currentPositions = track.getCurrentPositions()
            if startTime:
                currentPositions = currentPositions.filter(timestamp__gte=startTime)
            if endTime:
                currentPositions = currentPositions.filter(timestamp__lte=endTime)
            currentPositions = currentPositions[:1]
            if currentPositions:
                pos = currentPositions[0]

                if showIcon:
                    track.writeCurrentKml(out, pos, urlFn=request.build_absolute_uri)

                if showCompass:
                    track.writeCompassKml(out, pos, urlFn=request.build_absolute_uri)

    out.write("""
</Document>
</kml>
""")
    return HttpResponse(out.getvalue(), content_type='application/vnd.google-earth.kml+xml')


def getCsvTrackLink(day, trackName, startTimeUtc=None, endTimeUtc=None):
    fname = '%s_%s.csv' % (day.strftime('%Y%m%d'), trackName)
    url = reverse('geocamTrack_trackCsv', args=[trackName, fname])
    params = {}
    #     params['track'] = trackName
    if startTimeUtc:
        params['start'] = str(calendar.timegm(startTimeUtc.timetuple()))
    if endTimeUtc:
        params['end'] = str(calendar.timegm(endTimeUtc.timetuple()))
    urlParams = urllib.urlencode(params)
    if urlParams:
        url += '?' + urlParams
    return url


def getCsvTrackIndex(request):
    dates = getDatesWithPositionData()
    tracks = TRACK_MODEL.get().objects.all().order_by('name')

    out = StringIO()
    for day in dates:
        dayStart = datetime.datetime.combine(day, datetime.time())
        startTimeUtc = defaultToUtcTime(dayStart)
        endTimeUtc = defaultToUtcTime(dayStart + datetime.timedelta(1))

        dayPoints = (PAST_POSITION_MODEL.get()
                     .objects.filter
                     (timestamp__gte=startTimeUtc,
                      timestamp__lte=endTimeUtc))
        if not dayPoints.count():
            continue

        out.write('<li><span class="trackDate">%s</span> ' % day.strftime('%Y%m%d'))

        for track in tracks:
            trackPoints = dayPoints.filter(track=track)
            if trackPoints.count():
                link = getCsvTrackLink(day, track.name, startTimeUtc, endTimeUtc)
                out.write('<a class="trackLink" href="%s"><span>%s</span></a> '
                          % (link, track.name))
            else:
                out.write('<span class="disabledTrackLink">%s</span>'
                          % track.name)

        out.write('</li>\n')
    index = out.getvalue()

    return render(request,
                  'geocamTrack/csvTrackIndex.html',
                  {'index': index},
                  )


def getTrackCsv(request, trackName, fname=None):
    if not trackName:
        return HttpResponseBadRequest('trackName is required')
    if not fname:
        fname = trackName + '.csv'
    track = TRACK_MODEL.get().objects.get(name=trackName)
    positions = PAST_POSITION_MODEL.get().objects.filter(track=track). \
        order_by('timestamp')

    startTimeEpoch = request.GET.get('start')
    if startTimeEpoch:
        startTime = datetime.datetime.utcfromtimestamp(float(startTimeEpoch))
        positions = positions.filter(timestamp__gte=startTime)

    endTimeEpoch = request.GET.get('end')
    if endTimeEpoch:
        endTime = datetime.datetime.utcfromtimestamp(float(endTimeEpoch))
        positions = positions.filter(timestamp__lte=endTime)

    hasHeading = issubclass(PAST_POSITION_MODEL.get(), AbstractResourcePositionWithHeading)
    out = StringIO()
    topRow = '"epoch timestamp","timestamp","latitude","longitude","distance (m)","capped distance (m)","cumulative distance (m)"\n'
    if hasHeading:
        topRow = '"epoch timestamp","timestamp","latitude","longitude","heading","distance (m)","capped distance (m)","cumulative distance (m)"\n'
    out.write(topRow)
    prevPos = None
    cumDist = 0
    for pos in positions:
        epoch = calendar.timegm(pos.timestamp.timetuple())
        timestamp = pos.timestamp.isoformat() + 'Z'
        if prevPos:
            diff = geomath.calculateDiffMeters([pos.longitude, pos.latitude],
                                               [prevPos.longitude, prevPos.latitude])
            dist = geomath.getLength(diff)
        else:
            dist = 0
        if (settings.GEOCAM_TRACK_START_NEW_LINE_DISTANCE_METERS and
                dist > settings.GEOCAM_TRACK_START_NEW_LINE_DISTANCE_METERS):
            cappedDist = 0
        else:
            cappedDist = dist
        cumDist += cappedDist
        if hasHeading:
            if not pos.heading:
                out.write('%d,"%s",%.6f,%.6f,%s,%.2f,%.2f,%.2f\n'
                          % (epoch, timestamp, pos.latitude, pos.longitude, '', dist, cappedDist, cumDist))
            else:
                out.write('%d,"%s",%.6f,%.6f,%.2f,%.2f,%.2f,%.2f\n'
                          % (epoch, timestamp, pos.latitude, pos.longitude, pos.heading, dist, cappedDist, cumDist))
        else:
            out.write('%d,"%s",%.6f,%.6f,%.2f,%.2f,%.2f\n'
                      % (epoch, timestamp, pos.latitude, pos.longitude, dist, cappedDist, cumDist))

        prevPos = pos
    response = HttpResponse(out.getvalue(),
                            content_type='text/csv')
    response['Content-disposition'] = 'attachment; filename=%s' % fname
    return response


def getAnimatedTrackKml(request, trackName):
    #     print 'getting animated track %s' % trackName
    return getTrackKml(request, trackName, animated=True)


def getTrackKml(request, trackName, animated=False):
    if not trackName:
        return HttpResponseBadRequest('track parameter is required')
    track = TRACK_MODEL.get().objects.get(name=trackName)
    output = StringIO()
    track.writeTrackKml(output, animated=animated)
    text = output.getvalue()
    output.close()

    if text:
        return djangoResponse(text)
    else:
        # handle error case
        return HttpResponseBadRequest("ERROR GETTING TRACK -- no positions")


# TODO implement and test
# get some kml that has a bunch of centroids on a track
def getCentroidKml(request, trackName, centroids):
    if not trackName:
        return HttpResponseBadRequest('track parameter is required')
    track = TRACK_MODEL.get().objects.get(name=trackName)
    if track:
        for centroid in centroids:
            centroid.writeCentroidKml(track.getLineStyle())


def getLocationCentroid(trackName, start, end):
    """
    for a track, start time and end time get the centroid
    """
    track = TRACK_MODEL.get().objects.get(name=trackName)
    if not track:
        return None

    # get all the lats and longs over duration and find average.
    positions = POSITION_MODEL.get().objects.filter(track=track, timestamp__gte=start, timestamp__lte=end)
    if not positions:
        return None

    # then figure out the distribution
    centroid = Centroid()

    # iterate through
    count = 1
    totalLat = 0
    totalLon = 0
    for position in positions:
        totalLat += position.latitude
        totalLon += position.longitude
        count += 1

    centroid.latitude = totalLat / count
    centroid.longitude = totalLon / count

    # now figure out the standard deviation
    distance = 0
    for position in positions:
        distance += geomath.calculateDiffMeters([position.longitude, position.latitude],
                                                [centroid.longitude, centroid.latitude])
    distance = distance / len(positions)
    centroid.distance = math.sqrt(distance)

    return centroid


def getActivePositions(trackId=None):
    """ look up the active tracks from the GEOCAM_TRACK_POSITION_MODEL """
    tablename = POSITION_MODEL.get()._meta.db_table
    query = "select * from " + tablename
    # query = query + " where (timestampdiff(second, '" + datetime.now(pytz.utc).isoformat() + "', timestamp)) < " + settings.GEOCAM_TRACK_CURRENT_POSITION_AGE_MIN_SECONDS
    if trackId:
        query = query + ' where track_id=' + str(trackId)
    #     print query
    try:
        results = (POSITION_MODEL.get().objects.raw(query))
        return list(results)
    except:
        return []


def getActivePositionsJSON(request):
    ''' return JSON of the current active positions '''
    active_positions = getActivePositions()
    active_tracks = getActiveTracks()
    result = {}
    if active_positions:
        for position in active_positions:
            if (position.track in active_tracks):
                result[position.track.name] = position.toMapDict()

    return JsonResponse(result, encoder=DatetimeJsonEncoder)


def getActiveTracks():
    """ look up the active tracks from the GEOCAM_TRACK_POSITION_MODEL """
    return TRACK_MODEL.get().objects.filter(currentposition__isnull=False)


def getActiveTrackPKs(request):
    ''' return a JSON dictionary of channels to track pk '''
    active_tracks = getActiveTracks()
    result = {}
    if active_tracks:
        for track in active_tracks:
            result[track.name] = track.pk
    return JsonResponse(result, encoder=DatetimeJsonEncoder)


def mapJsonTrack(request, uuid):
    TRACK_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_TRACK_MODEL)
    try:
        track = TRACK_MODEL.get().objects.get(uuid=uuid)
        json_data = json.dumps([track.toMapDict()], cls=DatetimeJsonEncoder)
        return HttpResponse(content=json_data,
                            content_type="application/json")
    except:
        traceback.print_exc()
        return HttpResponse(content={},
                            content_type="application/json")


def mapJsonPosition(request, id):
    POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_POSITION_MODEL)
    try:
        position = POSITION_MODEL.get().objects.get(pk=id)
        json_data = json.dumps([position.toMapDict()], cls=DatetimeJsonEncoder)
        return HttpResponse(content=json_data,
                            content_type="application/json")
    except:
        return HttpResponse(content={},
                            content_type="application/json")


if False and settings.XGDS_SSE:
    def getLiveTest(request, trackId=None):
        return render(request,
                      "geocamTrack/testLive.html",
                      {'trackId': trackId},
                      )


    def getActivePositionsJson(request, trackId=None):
        json_data = modelsToJson(getActivePositions(trackId), DatetimeJsonEncoder)
        return HttpResponse(content=json_data,
                            content_type="application/json")


    def testPositions(request, trackId=None):
        activePositions = getActivePositions(trackId)
        if activePositions:
            json_data = modelsToJson(activePositions, DatetimeJsonEncoder)
            channel = 'live/positions'
            if trackId:
                channel = channel + '/' + str(trackId)
            json_data = ['{"now":' + datetime.datetime.now(pytz.utc).isoformat() + '}'] + json_data
            send_event('positions', json_data, channel)
            return HttpResponse(content=json_data,
                                content_type="application/json")
        return HttpResponse('No data')


    def sendActivePositions(trackId=None):
        while True:
            activePositions = getActivePositions(trackId)
            if activePositions:
                json_data = modelsToJson(activePositions, DatetimeJsonEncoder)
                channel = 'live/positions'
                theNow = datetime.datetime.now(pytz.utc).isoformat()
                if trackId:
                    json_data = ['{"now":' + theNow + '}'] + json_data
                    send_event('positions', json_data, channel + '/' + str(trackId))
                else:
                    for position in activePositions:
                        json_data = '{"now":' + theNow + '}' + modelToJson(position, DatetimeJsonEncoder)
                        send_event('positions', json_data, channel + '/' + str(position.track.pk))
            time.sleep(1)


#             yield

def getGpxWaypointList(docroot, ns):
    wptList = []
    for wpt in docroot.findall("ns:wpt", ns):
        if wpt.find("ns:time", ns) is not None:
            time = dateparser(wpt.find("ns:time", ns).text)
        else:
            time = None
        wptData = {"time": time,
                   "name": wpt.find("ns:name", ns).text,
                   "lat": float(wpt.attrib["lat"]),
                   "lon": float(wpt.attrib["lon"]),
                   "ele": float(wpt.find("ns:ele", ns).text),
                   "desc": wpt.find("ns:desc", ns).text,
                   "cmt": wpt.find("ns:cmt", ns).text,
                   "markerAndColor": [s.strip() for s in wpt.find("ns:sym", ns).
                       text.split(",")]}
        wptList.append(wptData)

    return wptList


def getGpxTrackSet(docroot, ns):
    trackCollection = []
    for trk in docroot.findall("ns:trk", ns):
        trackName = trk.find("ns:name", ns).text
        trackSegPointList = trk.find("ns:trkseg", ns)
        trackSegment = {"name": trackName}
        trackSegPoints = []
        foundTimeInTrackData = True
        for point in trackSegPointList:
            if point.find("ns:time", ns) is not None:
                time = dateparser(point.find("ns:time", ns).text)
                time = time.replace(tzinfo=None)
            else:
                foundTimeInTrackData = False
                time = "<no time>"
            trackPoint = {"lat": float(point.attrib["lat"]),
                          "lon": float(point.attrib["lon"]),
                          "ele": float(point.find("ns:ele", ns).text),
                          "time": time}
            trackSegPoints.append(trackPoint)
        trackSegment["foundTimeInTrackData"] = foundTimeInTrackData
        trackSegment["trackPoints"] = trackSegPoints
        trackCollection.append(trackSegment)

    return trackCollection


def doImportGpxTrack(request, f, tz, vehicle):
    gpxData = ''.join([chunk for chunk in f.chunks()])
    root = et.fromstring(gpxData)
    ns = {"ns": root.tag.split('}')[0].strip('{')}

    trackSet = getGpxTrackSet(root, ns)
    newTracksDB = []
    for track in trackSet:
        if track["foundTimeInTrackData"]:
            newTrackDB = TRACK_MODEL.get().objects.create(name=track["name"],
                                                          vehicle=vehicle)
            newTracksDB.append(newTrackDB)
            for point in track["trackPoints"]:
                PAST_POSITION_MODEL.get().objects.create(track=newTrackDB,
                                                         serverTimestamp=datetime.datetime.now(pytz.utc),
                                                         timestamp=point["time"],
                                                         latitude=point["lat"],
                                                         longitude=point["lon"],
                                                         altitude=point["ele"])
    return newTracksDB


def importTrack(request):
    errors = None
    newTracks = []
    jsonTracks = []
    if request.method == 'POST':
        form = ImportTrackForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data['sourceFile'].name.endswith(".gpx"):
                newTracks = doImportGpxTrack(request, request.FILES['sourceFile'], form.getTimezone(),
                                             form.getVehicle())
                if newTracks:
                    for t in newTracks:
                        jsonTracks.append(t.toMapDict())

        else:
            errors = form.errors
    return render(
        request,
        'geocamTrack/importTrack.html',
        {
            'form': ImportTrackForm(),
            'errorstring': errors,
            'tracks': json.dumps(jsonTracks, cls=DatetimeJsonEncoder)
        },
    )


def getSseActiveTracks(request):
    # Look up the active channels we are using for SSE
    return JsonResponse(settings.XGDS_SSE_TRACK_CHANNELS, safe=False)