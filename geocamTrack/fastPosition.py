# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

"""
The FastPosition class enables very efficient
getInterpolatedPosition(timestamp) queries, provided you are running a
large number of queries sorted in order of increasing timestamp.

It works by keeping a cache of position records and an index pointer
that tracks which position records in the cache bracketed the last
timestamp query.

Since the next query is likely to have a timestamp just a little bit
later than the last query, it's a fast operation to scan forward through
the records looking for ones that bracket the new timestamp.  We need to
run another database query only when the query timestamp runs past the
interval stored in the cache.

If you are running N timestamp queries in increasing order and have K
position records covering that time span, the asymptotic run time upper
bound is approximately O(N + K), which is as good as you can possibly
get.

The FastPosition class should give correct interpolated positions even
if you don't run timestamp queries in increasing order, but the
performance could be very bad.
"""

import datetime

from geocamUtil.loader import LazyGetModelByName
from geocamTrack import settings

PAST_POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)
POSITION_CACHE_SIZE = 10000


def timeDeltaTotalSeconds(delta):
    return 86400 * delta.days + delta.seconds + 1e-6 * delta.microseconds


class FastPosition(object):
    def __init__(self, track):
        self.track = track
        self.baseQuery = (PAST_POSITION_MODEL.get().objects
                          .filter(track=self.track))
        self.cache = []
        self.cacheMin = None
        self.cacheMax = None
        self.cacheIndex = None
        self.globalMin = (self.baseQuery
                          .order_by('timestamp')
                          [:1][0].timestamp)
        self.globalMax = (self.baseQuery
                          .order_by('-timestamp')
                          [:1][0].timestamp)
        #print vars(self)
        #sys.exit(1)

    def populateCache(self, utcDt):
        maxDelta = datetime.timedelta(seconds=settings.GEOCAM_TRACK_INTERPOLATE_MAX_SECONDS)
        startTime = utcDt - maxDelta
        self.cache = list(self.baseQuery
                          .order_by('timestamp')
                          .filter(timestamp__gte=startTime)[:POSITION_CACHE_SIZE])
        if self.cache:
            self.cacheMin = startTime
            self.cacheMax = self.cache[-1].timestamp
            self.cacheIndex = 0
        else:
            self.cacheMin = None
            self.cacheMax = None
            self.cacheIndex = None

    def getBracketingPositions(self, utcDt):
        if not self.globalMin <= utcDt <= self.globalMax:
            # bracketing values are not in the db at all
            return None, None
        elif not self.cache or not self.cacheMin <= utcDt <= self.cacheMax:
            # bracketing values are not in the cache but are in the db... run a query
            self.populateCache(utcDt)
        elif not self.cache[self.cacheIndex].timestamp <= utcDt:
            # index pointer is past utcDt... reset the index
            self.cacheIndex = 0

        if not self.cache[self.cacheIndex].timestamp <= utcDt:
            # previous position record is not within max interpolation time
            return None, None

        # do fast search in cache
        n = len(self.cache)
        for i in xrange(self.cacheIndex, n - 1):
            nxt = self.cache[i + 1]
            if utcDt <= nxt.timestamp:
                self.cacheIndex = i
                return self.cache[i], self.cache[i + 1]

    def getInterpolatedPosition(self, utcDt):
        beforePos, afterPos = self.getBracketingPositions(utcDt)

        # no bracketing values
        if beforePos is None:
            return None

        # if the before value is an exact match
        if beforePos.timestamp == utcDt:
            return (PAST_POSITION_MODEL.get().getInterpolatedPosition
                    (utcDt, 1, afterPos, 0, afterPos))

        afterDelta = timeDeltaTotalSeconds(afterPos.timestamp - utcDt)
        beforeDelta = timeDeltaTotalSeconds(utcDt - beforePos.timestamp)
        delta = beforeDelta + afterDelta

        # bracketing values aren't close enough
        if delta > settings.GEOCAM_TRACK_INTERPOLATE_MAX_SECONDS:
            return None

        # interpolate
        beforeWeight = afterDelta / delta
        afterWeight = beforeDelta / delta
        return (PAST_POSITION_MODEL.get().getInterpolatedPosition
                (utcDt, beforeWeight, beforePos, afterWeight, afterPos))
