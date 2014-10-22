# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.db import connection

from geocamUtil.loader import LazyGetModelByName
from geocamTrack import settings

PAST_POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)


def getDatesWithPositionData():
    cursor = connection.cursor()
    cursor.execute("SELECT DISTINCT DATE(CONVERT_TZ(timestamp, 'UTC', '%s')) FROM %s"
                   % (settings.GEOCAM_TRACK_OPS_TIME_ZONE,
                      PAST_POSITION_MODEL.get()._meta.db_table))
    dates = [fields[0] for fields in cursor.fetchall()]
    return dates
