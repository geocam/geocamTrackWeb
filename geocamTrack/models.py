# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

import json
import calendar
import datetime
import logging
import struct
from math import pi, cos, sin
import urllib

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
import pytz

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from geocamUtil import TimeUtil
from geocamUtil import geomath
from geocamUtil.models.ExtrasDotField import ExtrasDotField
from geocamUtil.models.UuidField import UuidField
from geocamUtil.loader import LazyGetModelByName

from geocamUtil.usng import usng

# pylint: disable=C1001
latestRequestG = None

POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_POSITION_MODEL)
PAST_POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)


def getModClass(name):
    """converts 'app_name.ModelName' to ['stuff.module', 'ClassName']"""
    try:
        dot = name.rindex('.')
    except ValueError:
        return name, ''
    return name[:dot], name[dot + 1:]


class AbstractResource(models.Model):
    name = models.CharField(max_length=32)
    user = models.ForeignKey(User, null=True, blank=True)
    uuid = UuidField()
    extras = ExtrasDotField()

    def __unicode__(self):
        return '%s %s' % (self.__class__.__name__, self.name)
    
    def get_content_type(self):
        return ContentType.objects.get_for_model(self).pk
    
    class Meta:
        abstract = True
    

class Resource(AbstractResource):
    pass


class IconStyle(models.Model):
    name = models.CharField(max_length=40, blank=True)
    url = models.CharField(max_length=1024, blank=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    scale = models.FloatField(default=1)
    color = models.CharField(max_length=16, blank=True,
                             help_text='Optional KML color specification, hex in AABBGGRR order')
    uuid = UuidField()
    extras = ExtrasDotField()

    def __unicode__(self):
        return '%s %s' % (self.__class__.__name__, self.name)

    def writeKml(self, out, heading=None, urlFn=None, color=None):
        if not color:
            color = self.color
        if color:
            colorStr = '<color>%s</color>' % color
        else:
            colorStr = ''
        if self.scale != 1:
            scaleStr = '<scale>%s</scale>' % self.scale
        else:
            scaleStr = ''
        if heading is not None:
            headingStr = '<heading>%s</heading>' % heading
        else:
            headingStr = ''
        imgUrl = self.url
        if urlFn:
            imgUrl = urlFn(imgUrl)
        out.write("""
<IconStyle>
  %(headingStr)s
  %(colorStr)s
  %(scaleStr)s
  <Icon>
    <href>%(url)s</href>
  </Icon>
</IconStyle>
""" % dict(url=imgUrl,
           scaleStr=scaleStr,
           colorStr=colorStr,
           headingStr=headingStr,
           id=self.pk))


class LineStyle(models.Model):
    name = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=16, blank=True,
                             help_text='Optional KML color specification, hex in AABBGGRR order')
    width = models.PositiveIntegerField(default=1, null=True, blank=True)
    uuid = UuidField()
    extras = ExtrasDotField()

    def __unicode__(self):
        return '%s %s' % (self.__class__.__name__, self.name)

    def writeKml(self, out, urlFn=None, color=None):
        if not color:
            color = self.color
        if color:
            colorStr = '<color>%s</color>' % color
        else:
            colorStr = ''
        if self.width is not None:
            widthStr = '<width>%s</width>' % self.width
        else:
            widthStr = ''
        out.write("""
<LineStyle>
  %(colorStr)s
  %(widthStr)s
</LineStyle>
""" % dict(colorStr=colorStr,
           widthStr=widthStr))

    def getAlpha(self):
        """ Get 0-1 alpha value from color """
        if self.color:
            decvalue = int("0x" + self.color[0:2], 16)
            return decvalue / 255
        return 1.0

    def getHexColor(self):
        if self.color:
            return self.color[2:]
        return None


def timeDeltaTotalSeconds(delta):
    return 86400 * delta.days + delta.seconds + 1e-6 * delta.microseconds


def getTimeSpinner(timestamp):
    secondSinceEpoch = calendar.timegm(timestamp.timetuple())
    index = int(secondSinceEpoch) % 4
    return '|/-\\'[index]


def posixTimestampFromDatetime(dt):
    return calendar.timegm(dt.timetuple())


