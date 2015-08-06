# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

from django.db import connection

from geocamUtil.loader import LazyGetModelByName
from django.conf import settings

PAST_POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)


def getDatesWithPositionData():
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT DATE(CONVERT_TZ(timestamp, 'UTC', '%s')) FROM %s"
                       % (settings.GEOCAM_TRACK_OPS_TIME_ZONE,
                          PAST_POSITION_MODEL.get()._meta.db_table))
        dates = [fields[0] for fields in cursor.fetchall()]
        return dates
    except:
        return None
