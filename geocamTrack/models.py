# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

import calendar
import datetime
import logging
from math import pi, cos, sin
import urllib

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
import pytz

from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from geocamUtil import TimeUtil
from geocamUtil import geomath
from geocamUtil.models.ExtrasDotField import ExtrasDotField
from geocamUtil.models.UuidField import UuidModel
from geocamUtil.loader import LazyGetModelByName

from geocamUtil.usng import usng
from xgds_core.models import SearchableModel, HasVehicle, HasFlight

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


class IconStyle(UuidModel):
    name = models.CharField(max_length=40, blank=True)
    url = models.CharField(max_length=1024, blank=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    scale = models.FloatField(default=1)
    color = models.CharField(max_length=16, blank=True,
                             help_text='Optional KML color specification, hex in AABBGGRR order')
    extras = ExtrasDotField()

    def __unicode__(self):
        return '%s %s' % (self.__class__.__name__, self.name)

    def writeKml(self, out, heading=None, urlFn=None, color=None):
        if not color:
            color = self.color
            try:
                int(self.color)
            except:
                try:
                    color = self.color()
                except:
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


class LineStyle(UuidModel):
    name = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=16, blank=True,
                             help_text='Optional KML color specification, hex in AABBGGRR order')
    width = models.PositiveIntegerField(default=1, null=True, blank=True)
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


# TODO update these if you are not using defaults
DEFAULT_FLIGHT_FIELD = lambda: models.OneToOneField('xgds_core.Flight',
                                                    related_name='track',
                                                    verbose_name=settings.XGDS_CORE_FLIGHT_MONIKER, blank=True,
                                                    null=True)
DEFAULT_VEHICLE_FIELD = lambda: models.ForeignKey('xgds_core.Vehicle',
                                                  related_name='%(app_label)s_%(class)s_related',
                                                  verbose_name=settings.XGDS_CORE_VEHICLE_MONIKER, blank=True,
                                                  null=True)
DEFAULT_ICON_STYLE_FIELD = lambda: models.ForeignKey(IconStyle, null=True, blank=True,
                                                     related_name='%(app_label)s_%(class)s_related')
DEFAULT_LINE_STYLE_FIELD = lambda: models.ForeignKey(LineStyle, null=True, blank=True,
                                                     related_name='%(app_label)s_%(class)s_related')


