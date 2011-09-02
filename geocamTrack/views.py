# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import os
import sys
from StringIO import StringIO
import datetime
import calendar
import urllib

from django.http import HttpResponse, HttpResponseNotAllowed, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
import pytz
import iso8601

from geocamUtil import anyjson as json
from geocamTrack.models import Resource, ResourcePosition, PastResourcePosition, Track, getModelByName
import geocamTrack.models
from geocamTrack.avatar import renderAvatar
from geocamTrack import settings

TRACK_MODEL = getModelByName(settings.GEOCAM_TRACK_TRACK_MODEL)
RESOURCE_MODEL = getModelByName(settings.GEOCAM_TRACK_RESOURCE_MODEL)
PAST_POSITION_MODEL = getModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)
DEFAULT_TZ = pytz.timezone(settings.DEFAULT_TIME_ZONE['code'])

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
                features=[r.getGeoJson() for r in ResourcePosition.objects.all()])

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
  <name>GeoCam Track</name>
  <Link>
    <href>%(url)s</href>
    <refreshMode>onInterval</refreshMode>
    <refreshInterval>5</refreshInterval>
  </Link>
</NetworkLink>
''' % dict(url=url))

def getKmlLatest(request):
    text = '<Document>\n'
    text += '  <name>GeoCam Track</name>\n'
    positions = ResourcePosition.objects.all().order_by('resource__user__username')
    for i, pos in enumerate(positions):
        text += pos.getKml(i)
    text += '</Document>\n'
    return getKmlResponse(text)

def dumps(obj):
    if settings.DEBUG:
        return json.dumps(obj, indent=4, sort_keys=True) # pretty print
    else:
        return json.dumps(obj, separators=(',',':')) # compact

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
    userData = { 'loggedIn': False }
    if request.user.is_authenticated():
        userData['loggedIn'] = True
        userData['userName'] = request.user.username

    return render_to_response('liveMap.html',
                              { 'userData': dumps(userData) },
                              context_instance=RequestContext(request))

def getIcon(request, userName):
    return HttpResponse(renderAvatar(request, userName),
                        mimetype='image/png')

def utcToDefaultTime(t):
    return pytz.utc.localize(t).astimezone(DEFAULT_TZ).replace(tzinfo=None)

def defaultToUtcTime(t):
    return DEFAULT_TZ.localize(t).astimezone(pytz.utc).replace(tzinfo=None)

def getDateRange(minDate, maxDate):
    dt = datetime.timedelta(1)
    d = minDate
    while d <= maxDate:
        yield d
        d += dt

def writeTrackNetworkLink(out, name, trackName=None, startTimeUtc=None,
                          endTimeUtc=None, showIcon=1, showLine=1,
                          viewRefreshTime=None, visibility=0):
    url = reverse('geocamTrack_tracks')
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
    urlParams = urllib.urlencode(params)
    if urlParams:
        url += '?' + urlParams
    url = geocamTrack.models.latestRequestG.build_absolute_uri(url)
    if visibility:
        visibilityStr = ''
    else:
        visibilityStr = '<visibility>0</visibility>'
    if viewRefreshTime:
        refreshStr = ("""
    <refreshMode>onInterval</refreshMode>
    <viewRefreshTime>%s</viewRefreshTime>
""" % viewRefreshTime)
    else:
        refreshStr = ''
        
    out.write("""
<NetworkLink>
  <name>%(name)s</name>
  %(visibilityStr)s
  <Link>
    <href><![CDATA[%(url)s]]></href>
    %(refreshStr)s
  </Link>
</NetworkLink>
""" % dict(name=name, url=url, refreshStr=refreshStr,
           visibilityStr=visibilityStr))

def getTrackIndexKml(request):
    geocamTrack.models.latestRequestG = request

    allPositions = PAST_POSITION_MODEL.objects.all()
    if allPositions.count():
        minTimeUtc = allPositions.order_by('timestamp')[0].timestamp
        maxTimeUtc = allPositions.order_by('-timestamp')[0].timestamp
        minDate = utcToDefaultTime(minTimeUtc).date()
        maxDate = utcToDefaultTime(maxTimeUtc).date()
        dates = list(getDateRange(minDate, maxDate))
    else:
        dates = []
    
    tracks = TRACK_MODEL.objects.all().order_by('name')

    now = utcToDefaultTime(datetime.datetime.utcnow())
    today = now.date()
    if today not in dates:
        dates.append(today)

    out = StringIO()
    out.write("""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"
     xmlns:gx="http://www.google.com/kml/ext/2.2"
     xmlns:kml="http://www.opengis.net/kml/2.2"
     xmlns:atom="http://www.w3.org/2005/Atom">
<Document>
  <name>Tracks</name>
""")

    for day in dates:
        dateStr = day.strftime('%Y%m%d')
        if day == today:
            dateStr += ' (today)'

        dayStart = datetime.datetime.combine(day, datetime.time())
        startTimeUtc = defaultToUtcTime(dayStart)
        endTimeUtc = defaultToUtcTime(dayStart + datetime.timedelta(1))
        
        if day != today:
            pathCount = (PAST_POSITION_MODEL
                         .objects.filter
                         (timestamp__gte=startTimeUtc,
                          timestamp__lte=endTimeUtc)).count()
            if not pathCount:
                continue

        out.write("""
  <Folder>
    <name>%s</name>
""" % dateStr)

        for track in tracks:
            if day == today:
                out.write("""
    <Folder>
      <name>%s</name>
""" % track.name)
                writeTrackNetworkLink(out,
                                      '%s Current' % track.name,
                                      trackName=track.name,
                                      showLine=0,
                                      viewRefreshTime=settings.GEOCAM_TRACK_KML_REFRESH_TIME_SECONDS)
                writeTrackNetworkLink(out,
                                      '%s Track' % track.name,
                                      trackName=track.name,
                                      showIcon=0,
                                      startTimeUtc=startTimeUtc,
                                      endTimeUtc=endTimeUtc,
                                      viewRefreshTime=settings.GEOCAM_TRACK_KML_REFRESH_TIME_SECONDS)
                out.write("""
    </Folder>
""")
            else: # not today
                pathCount = (PAST_POSITION_MODEL
                             .objects.filter
                             (track=track,
                              timestamp__gte=startTimeUtc,
                              timestamp__lte=endTimeUtc)).count()
                if pathCount != 0:
                    writeTrackNetworkLink(out,
                                          '%s Track' % track.name,
                                          trackName=track.name,
                                          showIcon=0,
                                          startTimeUtc=startTimeUtc,
                                          endTimeUtc=endTimeUtc,
                                          visibility=0)
        out.write("""
  </Folder>
""")

    out.write("""
</Document>
</kml>
""")
    return HttpResponse(out.getvalue(), mimetype='application/vnd.google-earth.kml+xml')
    

def getTracksKml(request):
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
        
    endTime = request.GET.get('end')
    if endTime:
        endTime = datetime.datetime.utcfromtimestamp(float(endTime))

    showLine = int(request.GET.get('line', 1))
    showIcon = int(request.GET.get('icon', 1))

    for track in tracks:
        if showLine:
            pastPositions = track.getPositions()
            if startTime:
                pastPositions = pastPositions.filter(timestamp__gte=startTime)
            if endTime:
                pastPositions = pastPositions.filter(timestamp__lte=endTime)
            track.writeTrackKml(out, positions=pastPositions)

        if showIcon:
            currentPositions = track.getCurrentPositions()
            if startTime:
                currentPositions = currentPositions.filter(timestamp__gte=startTime)
            if endTime:
                currentPositions = currentPositions.filter(timestamp__lte=endTime)
            track.writeCurrentKml(out, positions=currentPositions)
    out.write("""
</Document>
</kml>
""")
    return HttpResponse(out.getvalue(), mimetype='application/vnd.google-earth.kml+xml')