def getKmlUrl(trackName=None,
              recent=False, cached=False,
              startTime=None, endTime=None,
              showLine=True, showIcon=False, showCompass=False):

    paramsDict = {}
    if trackName is not None:
        paramsDict['track'] = trackName
    if recent:
        paramsDict['recent'] = '1'
    if startTime is not None:
        paramsDict['start'] = str(posixTimestampFromDatetime(startTime))
    if endTime is not None:
        paramsDict['end'] = str(posixTimestampFromDatetime(endTime))
    if not showLine:
        paramsDict['line'] = '0'
    if not showIcon:
        paramsDict['icon'] = '0'
    if showCompass:
        paramsDict['compass'] = '1'

    if paramsDict:
        queryParams = '?' + urllib.urlencode(paramsDict)
    else:
        queryParams = ''

    if cached:
        urlPattern = 'geocamTrack_cachedTracks'
    elif recent:
        urlPattern = 'geocamTrack_recentTracks'
    else:
        urlPattern = 'geocamTrack_tracks'

    return reverse(urlPattern) + queryParams


class AbstractTrack(models.Model):
    """ This is for an abstract track with a FIXED resource model, ie all the tracks have like resources.
    """
    name = models.CharField(max_length=40, blank=True)
    resource = models.ForeignKey(settings.GEOCAM_TRACK_RESOURCE_MODEL,
                                 related_name='%(app_label)s_%(class)s_related',
                                 verbose_name=settings.GEOCAM_TRACK_RESOURCE_VERBOSE_NAME, blank=True, null=True)
    iconStyle = models.ForeignKey(settings.GEOCAM_TRACK_ICON_STYLE_MODEL, null=True, blank=True,
                                  related_name='%(app_label)s_%(class)s_related')
    lineStyle = models.ForeignKey(settings.GEOCAM_TRACK_LINE_STYLE_MODEL, null=True, blank=True,
                                  related_name='%(app_label)s_%(class)s_related')
    uuid = UuidField()
    extras = ExtrasDotField()

    class Meta:
        abstract = True
        ordering = ('name',)

    def __unicode__(self):
        return '%s %s' % (self.__class__.__name__, self.name)

    def getTimezone(self):
        """
        Override if your model has a different way of getting time zones.
        It would be nifty to look them up from lat/lon
        """
        return pytz.timezone(settings.TIME_ZONE)

    def getPositions(self):
        return PAST_POSITION_MODEL.get().objects.filter(track=self)

    def getCurrentPositions(self):
        return POSITION_MODEL.get().objects.filter(track=self)

    def getLabelName(self, pos):
        return self.name

    def getLabelExtra(self, pos):
        return ''

    def getIconStyle(self, pos):
        # use specific style if given
        if self.iconStyle is not None:
            return self.iconStyle

        # use pointer icon if we know the heading
        if pos.heading is not None:
            if not hasattr(self, '_pointerIcon'):
                self._pointerIcon = IconStyle.objects.get(name='pointer')
            return self._pointerIcon

        # use spot icon otherwise
        if not hasattr(self, '_defaultIcon'):
            self._defaultIcon = IconStyle.objects.get(name='default')
        return self._defaultIcon

    def getLineStyle(self):
        if self.lineStyle:
            return self.lineStyle
        return LineStyle.objects.get(name='default')

    def getIconColor(self, pos):
        return self.getIconStyle(pos).color

    def getLineColor(self):
        return self.getLineStyle().color

    def getKmlUrl(self, **kwargs):
        kwargs['trackName'] = self.name
        return getKmlUrl(**kwargs)

    def writeCurrentKml(self, out, pos, iconStyle=None, urlFn=None):
        if iconStyle is None:
            iconStyle = self.getIconStyle(pos)
        ageStr = ''
        if settings.GEOCAM_TRACK_SHOW_CURRENT_POSITION_AGE:
            now = datetime.datetime.utcnow()
            diff = now - pos.timestamp
            diffSecs = diff.days * 24 * 60 * 60 + diff.seconds
            if diffSecs >= settings.GEOCAM_TRACK_CURRENT_POSITION_AGE_MIN_SECONDS:
                age = TimeUtil.getTimeShort(pos.timestamp)
                ageStr = ' (%s)' % age
            ageStr += ' %s' % getTimeSpinner(datetime.datetime.now())

        label = ('%s%s%s' %
                 (self.getLabelName(pos),
                  self.getLabelExtra(pos),
                  ageStr))
        out.write("""
<Placemark>
  <name>%(label)s</name>
""" % dict(label=label))
        if iconStyle:
            out.write("<Style>\n")
            iconStyle.writeKml(out, pos.getHeading(), urlFn=urlFn, color=self.getIconColor(pos))
            out.write("</Style>\n")

        out.write("""
  <Point>
    <coordinates>
""")
        pos.writeCoordinatesKml(out)
        out.write("""
    </coordinates>
  </Point>
</Placemark>
""")

    def writeCompassKml(self, out, pos, urlFn=None):
        pngUrl = settings.STATIC_URL + 'geocamTrack/icons/compassRoseLg.png'
        if urlFn:
            pngUrl = urlFn(pngUrl)
        out.write("""
<Placemark>
  <Style>
    <IconStyle>
      <scale>6.0</scale>
      <Icon>
        <href>%(pngUrl)s</href>
      </Icon>
    </IconStyle>
  </Style>
  <Point>
    <coordinates>
""" % {'pngUrl': pngUrl})
        pos.writeCoordinatesKml(out)
        out.write("""
    </coordinates>
  </Point>
</Placemark>
""")

    def writeAnimatedPlacemarks(self, out, positions):
        out.write("    <Folder>\n")
        out.write("        <name>Trajectory</name>\n")
        out.write("        <open>0</open>\n")

