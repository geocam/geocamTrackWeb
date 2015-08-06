# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

import datetime

from geocamUtil.loader import LazyGetModelByName
from django.conf import settings

PAST_POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)


class PositionFilter(object):
    def __init__(self, distanceMeters, callback=lambda pos: pos.save()):
        self.distanceMeters = distanceMeters
        self.callback = callback

        pastPositions = PAST_POSITION_MODEL.get().objects.all().order_by('-timestamp')
        if pastPositions.count():
            self.previousPos = pastPositions[0]
        else:
            self.previousPos = None

    def add(self, pos):
        if self.previousPos is None or pos.getDistance(self.previousPos) > self.distanceMeters:
            self.callback(pos)
            self.previousPos = pos
            return True
        else:
            return False


class FancyPositionFilter(object):
    """
    The add() method accepts the sample you pass it if it is distant
    from the previous pose in position (@meters parameter), heading
    (@degrees parameter), or time (@seconds parameter).

    Any of the parameters can be None, in which case they are ignored.

    When a sample is accepted, the @callback parameter is invoked with
    the sample as an argument.
    """
    def __init__(self, meters=None, degrees=None, seconds=None, callback=lambda pos: pos.save()):
        self.meters = meters
        self.degrees = degrees
        self.seconds = datetime.timedelta(seconds=seconds)
        self.callback = callback

        pastPositions = PAST_POSITION_MODEL.get().objects.all().order_by('-timestamp')
        if pastPositions.count():
            self.previousPos = pastPositions[0]
        else:
            self.previousPos = None

    def add(self, pos):
        prev = self.previousPos
        accept = ((prev is None) or
                  (self.seconds is not None and pos.timestamp - prev.timestamp > self.seconds) or
                  (self.degrees is not None and abs(pos.heading - prev.heading) > self.degrees) or
                  (self.meters is not None and pos.getDistance(prev) > self.meters))
        if accept:
            self.callback(pos)
            self.previousPos = pos
            return True
        else:
            return False
