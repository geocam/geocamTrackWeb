# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from StringIO import StringIO
import datetime
import time
import calendar
import urllib
import math

from django.views.decorators.cache import cache_page
from django.http import HttpResponse, HttpResponseNotAllowed, Http404, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
import pytz
import iso8601

from geocamUtil import anyjson as json
from geocamUtil import geomath
from geocamUtil.loader import getModelByName

from geocamTrack.models import Resource, ResourcePosition, PastResourcePosition, Centroid
import geocamTrack.models
from geocamTrack.avatar import renderAvatar
from geocamTrack import settings

TRACK_MODEL = getModelByName(settings.GEOCAM_TRACK_TRACK_MODEL)
RESOURCE_MODEL = getModelByName(settings.GEOCAM_TRACK_RESOURCE_MODEL)
POSITION_MODEL = getModelByName(settings.GEOCAM_TRACK_POSITION_MODEL)
PAST_POSITION_MODEL = getModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)
GEOCAM_TRACK_OPS_TZ = pytz.timezone(settings.GEOCAM_TRACK_OPS_TIME_ZONE)


class ExampleError(Exception):
    pass


def getIndex(request):
    return render_to_response('trackingIndex.html',
                              {},
                              context_instance=RequestContext(request))


def getGeoJsonDict():
    return dict(type='FeatureCollection',
                crs=dict(type='name',
                         properties=dict(name='urn:ogc:def:crs:OGC:1.3:CRS84')),
                features=[r.getGeoJson() for r in POSITION_MODEL.objects.all()])


def getGeoJsonDictWithErrorHandling():
    try:
        result = getGeoJsonDict()
    except ExampleError:
        return dict(error=dict(code=-32099,
                               message='This is how we would signal an err'))
    return dict(result=result)


def wrapKml(text):
    # xmlns:gx="http://www.google.com/kml/ext/2.2"
    return '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"
     xmlns:kml="http://www.opengis.net/kml/2.2"
     xmlns:atom="http://www.w3.org/2005/Atom">
%s
</kml>
''' % text


def getKmlResponse(text):
    return HttpResponse(wrapKml(text),
                        mimetype='application/vnd.google-earth.kml+xml')


def getKmlNetworkLink(request):
    url = request.build_absolute_uri(settings.SCRIPT_NAME + 'geocamTrack/latest.kml')
    return getKmlResponse('''
<NetworkLink>
  <name>%(name)s</name>
  <Link>
    <href>%(url)s</href>
    <refreshMode>onInterval</refreshMode>
    <refreshInterval>5</refreshInterval>
  </Link>