#         out.write('      <visibility>1</visibility>\n')
        numPositions = len(positions) - 1
        for i, pos in enumerate(positions):
            # start new line string
            out.write("        <Placemark>\n")
            out.write("            <TimeSpan>\n")
            begin = pytz.utc.localize(pos.timestamp).astimezone(self.getTimezone())
            tzoffset = begin.strftime('%z')
            tzoffset = tzoffset[0:-2] + ":00"
            out.write("                <begin>%04d-%02d-%02dT%02d:%02d:%02d%s</begin>\n" %
                        (begin.year, begin.month, begin.day,
                         begin.hour, begin.minute, begin.second, tzoffset))
            if i < numPositions:
                nextpos = positions[i + 1]
                end = pytz.utc.localize(nextpos.timestamp).astimezone(self.getTimezone())
                #end = self.getTimezone().localize(nextpos.timestamp)
            else:
                end = begin

            out.write("                <end>%04d-%02d-%02dT%02d:%02d:%02d%s</end>\n" %
                        (end.year, end.month, end.day,
                         end.hour, end.minute, end.second, tzoffset))
            out.write("            </TimeSpan>\n")
#             out.write("            <styleUrl>#dw%d</styleUrl>\n" % (pos.heading))
            out.write("            <styleUrl>#%s</styleUrl>\n" % self.getIconStyle(pos).pk)
            out.write("            <gx:balloonVisibility>1</gx:balloonVisibility>\n")
            out.write("            <Point>\n")
            out.write("                <coordinates>")
            pos.writeCoordinatesKml(out)
            out.write("                </coordinates>\n")
            out.write("            </Point>\n")
            out.write("        </Placemark>\n")
        out.write("        </Folder>\n")

    def writeTrackKml(self, out, positions=None, lineStyle=None, urlFn=None, animated=False):
        if positions is None:
            positions = self.getPositions()
        if lineStyle is None:
            lineStyle = self.lineStyle

        n = positions.count()
        if n == 0:
            return

        if n < 2:
            # kml LineString requires 2 or more positions
            return
        out.write("<Folder>\n")
        out.write("""
<Placemark>
  <name>%(name)s path</name>
""" % dict(name=self.name))
        if lineStyle:
            out.write("<Style>")
            lineStyle.writeKml(out, urlFn=urlFn, color=self.getLineColor())
            out.write("</Style>")

        if animated:
            if self.iconStyle:
                out.write("<Style id=\"%s\">\n" % self.iconStyle.pk)
                self.iconStyle.writeKml(out, 0, urlFn=urlFn, color=self.getLineColor())
                out.write("</Style>\n")

        out.write("""
  <MultiGeometry>
    <LineString>
      <tessellate>1</tessellate>
      <coordinates>
""")
        lastPos = None
        breakDist = settings.GEOCAM_TRACK_START_NEW_LINE_DISTANCE_METERS
        for pos in positions:
            if lastPos and breakDist is not None:
                diff = geomath.calculateDiffMeters([lastPos.longitude, lastPos.latitude],
                                                   [pos.longitude, pos.latitude])
                dist = geomath.getLength(diff)
                if dist > breakDist:
                    # start new line string
                    out.write("""
      </coordinates>
    </LineString>
    <LineString>
      <tessellate>1</tessellate>
      <coordinates>
""")
            pos.writeCoordinatesKml(out)
            lastPos = pos

        out.write("""
      </coordinates>
    </LineString>
  </MultiGeometry>
</Placemark>
""")
        if animated:
            self.writeAnimatedPlacemarks(out, list(positions))
        out.write("</Folder>\n")

    def getInterpolatedPosition(self, utcDt):
        positions = PAST_POSITION_MODEL.get().objects.filter(track=self)

        # get closest position after utcDt
        afterPositions = positions.filter(timestamp__gte=utcDt).order_by('timestamp')
        if afterPositions.count():
            afterPos = afterPositions[0]
        else:
            return None
        afterDelta = timeDeltaTotalSeconds(afterPos.timestamp - utcDt)

        # special case -- if we have a position exactly matching utcDt
        if afterPos.timestamp == utcDt:
            return POSITION_MODEL.get().getInterpolatedPosition(utcDt, 1, afterPos, 0, afterPos)

        # get closest position before utcDt
        beforePositions = positions.filter(timestamp__lt=utcDt).order_by('-timestamp')
        if beforePositions.count():
            beforePos = beforePositions[0]
        else:
            return None
        beforeDelta = timeDeltaTotalSeconds(utcDt - beforePos.timestamp)
        delta = beforeDelta + afterDelta

        if delta > settings.GEOCAM_TRACK_INTERPOLATE_MAX_SECONDS:
            return None

        # interpolate
        beforeWeight = afterDelta / delta
        afterWeight = beforeDelta / delta
        return POSITION_MODEL.get().getInterpolatedPosition(utcDt, beforeWeight, beforePos, afterWeight, afterPos)

    def toMapDict(self):
        positions = self.getPositions()

        n = positions.count()
        if n < 2:
            return

        result = {}
        result['type'] = 'AbstractTrack'
        result['id'] = self.uuid
        color = self.getLineStyle().getHexColor()
        if color:
            result['color'] = color
        else:
            result['color'] = ''
        result['alpha'] = self.getLineStyle() .getAlpha()
        coordGroups = []
        timesGroups = []
        coords = []
        times = []

        lastPos = None
        breakDist = settings.GEOCAM_TRACK_START_NEW_LINE_DISTANCE_METERS
        for pos in positions:
            if lastPos and breakDist is not None:
                diff = geomath.calculateDiffMeters([lastPos.longitude, lastPos.latitude],
                                                   [pos.longitude, pos.latitude])
                dist = geomath.getLength(diff)
                if dist > breakDist:
                    # start new line string
                    if coords:
                        coordGroups.append(coords)
                        coords = []
                        timesGroups.append(times)
                        times = []
                coords.append([pos.longitude, pos.latitude])
                times.append(pos.timestamp)
            lastPos = pos
        coordGroups.append(coords)
        timesGroups.append(times)
        result['times'] = timesGroups
        result['coords'] = coordGroups
        return result


