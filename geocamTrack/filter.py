# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from geocamTrack.models import getModelByName
from geocamTrack import settings

PAST_POSITION_MODEL = getModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)

class PositionFilter(object):
    def __init__(self, distanceMeters, callback=lambda pos: pos.save()):
        self.distanceMeters = distanceMeters
        self.callback = callback

        pastPositions = PAST_POSITION_MODEL.objects.all().order_by('-timestamp')
        if pastPositions.count():
            self.previousPos = pastPositions[0]
        else:
            self.previousPos = None

    def add(self, pos):
        if self.previousPos is not None and pos.getDistance(self.previousPos) > self.distanceMeters:
            self.callback(pos)
            self.previousPos = pos
            return True
        else:
            return False
