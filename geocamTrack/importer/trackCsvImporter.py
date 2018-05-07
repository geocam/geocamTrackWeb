# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
#
# The xGDS platform is licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
# __END_LICENSE__

"""
Utilities for loading track csv data, including creation of the track if necessary.
Supports transformation from UTM to Lat Long, which is our native storage format
"""


from pyproj import Proj

from django.conf import settings

from xgds_core.importer import csvImporter
from geocamTrack.trackUtil import get_or_create_track, get_next_available_track_name
from geocamUtil.loader import LazyGetModelByName

TRACK_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_TRACK_MODEL)


class TrackCsvImporter(csvImporter.CsvImporter):

    def __init__(self, yaml_file_path, csv_file_path, vehicle_name=None, flight_name=None, defaults=None,
                 track_name=None, utm=False, utm_zone=None, utm_south=False, force=False):
        """
         Initialize with a path to a configuration yaml file and a path to a csv file
         :param yaml_file_path: The path to the yaml configuration file for import
         :param csv_file_path: The path to the csv file to import
         :param vehicle_name: The name of the vehicle
         :param flight_name: The name of the flight
         :param defaults: Optional additional defaults to add to objects
         :param track_name: The name of the track
         :param utm: True to import the coordinates in utm, False otherwise
         :param utm_zone: The name of the UTM zone, ie '10S'
         :param utm_south: True if the UTM zone is southern hemisphere.
         :param force: True to force import even if the data was already imported.  This will duplicate data.
         :return: the imported items
         """
        self.track = None
        self.utm = utm
        self.utm_zone = utm_zone
        if self.utm:
            # convert northing easting to latitude longitude
            south = ''
            if utm_south:
                south = '+south'
            self.projection = Proj("+proj=utm +zone=%s, %s +ellps=WGS84 +datum=WGS84 +units=m +no_defs" % (utm_zone, south))

        super(TrackCsvImporter, self).__init__(yaml_file_path, csv_file_path, vehicle_name, flight_name, defaults,
                                               force)
        if not self.flight:
            self.get_or_create_flight(self.get_first_row())
        self.get_or_create_track(track_name)

    def get_or_create_track(self, track_name=None):
        """
        Use the timestamp in the row to look up or create a track name.
        :param track_name: the name of the track
        """
        if not track_name:
            if self.flight:
                track_name = self.flight.name
            else:
                track_name = get_next_available_track_name(self.get_start_time().strftime('%Y%m%d'), self.vehicle.name)
        self.track = get_or_create_track(track_name, self.vehicle, self.flight)
        if self.track:
            self.config['defaults'].update({'track_id': self.track.id})
        else:
            raise Exception('Could not create track')

    def update_row(self, row):
        """
        Update the row, in this case converting utm to lat long if necessary
        :param row:
        :return:
        """
        row = super(TrackCsvImporter, self).update_row(row)
        if self.utm and self.projection:
            easting = None
            if 'easting' in row:
                easting = row['easting']
                del row['easting']
            elif 'east' in row:
                easting = row['east']
                del row['east']
            elif 'longitude' in row:
                easting = row['longitude']
            northing = None
            if 'northing' in row:
                northing = row['northing']
                del row['northing']
            elif 'north' in row:
                northing = row['north']
                del row['north']
            elif 'latitude' in row:
                northing = row['latitude']

            row['longitude'], row['latitude'] = self.projection(easting, northing, inverse=True)
        return row








