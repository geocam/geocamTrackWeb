# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

import math

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from geocamUtil.loader import LazyGetModelByName

TRACK_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_TRACK_MODEL)
PAST_POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)


def getClosestPosition(track=None, timestamp=None, max_time_difference_seconds=settings.GEOCAM_TRACK_INTERPOLATE_MAX_SECONDS, resource=None):
    """
    Look up the closest location, with a 1 minute default maximum difference.
    Track is optional but it will be a more efficient query if you limit it by track
    also if you have multiple tracks at the same time from different vehicles, you really need to pass in a track.
    TODO this will not work for GenericTrack
    """
    if not timestamp:
        return None
    foundPosition = None

    try:
        if not track:
            foundPositions = PAST_POSITION_MODEL.get().objects.filter(timestamp=timestamp)
        elif resource:
            foundPositions = PAST_POSITION_MODEL.get().objects.filter(track__resource=resource, timestamp=timestamp)
        else:
            foundPositions = PAST_POSITION_MODEL.get().objects.filter(track=track, timestamp=timestamp)
        # take the first one.
        if foundPositions:
            foundPosition = foundPositions[0]
    except ObjectDoesNotExist:
        pass

    if not foundPosition:
        tablename = PAST_POSITION_MODEL.get()._meta.db_table
        query = "select * from " + tablename + ' pos'
        if track:
            query = query + " where " + "track_id = '" + str(track.pk) + "'"
        elif resource:
            query = query + ", " + TRACK_MODEL.get()._meta.db_table + " track"
            query = query + " where"
#             query = query + " pos.track_id is not null and"
            query = query + " pos.track_id=track." + TRACK_MODEL.get()._meta.pk.name
            query = query + " and track.resource_id = '" + str(resource.pk) + "'"
            
        query = query + " order by abs(timestampdiff(second, '" + timestamp.isoformat() + "', timestamp)) limit 1;"
        posAtTime = (PAST_POSITION_MODEL.get().objects.raw(query))
        posList = list(posAtTime)
        if posList:
            foundPosition = posAtTime[0]
            if foundPosition and foundPosition.timestamp:
                if (foundPosition.timestamp > timestamp):
                    delta = (foundPosition.timestamp - timestamp)
                else:
                    delta = (timestamp - foundPosition.timestamp)
                if math.fabs(delta.total_seconds()) > max_time_difference_seconds:
                    foundPosition = None
            else:
                foundPosition = None
        else:
            foundPosition = None
    return foundPosition
