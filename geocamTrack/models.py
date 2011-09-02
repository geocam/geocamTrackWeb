# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import sys

from django.db import models
from django.contrib.auth.models import User
import pytz

from geocamUtil.models.UuidField import UuidField
from geocamUtil.models.ExtrasDotField import ExtrasDotField
from geocamUtil import geomath
from geocamUtil import TimeUtil

from geocamTrack import settings

latestRequestG = None
        
def getModClass(name):
    """converts 'app_name.ModelName' to ['stuff.module', 'ClassName']"""
    try:
        dot = name.rindex('.')
    except ValueError:
        return name, ''
    return name[:dot], name[dot+1:]

def getModelByName(qualifiedName):
    """
    converts 'module_name.ClassName' to a class object
    """
    appName, className = qualifiedName.split('.', 1)
    modelsName = '%s.models' % appName
    __import__(modelsName)
    mod = sys.modules[modelsName]
    return getattr(mod, className)

class Resource(models.Model):
    name = models.CharField(max_length=32)
    user = models.ForeignKey(User, null=True, blank=True)
    uuid = UuidField()
    extras = ExtrasDotField()

    def __unicode__(self):
        return '%s %s' % (self.__class__.__name__, self.name)

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

    def writeKml(self, out, heading=None):
        if self.color:
            colorStr = '<color>%s</color>' % self.color
        else:
            colorStr = ''
        if self.scale != 1:
            scaleStr = '<scale>%s</scale>' % self.scale
        else:
            scaleStr = ''
        if heading != None:
            headingStr = '<heading>%s</heading>' % heading
        else:
            headingStr = ''
        out.write("""
<IconStyle>
  %(headingStr)s
  %(colorStr)s
  <Icon>
    %(scaleStr)s
    <href>%(url)s</href>
  </Icon>
</IconStyle>
""" % dict(url=latestRequestG.build_absolute_uri(self.url),
           scaleStr=scaleStr,
           colorStr=colorStr,
           headingStr=headingStr))

class LineStyle(models.Model):
    name = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=16, blank=True,
                             help_text='Optional KML color specification, hex in AABBGGRR order')
    width = models.PositiveIntegerField(default=1, null=True, blank=True)
    uuid = UuidField()
    extras = ExtrasDotField()

    def __unicode__(self):
        return '%s %s' % (self.__class__.__name__, self.name)

    def writeKml(self, out):
        if self.color:
            colorStr = '<color>%s</color>' % self.color
        else:
            colorStr = ''
        if self.width != None:
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

class Track(models.Model):
    name = models.CharField(max_length=40, blank=True)
    resource = models.ForeignKey(settings.GEOCAM_TRACK_RESOURCE_MODEL)
    iconStyle = models.ForeignKey(settings.GEOCAM_TRACK_ICON_STYLE_MODEL, null=True, blank=True)
    lineStyle = models.ForeignKey(settings.GEOCAM_TRACK_LINE_STYLE_MODEL, null=True, blank=True)
    uuid = UuidField()
    extras = ExtrasDotField()

    def __unicode__(self):
        return '%s %s' % (self.__class__.__name__, self.name)

    def getPositions(self):
        PositionModel = getModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)
        return PositionModel.objects.filter(track=self)

    def getCurrentPositions(self):
        PositionModel = getModelByName(settings.GEOCAM_TRACK_POSITION_MODEL)
        return PositionModel.objects.filter(track=self)

    def writeCurrentKml(self, out, positions=None, iconStyle=None):
        if positions == None:
            positions = self.getCurrentPositions()
        if positions:
            pos = positions[0]
        else:
            return
        if iconStyle == None:
            iconStyle = self.iconStyle
        age = TimeUtil.getTimeShort(pos.timestamp)

        out.write("""
<Placemark>
  <name>%(name)s (%(age)s)</name>
""" % dict(name=self.name, age=age))
        if iconStyle:
            out.write("<Style>\n")
            iconStyle.writeKml(out, pos.getHeading())
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

    def writeTrackKml(self, out, positions=None, lineStyle=None):
        if positions == None:
            positions = self.getPositions()
        if lineStyle == None:
            lineStyle = self.lineStyle

        if len(positions) < 2:
            # kml LineString requires 2 or more positions
            return

        out.write("""
<Placemark>
  <name>%(name)s path</name>
""" % dict(name=self.name))
        if lineStyle:
            out.write("<Style>")
            lineStyle.writeKml(out)
            out.write("</Style>")

        out.write("""
  <MultiGeometry>
    <LineString>
      <tessellate>1</tessellate>
      <coordinates>
""")
        lastPos = None
        breakDist = settings.GEOCAM_TRACK_START_NEW_LINE_DISTANCE_METERS
        for pos in positions:
            if lastPos and breakDist != None:
                diff = geomath.calculateDiffMeters([lastPos.longitude, lastPos.latitude],
                                                   [pos.longitude, pos.latitude])
                dist = geomath.getLength(diff)
                print 'dist=%s breakDist=%s' % (dist, breakDist)
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

class AbstractResourcePosition(models.Model):
    track = models.ForeignKey(settings.GEOCAM_TRACK_TRACK_MODEL, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    uuid = UuidField()

    def getHeading(self):
        return None

    def writeCoordinatesKml(self, out):
        out.write('%.6f,%.6f,0\n' % (self.longitude, self.latitude))

    def getGeometry(self):
        return dict(type='Point',
                    coordinates=[self.longitude, self.latitude])

    def getProperties(self):
        timezone = pytz.timezone(settings.TIME_ZONE)
        localTime = timezone.localize(self.timestamp)
        props0 = dict(subtype='ResourcePosition',
                      userName=self.resource.user.username,
                      displayName=self.resource.getUserNameAbbreviated(),
                      timestamp=localTime.isoformat(),
                      unixstamp=localTime.strftime("%s"))
        props = dict(((k, v) for k, v in props0.iteritems()
                      if v not in ('', None)))
        return props

    def getGeoJson(self):
        return dict(type='Feature',
                    id=self.resource.uuid,
                    geometry=self.getGeometry(),
                    properties=self.getProperties())

    def getIconForIndex(self, index):
        if index == None or index >= 26:
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
                % dict(id='resource-' + self.resource.user.username,
                       displayName=self.resource.getUserNameAbbreviated(),
                       coords=coords,
                       icon=self.getIconForIndex(index)))

    def __unicode__(self):
        return ('%s %s %s %s %s'
                % (self.__class__.__name__,
                   unicode(self.track),
                   self.timestamp,
                   self.latitude,
                   self.longitude))

    class Meta:
        abstract = True

class ResourcePosition(AbstractResourcePosition):
    pass

class PastResourcePosition(AbstractResourcePosition):
    pass

# If settings.GEOCAM_TRACK_LATITUDE_ENABLED is False, we don't need
# these models... but we'll keep them in at the DB level anyway, to
# avoid syncdb asking to delete and re-add them when we change the
# settings.
from geocamTrack.latitude.models import *