class AbstractTrack(SearchableModel, UuidModel, HasVehicle, HasFlight):
    """ This is for an abstract track with a FIXED vehicle model, ie all the tracks have like vehicles.
    """
    name = models.CharField(max_length=40, blank=True)
    iconStyle = 'set this to DEFAULT_ICON_STYLE_FIELD() or similar in derived classes'
    lineStyle = 'set this to DEFAULT_LINE_STYLE_FIELD() or similar in derived classes'
    extras = ExtrasDotField()

    def __init__(self, *args, **kwargs):
        super(AbstractTrack, self).__init__(*args, **kwargs)
        if self.id:
            self.pastposition_set = PAST_POSITION_MODEL.get().objects.filter(track_id=self.id)

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

    @property
    def lat(self):
        # This is a total hack to get tracks to show on the map after they were searched.
        return 1

    def get_tree_json(self):
        result = {"title": self.name,
                  "key": self.uuid,
                  "tooltip": "%s for %s" % (settings.GEOCAM_TRACK_TRACK_MONIKER, self.name),
                  "data": {
                      "json": reverse('geocamTrack_mapJsonTrack', kwargs={'uuid': str(self.uuid)}),
                      "kmlFile": reverse('geocamTrack_trackKml', kwargs={'trackName': self.name}),
                      "sseUrl": "",
                      "type": 'MapLink',
                  }
                  }

        return result

    def getIconStyle(self, pos):
        if hasattr(self, '_currentIcon'):
            return self._currentIcon

        # use specific style if given
        if self.iconStyle is not None:
            self._currentIcon = self.iconStyle
            return self.iconStyle

        # use pointer icon if we know the heading
        if pos.heading is not None:
            if not hasattr(self, '_pointerIcon'):
                self._pointerIcon = IconStyle.objects.get(name='pointer')
            self._currentIcon = self._pointerIcon
            return self._pointerIcon

        # use spot icon otherwise
        if not hasattr(self, '_defaultIcon'):
            self._defaultIcon = IconStyle.objects.get(name='default')
            self._defaultIcon.color = self.getLineStyleColor
            self._currentIcon = self._defaultIcon

        return self._currentIcon

    def getLineStyle(self):
        if self.lineStyle:
            return self.lineStyle
        return LineStyle.objects.get(name='default')

    def getLineStyleColor(self):
        if self.lineStyle:
            return self.lineStyle.color
        return LineStyle.objects.get(name='default').color

    def getIconColor(self, pos):
        try:
            currentIconStyle = self.getIconStyle(pos)
            int(str(currentIconStyle.color))
            return currentIconStyle.color
        except:
            try:
                return currentIconStyle.color()
            except:
                return str(currentIconStyle.color)

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
            now = datetime.datetime.now(pytz.utc)
            diff = now - pos.timestamp
            diffSecs = diff.days * 24 * 60 * 60 + diff.seconds
            if diffSecs >= settings.GEOCAM_TRACK_CURRENT_POSITION_AGE_MIN_SECONDS:
                age = TimeUtil.getTimeShort(pos.timestamp)
                ageStr = ' (%s)' % age
            ageStr += ' %s' % getTimeSpinner(datetime.datetime.now(pytz.utc))

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
                # end = self.getTimezone().localize(nextpos.timestamp)
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

    @classmethod
    def cls_type(cls):
        return settings.GEOCAM_TRACK_TRACK_MONIKER

    @property
    def color(self):
        color = self.getLineStyle().getHexColor()
        if color:
            return color
        return None

    @property
    def alpha(self):
        return self.getLineStyle().getAlpha()

    @property
    def icon_url(self):
        if self.iconStyle:
            return self.iconStyle.url
        return None

    @property
    def icon_color(self):
        if self.iconStyle:
            return self.iconStyle.color
        return None

    @property
    def icon_scale(self):
        if self.iconStyle:
            return self.iconStyle.scale
        return 1

    def buildTimeCoords(self):
        self.coordGroups = []
        self.timesGroups = []
        currentPositions = self.getPositions()
        if currentPositions.count() < 2:
            return
        if self.coordGroups:
            return
        coords = []
        times = []

        lastPos = None
        breakDist = settings.GEOCAM_TRACK_START_NEW_LINE_DISTANCE_METERS
        for pos in currentPositions:
            if lastPos and breakDist is not None:
                diff = geomath.calculateDiffMeters([lastPos.longitude, lastPos.latitude],
                                                   [pos.longitude, pos.latitude])
                dist = geomath.getLength(diff)
                if dist > breakDist:
                    # start new line string
                    if coords:
                        self.coordGroups.append(coords)
                        coords = []
                        self.timesGroups.append(times)
                        times = []
                coords.append(pos.coords_array)
                times.append(pos.timestamp)
            lastPos = pos
        self.coordGroups.append(coords)
        self.timesGroups.append(times)

    @property
    def coords(self):
        self.buildTimeCoords()
        if self.coordGroups:
            return self.coordGroups
        return None

    @property
    def times(self):
        self.buildTimeCoords()
        if self.timesGroups:
            return self.timesGroups
        return None

    def toMapDict(self):
        result = super(AbstractTrack, self).toMapDict()
        result['coords_array_order'] = PAST_POSITION_MODEL.get().coords_array_order()
        if 'vehicle' in result:
            if self.vehicle:
                result['vehicle'] = self.vehicle.name
            else:
                del result['vehicle']
        self.buildTimeCoords()
        if self.timesGroups:
            result['times'] = self.timesGroups

        if self.coordGroups:
            result['coords'] = self.coordGroups

        return result

    @classmethod
    def timesearchField(cls):
        return None

    @property
    def event_time(self):
        self.buildTimeCoords()
        if self.timesGroups:
            return self.timesGroups[0][0]
        return None

    @classmethod
    def getSearchFormFields(cls):
        return ['name', 'vehicle']


class Track(AbstractTrack, HasVehicle):
    iconStyle = DEFAULT_ICON_STYLE_FIELD()
    lineStyle = DEFAULT_LINE_STYLE_FIELD()
    flight = DEFAULT_FLIGHT_FIELD()
    vehicle = DEFAULT_VEHICLE_FIELD()

    def __unicode__(self):
        return '%s %s' % (self.__class__.__name__, self.name)


# class GenericTrack(AbstractTrack):
#     """ This is for a track with a generic vehicle model, ie the vehicles can be of different types all extending AbstractResource
#     For example camera, GPS, robot, etc.
#     """
#     generic_vehicle_content_type = models.ForeignKey(ContentType, related_name='generic_vehicle_content_type')
#     generic_vehicle_id = models.PositiveIntegerField()
#     generic_vehicle = GenericForeignKey('generic_vehicle_content_type', 'generic_vehicle_id')

