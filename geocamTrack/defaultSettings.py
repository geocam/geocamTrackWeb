# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

GEOCAM_TRACK_RESOURCE_MODEL = 'geocamTrack.Resource'
GEOCAM_TRACK_RESOURCE_VERBOSE_NAME = 'Resource'
GEOCAM_TRACK_TRACK_MODEL = 'geocamTrack.Track'
GEOCAM_TRACK_POSITION_MODEL = 'geocamTrack.ResourcePosition'
GEOCAM_TRACK_PAST_POSITION_MODEL = 'geocamTrack.PastResourcePosition'
GEOCAM_TRACK_ICON_STYLE_MODEL = 'geocamTrack.IconStyle'
GEOCAM_TRACK_LINE_STYLE_MODEL = 'geocamTrack.LineStyle'

# note: currently all of these tracking views have caching enabled where
# the cache period is set to the refresh period minus epsilon

GEOCAM_TRACK_START_NEW_LINE_DISTANCE_METERS = 5
GEOCAM_TRACK_RECENT_TRACK_REFRESH_TIME_SECONDS = 5
GEOCAM_TRACK_CURRENT_POS_REFRESH_TIME_SECONDS = 1
GEOCAM_TRACK_SHOW_CURRENT_POSITION_AGE = False
GEOCAM_TRACK_CURRENT_POSITION_AGE_MIN_SECONDS = 60

GEOCAM_TRACK_OLD_TRACK_REFRESH_TIME_SECONDS = 300
GEOCAM_TRACK_RECENT_TRACK_LENGTH_SECONDS = 3 * 300

# When interpolating to generate the position for a timestamp, do not
# interpolate if the positions before and after the timestamp are
# farther than this distance apart.
GEOCAM_TRACK_INTERPOLATE_MAX_METERS = 20

# When interpolating to generate the position for a timestamp, do not
# interpolate if the positions before and after the timestamp have times
# longer than this apart.
GEOCAM_TRACK_INTERPOLATE_MAX_SECONDS = 8 * 60 * 60

# All timestamps in geocamTrack data tables should always use the UTC
# time zone.  GEOCAM_TRACK_OPS_TIME_ZONE is currently used only to
# choose how to split up days in the daily track index. We split at
# midnight in the specified time zone. Since ops are usually idle at
# night and we want to split during the idle period, we usually set this
# to the time zone where most ops actually occur.
GEOCAM_TRACK_OPS_TIME_ZONE = 'UTC'

GEOCAM_TRACK_FEED_NAME = 'GeoCam Track'

# include this in your siteSettings.py BOWER_INSTALLED_APPS
GEOCAM_TRACK_BOWER_INSTALLED_APPS = ('jquery-mobile',
                                     'google-maps-utility-library-v3-infobubble',
                                     'klass=git://github.com/ded/klass.git'
                                     )

XGDS_MAP_SERVER_JS_MAP = {}
XGDS_MAP_SERVER_JS_MAP['AbstractTrack'] = {'ol': 'geocamTrack/js/olTrackMap.js',
                                           'model': GEOCAM_TRACK_TRACK_MODEL,
                                           'hiddenColumns': ['type', 'color', 'alpha', 'times', 'coords']}

# override to include SSE; right now we are based on django-sse-wrapper
XGDS_SSE = False