</NetworkLink>
''' % dict(name=settings.GEOCAM_TRACK_FEED_NAME,
           url=url))


def getKmlTrack(name, positions):
    text = '<Document>\n'
    text += '  <name>%s</name>\n' % name
    for i, pos in enumerate(positions):
        text += pos.getKml(i)
    text += '</Document>\n'
    return text


def getKmlLatest(request):
    text = getKmlTrack(settings.GEOCAM_TRACK_FEED_NAME,
                       POSITION_MODEL.objects.all())
    return getKmlResponse(text)


def dumps(obj):
    if settings.DEBUG:
        return json.dumps(obj, indent=4, sort_keys=True)  # pretty print
    else:
        return json.dumps(obj, separators=(',', ':'))  # compact


def getResourcesJson(request):
    return HttpResponse(dumps(getGeoJsonDictWithErrorHandling()),
                        mimetype='application/json')


def postPosition(request):
    if request.method == 'GET':
        return HttpResponseNotAllowed('Please post a resource position as a GeoJSON Feature.')
    else:
        try:
            featureDict = json.loads(request.raw_post_data)
        except ValueError:
            return HttpResponse('Malformed request, expected resources position as a GeoJSON Feature',
                                status=400)

        # create or update Resource
        properties = featureDict['properties']
        featureUserName = properties['userName']
        matchingUsers = User.objects.filter(username=featureUserName)
        if matchingUsers:
            user = matchingUsers[0]
        else:
            user = User.objects.create_user(featureUserName, '%s@example.com' % featureUserName, '12345')
            user.first_name = featureUserName
            user.is_active = False
            user.save()
        resource, created = Resource.objects.get_or_create(uuid=featureDict['id'],
                                                           defaults=dict(user=user))
        if resource.user.username != featureUserName:
            resource.user = user
            resource.save()

        # create or update ResourcePosition
        coordinates = featureDict['geometry']['coordinates']
        timestamp = iso8601.parse_date(properties['timestamp']).replace(tzinfo=None)
        attrs = dict(timestamp=timestamp,
                     longitude=coordinates[0],
                     latitude=coordinates[1])
        if len(coordinates) >= 3:
            attrs['altitude'] = coordinates[2]
        rp, created = ResourcePosition.objects.get_or_create(resource=resource,
                                                             defaults=attrs)
        if not created:
            for field, val in attrs.iteritems():
                setattr(rp, field, val)
            rp.save()

        # add a PastResourcePosition historical entry
        PastResourcePosition(resource=resource, **attrs).save()

        return HttpResponse(dumps(dict(result='ok')),
                            mimetype='application/json')


def getLiveMap(request):
    userData = {'loggedIn': False}
    if request.user.is_authenticated():
        userData['loggedIn'] = True
        userData['userName'] = request.user.username

    return render_to_response('liveMap.html',
                              {'userData': dumps(userData)},
                              context_instance=RequestContext(request))


def getIcon(request, userName):
    return HttpResponse(renderAvatar(request, userName),
                        mimetype='image/png')


def utcToDefaultTime(t):
    return pytz.utc.localize(t).astimezone(GEOCAM_TRACK_OPS_TZ).replace(tzinfo=None)


def defaultToUtcTime(t):
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


def getPositionDataDateRange():
    allPositions = PAST_POSITION_MODEL.objects.all()
    if allPositions.count():
        minTimeUtc = allPositions.order_by('timestamp')[0].timestamp
        maxTimeUtc = allPositions.order_by('-timestamp')[0].timestamp
        minDate = utcToDefaultTime(minTimeUtc).date()
        maxDate = utcToDefaultTime(maxTimeUtc).date()
        return list(getDateRange(minDate, maxDate))
    else:
        return []


def writeTrackIndexForDay(out, track, day, isToday, startTimeUtc, endTimeUtc):
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
                              startTimeUtc=startTimeUtc,
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
                              startTimeUtc=startTimeUtc,
                              endTimeUtc=endTimeUtc,
                              visibility=0)


def getPositionCountForDay(day, track=None):
    dayStart = datetime.datetime.combine(day, datetime.time())
    startTimeUtc = defaultToUtcTime(dayStart)
    endTimeUtc = defaultToUtcTime(dayStart + datetime.timedelta(1))

    positions = (PAST_POSITION_MODEL
                 .objects.filter
                 (timestamp__gte=startTimeUtc,
                  timestamp__lte=endTimeUtc))
    if track:
        positions = positions.filter(track=track)
    return positions.count()


def getTrackIndexKml(request):
    geocamTrack.models.latestRequestG = request
    dates = reversed(getPositionDataDateRange())
    dates = [day
             for day in dates
             if getPositionCountForDay(day)]
    tracks = TRACK_MODEL.objects.all().order_by('name')

    now = utcToDefaultTime(datetime.datetime.utcnow())
    today = now.date()

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

    if len(dates) >= 4 and dates[0] == today:
        # Put past days in a separate folder to avoid clutter. The user
        # is most likely to be interested in today's data.
        dates = [dates[0]] + ['pastDaysStart'] + dates[1:] + ['pastDaysEnd']

    for day in dates:
        if day == 'pastDaysStart':
            out.write('<Folder><name>Past Days</name>\n')
            continue
        elif day == 'pastDaysEnd':
            out.write('</Folder>\n')
            continue

        if day == today:
            dateStr = 'Today'
        else:
            dateStr = day.strftime('%Y-%m-%d')

        dayStart = datetime.datetime.combine(day, datetime.time())
        startTimeUtc = defaultToUtcTime(dayStart)
        endTimeUtc = defaultToUtcTime(dayStart + datetime.timedelta(1))

        out.write("""
  <Folder>
    <name>%s</name>
""" % dateStr)

        for track in tracks:
            if getPositionCountForDay(day, track):
                isToday = (day == today)
                writeTrackIndexForDay(out, track, day, isToday, startTimeUtc, endTimeUtc)
        out.write("""
  </Folder>
""")

    out.write("""
</Document>
</kml>
""")
    return HttpResponse(out.getvalue(), mimetype='application/vnd.google-earth.kml+xml')


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
            track = TRACK_MODEL.objects.get(name=trackName)
        except ObjectDoesNotExist:
            raise Http404('no track named %s' % trackName)
        tracks = [track]
    else:
        tracks = TRACK_MODEL.objects.all()

    startTime = request.GET.get('start')
    if startTime:
        startTime = datetime.datetime.utcfromtimestamp(float(startTime))

    recent = request.GET.get('recent')
    if recent:
        recentStartFloat = time.time() - settings.GEOCAM_TRACK_RECENT_TRACK_LENGTH_SECONDS
        recentStartTime = datetime.datetime.utcfromtimestamp(recentStartFloat)
        if startTime is None or recentStartTime > startTime:
            startTime = recentStartTime

    endTime = request.GET.get('end')
    if endTime:
        endTime = datetime.datetime.utcfromtimestamp(float(endTime))

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
    return HttpResponse(out.getvalue(), mimetype='application/vnd.google-earth.kml+xml')


def getCsvTrackLink(day, trackName, startTimeUtc=None, endTimeUtc=None):
    fname = '%s_%s.csv' % (day.strftime('%Y%m%d'), trackName)
    url = reverse('geocamTrack_trackCsv', args=[fname])
    params = {}
    params['track'] = trackName
    if startTimeUtc:
        params['start'] = str(calendar.timegm(startTimeUtc.timetuple()))
    if endTimeUtc:
        params['end'] = str(calendar.timegm(endTimeUtc.timetuple()))
    urlParams = urllib.urlencode(params)
    if urlParams:
        url += '?' + urlParams
    return url


def getCsvTrackIndex(request):
    dates = getPositionDataDateRange()
    tracks = TRACK_MODEL.objects.all().order_by('name')

    out = StringIO()
    for day in dates:
        dayStart = datetime.datetime.combine(day, datetime.time())
        startTimeUtc = defaultToUtcTime(dayStart)
        endTimeUtc = defaultToUtcTime(dayStart + datetime.timedelta(1))

        dayPoints = (PAST_POSITION_MODEL
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

    return render_to_response('geocamTrack/csvTrackIndex.html',
                              {'index': index},
                              context_instance=RequestContext(request))


def getTrackCsv(request, fname):
    trackName = request.GET.get('track')
    if not trackName:
        return HttpResponseBadRequest('track parameter is required')
    track = TRACK_MODEL.objects.get(name=trackName)
    positions = PAST_POSITION_MODEL.objects.filter(track=track).\
        order_by('timestamp')

    startTimeEpoch = request.GET.get('start')
    if startTimeEpoch:
        startTime = datetime.datetime.utcfromtimestamp(float(startTimeEpoch))
        positions = positions.filter(timestamp__gte=startTime)

    endTimeEpoch = request.GET.get('end')
    if endTimeEpoch:
        endTime = datetime.datetime.utcfromtimestamp(float(endTimeEpoch))
        positions = positions.filter(timestamp__lte=endTime)

    out = StringIO()
    out.write('"epoch timestamp","timestamp","latitude","longitude","distance (m)","capped distance (m)","cumulative distance (m)"\n')
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
        out.write('%d,"%s",%.6f,%.6f,%.2f,%.2f,%.2f\n'
                  % (epoch, timestamp, pos.latitude, pos.longitude, dist, cappedDist, cumDist))

        prevPos = pos
    response = HttpResponse(out.getvalue(),
                            mimetype='text/csv')
    response['Content-disposition'] = 'attachment; filename=%s' % fname
    return response


def getTrackKml(request, trackName, animated=False):
#    trackName = request.GET.get('track')
    if not trackName:
        return HttpResponseBadRequest('track parameter is required')
    track = TRACK_MODEL.objects.get(name=trackName)
    output = StringIO()
    track.writeTrackKml(output, animated)
    text = output.getvalue()
    output.close()

    return getKmlResponse(text)


# TODO implement and test
# get some kml that has a bunch of centroids on a track
def getCentroidKml(request, trackName, centroids):
    if not trackName:
        return HttpResponseBadRequest('track parameter is required')
    track = TRACK_MODEL.objects.get(name=trackName)
    if track:
        for centroid in centroids:
            centroid.writeCentroidKml(track.getLineStyle())


def getClosestPosition(track, timestamp, max_time_difference_seconds=60):
    """
    Look up the closest location, with a 1 minute default maximum difference.
    """
    try:
        foundPosition = PAST_POSITION_MODEL.objects.get(track=track, timestamp=timestamp)
    except ObjectDoesNotExist:
        tablename = PAST_POSITION_MODEL._meta.db_table
        query = "select * from " + tablename + " where " + "track_id = '" + str(track.id) + "' order by abs(timestampdiff(second, '" + timestamp.isoformat() + "' , timestamp)) limit 1"
        posAtTime = (PAST_POSITION_MODEL.objects.raw(query))
        posList = list(posAtTime)
        if posList:
            foundPosition = posAtTime[0]
            if (foundPosition.timestamp > timestamp):
                delta = (foundPosition.timestamp - timestamp)
            else:
                delta = (timestamp - foundPosition.timestamp)
            if math.fabs(delta.seconds) > max_time_difference_seconds:
                foundPosition = None
        else:
            foundPosition = None
    return foundPosition


def getLocationCentroid(trackName, start, end):
    """
    for a track, start time and end time get the centroid
    """
    track = TRACK_MODEL.objects.get(name=trackName)
    if not track:
        return None

    # get all the lats and longs over duration and find average.
    positions = POSITION_MODEL.objects.filter(track=track, timestamp__gte=start, timestamp__lte=end)
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
        distance += geomath.calculateDiffMeters([position.longitude, position.latitude], [centroid.longitude, centroid.latitude])
    distance = distance / len(positions)
    centroid.distance = math.sqrt(distance)

    return centroid