# SUPER IMPORTANT.  If you reference an inherited class here you will get a circular dependency when this field is referenced in this file for any non-abstract class.
# DO NOT use this DEFAULT_TRACK_FIELD in this file unless you are sure that you are referencing a model defined in this submodule
DEFAULT_TRACK_FIELD = lambda: models.ForeignKey(settings.GEOCAM_TRACK_TRACK_MODEL, db_index=True, null=True, blank=True,
                                                related_name='%(app_label)s_%(class)s_related')


class TrackMixin(models.Model):
    """
    Mix this in to your model if it points to a track.
    Note that if you are not using geocamTrack.Track, you will have to redefine this member in your class.
    """
    track = DEFAULT_TRACK_FIELD()

    @property
    def has_track(self):
        # track field must exist and not be None
        return hasattr(self, 'track') and self.track

    @property
    def track_name(self):
        if self.has_track:
            return self.track.name
        return None

    @property
    def track_pk(self):
        if self.has_track:
            return self.track.pk
        return None

    @property
    def track_color(self):
        if self.has_track:
            return self.track.getLineStyleColor()
        return None

    @property
    def track_hexcolor(self):
        if self.has_track:
            kc = self.track.getLineStyleColor()
            nc = '%s%s%s' % (kc[6:], kc[4:6], kc[2:4])
            return nc
        return None

    class Meta:
        abstract = True


class AbstractResourcePosition(SearchableModel, TrackMixin):
    """
    AbstractResourcePosition is the most minimal position model
    geocamTrack supports.  Other apps building on geocamTrack may want
    to derive their position model from this. Server timestamp is intended to
    store time data arrived at server vs. timestamp which is ideally logged
    by the device collecting data in the field.
    """
    timestamp = models.DateTimeField(db_index=True, blank=True)
    serverTimestamp = models.DateTimeField(db_index=True, blank=True, default=timezone.now)
    latitude = models.FloatField(db_index=True, blank=True)
    longitude = models.FloatField(db_index=True, blank=True)

    class Meta:
        abstract = True
        ordering = ('-timestamp',)

    @property
    def lat(self):
        """ latitude """
        return self.latitude

    @property
    def lon(self):
        """ longitude """
        return self.longitude

    @property
    def head(self):
        """ heading """
        return None

    @classmethod
    def getFlattenedFields(cls):
        """Return the names of the fields to be used in a json dictionary.  These must have methods with the same name.
        This method must be defined on each non abstract position class.
        """
        return ['lat', 'lon']

    @classmethod
    def getSearchFormFields(cls):
        return ['track', 'track__vehicle', 'timestamp', 'latitude', 'longitude']

    @classmethod
    def cls_type(cls):
        return 'Position'

    @classmethod
    def timesearchField(self):
        return 'timestamp'

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
                      displayName=self.track.name if self.has_track else 'Pos',
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
        # if self.altitude != None:
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
                % dict(id=self.pk,
                       displayName=self.track.name if self.has_track else 'Pos',
                       coords=coords,
                       icon=self.getIconForIndex(index)))

    def getPosition(self):
        return self

    @property
    def displayName(self):
        if self.has_track:
            return self.track.name
        return str(self)

    @property
    def tz(self):
        if self.has_track and hasattr(self.track, 'timezone'):
            return self.track.timezone
        return settings.TIME_ZONE

    @classmethod
    def coords_array_order(cls):
        """
        Get the order of the values in the coords array
        :return:
        """
        return ['longitude', 'latitude']

    @property
    def coords_array(self):
        """
        Get the coordinates as an array.  Must be in expected order.
        Classes that extend this class and add other coordinates (altitude, depth, etc) must provide those coords.
        :return: [longitude, latitude]
        """
        return [self.longitude, self.latitude]

    def __unicode__(self):
        if self.has_track:
            return ('%s %s %s %s %s'
                    % (self.__class__.__name__,
                       self.track.name,
                       self.timestamp,
                       self.latitude,
                       self.longitude))
        else:
            return ('%s %s %s %s'
                    % (self.__class__.__name__,
                       self.timestamp,
                       self.latitude,
                       self.longitude))