class Track(AbstractTrack):
    pass


class GenericTrack(AbstractTrack):
    """ This is for a track with a generic resource model, ie the resources can be of different types all extending AbstractResource
    For example camera, GPS, robot, etc.
    """
    generic_resource_content_type = models.ForeignKey(ContentType, related_name='generic_resource_content_type')
    generic_resource_id = models.PositiveIntegerField()
    generic_resource = GenericForeignKey('generic_resource_content_type', 'generic_resource_id')
 

class AbstractResourcePositionNoUuid(models.Model):
    """
    AbstractResourcePositionNoUuid is the most minimal position model
    geocamTrack supports.  Other apps building on geocamTrack may want
    to derive their position model from this.
    """
    track = models.ForeignKey(settings.GEOCAM_TRACK_TRACK_MODEL, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        abstract = True
        ordering = ('-timestamp',)

    def saveCurrent(self):
        # if there is an existing entry for this track, overwrite
        oldCpos = self.__class__.objects.filter(track=self.track)

        if len(oldCpos) > 1:
            logging.warning('more than one position for track %s',
                            self.track)

        if oldCpos:
            oldCposPk = oldCpos[0].pk
        else:
            oldCposPk = None
        self.pk = oldCposPk

        self.save()

    def getHeading(self):
        return None

    @classmethod
    def interp(cls, beforeWeight, beforeVal, afterWeight, afterVal):
        if beforeVal is None or afterVal is None:
            return None
        else:
            return beforeWeight * beforeVal + afterWeight * afterVal

    def getDistance(self, pos):
        diff = geomath.calculateDiffMeters([self.longitude, self.latitude],
                                           [pos.longitude, pos.latitude])

        return geomath.getLength(diff)

    @classmethod
    def getInterpolatedPosition(cls, utcDt, beforeWeight, beforePos, afterWeight, afterPos):
        if afterPos.getDistance(beforePos) > settings.GEOCAM_TRACK_INTERPOLATE_MAX_METERS:
            return None

        result = cls()
        result.track = beforePos.track
        result.timestamp = utcDt
        result.latitude = cls.interp(beforeWeight, beforePos.latitude, afterWeight, afterPos.latitude)
        result.longitude = cls.interp(beforeWeight, beforePos.longitude, afterWeight, afterPos.longitude)
        return result

    def writeCoordinatesKml(self, out):
        out.write('%.6f,%.6f,0\n' % (self.longitude, self.latitude))

    def getGeometry(self):
        return dict(type='Point',
                    coordinates=[self.longitude, self.latitude])

    def getProperties(self):
        timezone = pytz.timezone(settings.TIME_ZONE)
        localTime = timezone.localize(self.timestamp)
        props0 = dict(subtype='ResourcePosition',
                      displayName=self.track.name,
                      timestamp=localTime.isoformat(),
                      unixstamp=localTime.strftime("%s"))
        props = dict(((k, v) for k, v in props0.iteritems()
                      if v not in ('', None)))
        return props

    def getGeoJson(self):
        return dict(type='Feature',
                    id=self.track.uuid,
                    geometry=self.getGeometry(),
                    properties=self.getProperties())

    def getIconForIndex(self, index):
        if index is None or index >= 26:
            letter = ''
        else:
            letter = chr(65 + index)
        return 'http://maps.google.com/mapfiles/marker%s.png' % letter

    def getKml(self, index=None):
        coords = '%f,%f' % (self.longitude, self.latitude)
        #if self.altitude != None:
        #    coords += ',%f' % self.altitude
        return ('''
<Placemark id="%(id)s">
  <name>%(displayName)s</name>
  <description>%(displayName)s</description>
  <Point>
    <coordinates>%(coords)s</coordinates>
  </Point>
  <Style>
    <IconStyle>
      <Icon>
        <href>%(icon)s</href>
      </Icon>
    </IconStyle>
  </Style>
</Placemark>
'''
                % dict(id=self.track.uuid,
                       displayName=self.track.name,
                       coords=coords,
                       icon=self.getIconForIndex(index)))

    def toMapDict(self):
        result = {}
        result['type'] = "Position"
        result['id'] = self.pk
        result['lat'] = self.latitude
        result['lon'] = self.longitude
        result.update(self.getProperties())
        del(result['unixstamp'])
        del(result['subtype'])
        return result

    def __unicode__(self):
        return ('%s %s %s %s %s'
                % (self.__class__.__name__,
                   self.track.name,
                   self.timestamp,
                   self.latitude,
                   self.longitude))


class AbstractResourcePosition(AbstractResourcePositionNoUuid):
    """
    Adds a uuid field to AbstractResourcePositionNoUuid. 
    """
    uuid = UuidField()

    class Meta:
        abstract = True


class AbstractResourcePositionWithHeadingNoUuid(AbstractResourcePositionNoUuid):
    """
    Adds heading support to AbstractResourcePosition.
    """
    heading = models.FloatField(null=True, blank=True)

    def getHeading(self):
        return self.heading

    def getProperties(self):
        props = super(AbstractResourcePositionWithHeadingNoUuid, self).getProperties()
        props['heading'] = self.heading
        return props

    @classmethod
    def interpHeading(cls, beforeWeight, beforeHeading, afterWeight, afterHeading):
        h1 = cls.interp(beforeWeight, beforeHeading, afterWeight, afterHeading)
        if h1 is None:
            return None

        # there are two intervals between beforeHeading and
        # afterHeading on the orientation circle.  their midpoints
        # are h1 and h2.  we want the midpoint of the shorter interval.
        if (min(abs(h1 - beforeHeading),
                abs(h1 - afterHeading)) < 90):
            return h1
        else:
            h2 = h1 + 180
            if h2 > 360:
                h2 -= 360
            return h2

    @classmethod
    def getInterpolatedPosition(cls, utcDt, beforeWeight, beforePos, afterWeight, afterPos):
        result = (super(AbstractResourcePositionWithHeadingNoUuid, cls)
                  .getInterpolatedPosition(utcDt,
                                           beforeWeight, beforePos,
                                           afterWeight, afterPos))
        if result is not None:
            result.heading = cls.interpHeading(beforeWeight, beforePos.heading, afterWeight, afterPos.heading)
        return result

    class Meta:
        abstract = True


class AbstractResourcePositionWithHeading(AbstractResourcePositionWithHeadingNoUuid):
    """
    Adds a uuid field to AbstractResourcePositionWithHeadingNoUuid. 
    """
    uuid = UuidField()

    class Meta:
        abstract = True


class GeoCamResourcePosition(AbstractResourcePositionWithHeading):
    """
    This abstract position model has the set of fields we usually use with
    GeoCam.
    """
    altitude = models.FloatField(null=True)
    precisionMeters = models.FloatField(null=True)  # estimated position error

    class Meta:
        abstract = True


class ResourcePosition(GeoCamResourcePosition):
    pass


class PastResourcePosition(GeoCamResourcePosition):
    pass


class AbstractTrackedAsset(models.Model):
    """ Abstract class allowing you to have an asset which has a position.
    By default this position is not filled; it can be looked up and filled 
    """
    position = models.ForeignKey(settings.GEOCAM_TRACK_PAST_POSITION_MODEL, null=True, blank=True, related_name='asset_position')

    # If the position was looked for but not found, this will be false so we don't have to look again.
    position_not_found = models.NullBooleanField(null=True)

    def getEventTime(self):
        """ Override this method to return the event time for this tracked asset
        """
        raise NotImplementedError

    def getPosition(self):
        from geocamTrack.views import getClosestPosition
        if self.position:
            return self.position
        elif self.position_not_found == None and self.getEventTime():
            # populate the position
            timestamp=self.getEventTime()
            if not timestamp:
                return None
            foundPosition = getClosestPosition(timestamp=timestamp)
            if foundPosition:
                self.position = foundPosition
                self.position_not_found = False
            else:
                self.position_not_found = True
            self.save()
            return self.position

    class Meta:
        abstract = True


# a convenience class to hold a UTM position and distance, for storing averages of locations.
class Centroid():
    name = None
    latitude = None
    longitude = None
    distance = None

    def writeCentroidKml(self, out, lineStyle):
        linecolor = 'a0' + lineStyle.color[2:]
        fillcolor = '66' + lineStyle.color[2:]

        leftAngle, rightAngle = 0.0, 2 * pi

        UTMEasting, UTMNorthing, zoneNumber, zoneLetter = usng.LLtoUTM(self.latitude, self.longitude)

        polygonUtm = []

        theta = leftAngle
        dtheta = 3 * pi / 180
        while (theta < rightAngle):
            polygonUtm.append([UTMEasting + self.distance * sin(theta),
                               UTMNorthing + self.distance * cos(theta)])
            theta += dtheta

        # Convert UTM to lat/lon:
        polygonLatLon = [usng.UTMtoLL(e, n, zoneNumber, zoneLetter) for e, n in polygonUtm]

        # Write the KML
        out.write("""
<Placemark>
   <name>%s</name>
""" % self.name)

        # write the style
        out.write("""
    <Style>
       <LineStyle>
          <color>%s</color>
          <width>%d</width>
       </LineStyle>
       <PolyStyle>
          <color>%s</color>
       </PolyStyle>
    </Style>
""" % linecolor, lineStyle.width, fillcolor)

        #write the polygon
        out.write("""
    <Polygon>
        <tessellate>1</tessellate>
        <altitudeMode>relativeToGround</altitudeMode>
        <outerBoundaryIs>
        <LinearRing>
            <coordinates>
""")
        for ll in polygonLatLon:
            out.write('                %f,%f,5 ' % (ll.lon, ll.lat))

        out.write("""
            </coordinates>
        </LinearRing>
        </outerBoundaryIs>
    </Polygon>
</Placemark>
""")
