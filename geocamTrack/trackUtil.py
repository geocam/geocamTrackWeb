# __BEGIN_LICENSE__
#Copyright © 2015, United States Government, as represented by the 
#Administrator of the National Aeronautics and Space Administration. 
#All rights reserved.
#
#The xGDS platform is licensed under the Apache License, Version 2.0 
#(the "License"); you may not use this file except in compliance with the License. 
#You may obtain a copy of the License at 
#http://www.apache.org/licenses/LICENSE-2.0.
#
#Unless required by applicable law or agreed to in writing, software distributed 
#under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR 
#CONDITIONS OF ANY KIND, either express or implied. See the License for the 
#specific language governing permissions and limitations under the License.
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