class HeadingMixin(models.Model):
    """
    Adds heading support to AbstractResourcePosition.
    """
    heading = models.FloatField(null=True, blank=True, db_index=True)

    @property
    def head(self):
        """ heading """
        return self.heading

    def getHeading(self):
        return self.heading

    def setHeading(self, heading):
        self.heading = heading

    def getProperties(self):
        props = super(HeadingMixin, self).getProperties()
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
        result = (super(HeadingMixin, cls)
                  .getInterpolatedPosition(utcDt,
                                           beforeWeight, beforePos,
                                           afterWeight, afterPos))
        if result is not None:
            result.heading = cls.interpHeading(beforeWeight, beforePos.heading, afterWeight, afterPos.heading)
        return result

    class Meta:
        abstract = True


class AltitudeMixin(models.Model):
    """
    This mixin includes altitude, typically in meters
    """
    altitude = models.FloatField(blank=True, null=True, db_index=True)

    @property
    def alt(self):
        """ altitude """
        return self.altitude

    class Meta:
        abstract = True


class AltitudeResourcePosition(AbstractResourcePosition, HeadingMixin, AltitudeMixin):
    precisionMeters = models.FloatField(blank=True, null=True, db_index=True)  # estimated position error

    class Meta:
        abstract = True


class YPRMixin(models.Model):
    """
    This mixin includes yaw pitch and roll
    """
    yaw = models.FloatField(blank=True, null=True, db_index=True)
    pitch = models.FloatField(blank=True, null=True, db_index=True)
    roll = models.FloatField(blank=True, null=True, db_index=True)

    def setHeading(self, heading):
        """
        Set the heading, in this case yaw
        :param heading:
        :return:
        """
        self.yaw = heading

    @property
    def heading(self):
        return self.yaw

    @property
    def head(self):
        """ altitude """
        return self.yaw

    class Meta:
        abstract = True


class DepthMixin(models.Model):
    """
    This mixin includes depth.  Typically this is a positive value, in meters (ie +10.5 = 10.5 meters deep.
    """
    depth = models.FloatField(blank=True, null=True, db_index=True)

    class Meta:
        abstract = True


class ResourcePosition(AltitudeResourcePosition, TrackMixin):

    @classmethod
    def coords_array_order(cls):
        """
        Get the order of the values in the coords array
        :return:
        """
        return ['longitude', 'latitude', 'altitude', 'heading']

    @property
    def coords_array(self):
        """
        Get the coordinates as an array.  Must be in expected order.
        Classes that extend this class and add other coordinates (altitude, depth, etc) must provide those coords.
        :return: [longitude, latitude, altitude, heading]
        """
        return [self.longitude, self.latitude, self.altitude, self.heading]


    @classmethod
    def getFlattenedFields(cls):
        """Return the names of the fields to be used in a json dictionary.  These must have methods with the same name.
        This method must be defined on each non abstract position class.
        """
        return ['lat', 'lon', 'alt', 'head']


class PastResourcePosition(AltitudeResourcePosition, TrackMixin):

    @classmethod
    def getSearchFormFields(cls):
        return ['track', 'track__vehicle', 'timestamp', 'latitude', 'longitude', 'altitude']

    @classmethod
    def coords_array_order(cls):
        """
        Get the order of the values in the coords array
        :return:
        """
        return ['longitude', 'latitude', 'altitude', 'heading']

    @property
    def coords_array(self):
        """
        Get the coordinates as an array.  Must be in expected order.
        Classes that extend this class and add other coordinates (altitude, depth, etc) must provide those coords.
        :return: [longitude, latitude, altitude, heading]
        """
        return [self.longitude, self.latitude, self.altitude, self.heading]

    @classmethod
    def getFlattenedFields(cls):
        """Return the names of the fields to be used in a json dictionary.  These must have methods with the same name.
        This method must be defined on each non abstract position class.
        """
        return ['lat', 'lon', 'alt', 'head']


class ResourcePose(AbstractResourcePosition, AltitudeMixin, YPRMixin, TrackMixin):

    @classmethod
    def coords_array_order(cls):
        """
        Get the order of the values in the coords array
        :return:
        """
        return ['longitude', 'latitude', 'altitude', 'yaw', 'pitch', 'roll']

    @property
    def coords_array(self):
        """
        Get the coordinates as an array.  Must be in expected order.
        Classes that extend this class and add other coordinates (altitude, depth, etc) must provide those coords.
        :return: [longitude, latitude, altitude, yaw, pitch, roll]
        """
        return [self.longitude, self.latitude, self.altitude, self.yaw, self.pitch, self.roll]

    @classmethod
    def getFlattenedFields(cls):
        """Return the names of the fields to be used in a json dictionary.  These must have methods with the same name.
        This method must be defined on each non abstract position class.
        """
        return ['lat', 'lon', 'alt', 'yaw', 'pitch', 'roll']


class PastResourcePose(AbstractResourcePosition, AltitudeMixin, YPRMixin, TrackMixin):

    @classmethod
    def getSearchFormFields(cls):
        return ['track', 'track__vehicle', 'timestamp', 'latitude', 'longitude', 'altitude', 'yaw', 'pitch', 'roll']

    @classmethod
    def coords_array_order(cls):
        """
        Get the order of the values in the coords array
        :return:
        """
        return ['longitude', 'latitude', 'altitude', 'yaw', 'pitch', 'roll']

    @property
    def coords_array(self):
        """
        Get the coordinates as an array.  Must be in expected order.
        Classes that extend this class and add other coordinates (altitude, depth, etc) must provide those coords.
        :return: [longitude, latitude, altitude, yaw, pitch, roll]
        """
        return [self.longitude, self.latitude, self.altitude, self.yaw, self.pitch, self.roll]

    @classmethod
    def getFlattenedFields(cls):
        """Return the names of the fields to be used in a json dictionary.  These must have methods with the same name.
        This method must be defined on each non abstract position class.
        """
        return ['lat', 'lon', 'alt', 'yaw', 'pitch', 'roll']


class ResourcePoseDepth(AbstractResourcePosition, AltitudeMixin, YPRMixin, TrackMixin, DepthMixin):

    @classmethod
    def coords_array_order(cls):
        """
        Get the order of the values in the coords array
        :return:
        """
        return ['longitude', 'latitude', 'altitude', 'yaw', 'pitch', 'roll', 'depth']

    @property
    def coords_array(self):
        """
        Get the coordinates as an array.  Must be in expected order.
        Classes that extend this class and add other coordinates (altitude, depth, etc) must provide those coords.
        :return: [longitude, latitude, altitude, yaw, pitch, roll, depth]
        """
        return [self.longitude, self.latitude, self.altitude, self.yaw, self.pitch, self.roll, self.depth]

    @classmethod
    def getFlattenedFields(cls):
        """Return the names of the fields to be used in a json dictionary.  These must have methods with the same name.
        This method must be defined on each non abstract position class.
        """
        return ['lat', 'lon', 'alt', 'yaw', 'pitch', 'roll', 'depth']


class PastResourcePoseDepth(AbstractResourcePosition, AltitudeMixin, YPRMixin, TrackMixin, DepthMixin):

    @classmethod
    def getSearchFormFields(cls):
        return ['track', 'track__vehicle', 'timestamp', 'latitude', 'longitude', 'altitude', 'depth', 'yaw', 'pitch', 'roll']

    @classmethod
    def coords_array_order(cls):
        """
        Get the order of the values in the coords array
        :return:
        """
        return ['longitude', 'latitude', 'altitude', 'yaw', 'pitch', 'roll', 'depth']

    @property
    def coords_array(self):
        """
        Get the coordinates as an array.  Must be in expected order.
        Classes that extend this class and add other coordinates (altitude, depth, etc) must provide those coords.
        :return: [longitude, latitude, altitude, yaw, pitch, roll, depth]
        """
        return [self.longitude, self.latitude, self.altitude, self.yaw, self.pitch, self.roll, self.depth]

    @classmethod
    def getFlattenedFields(cls):
        """Return the names of the fields to be used in a json dictionary.  These must have methods with the same name.
        This method must be defined on each non abstract position class.
        """
        return ['lat', 'lon', 'alt', 'yaw', 'pitch', 'roll', 'depth']


PAST_POSITION_FIELD = lambda: models.ForeignKey(PastResourcePosition,
                                                related_name='%(app_label)s_%(class)s_related',
                                                blank=True, null=True)

PAST_POSITION_FIELD = lambda: models.ForeignKey(PastResourcePosition,
                                                related_name='%(app_label)s_%(class)s_related',
                                                blank=True, null=True)


class AbstractTrackedAsset(models.Model):
    """ Abstract class allowing you to have an asset which has a position.
    By default this position is not filled; it can be looked up and filled
    """
    position = PAST_POSITION_FIELD()

    # If the position was looked for but not found, this will be false so we don't have to look again.
    position_not_found = models.NullBooleanField(null=True)

    def getEventTime(self):
        """ Override this method to return the event time for this tracked asset
        """
        raise NotImplementedError

    def getPosition(self):
        from geocamTrack.utils import getClosestPosition
        if self.position:
            return self.position
        elif self.position_not_found == None and self.getEventTime():
            # populate the position
            timestamp = self.getEventTime()
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
        while theta < rightAngle:
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

        # write the polygon
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
