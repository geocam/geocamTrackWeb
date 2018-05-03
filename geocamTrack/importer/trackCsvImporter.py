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
Utilities for loading track csv data, including creation of the track if necessary
"""

from dateutil.parser import parse as dateparser
from django.utils import timezone
from django.conf import settings

from xgds_core.importer import csvImporter
from geocamTrack.trackUtil import create_track, get_next_available_track_name
from geocamUtil.loader import LazyGetModelByName

TRACK_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_TRACK_MODEL)


def lookup_track_name(track_name, vehicle, flight):
    """ Look up the track by name
    :param track_name: The name of the track
    :return: the found track, or None
    """
    track = create_track(track_name, vehicle, flight)
    if track_name:
        try:
            track = TRACK_MODEL.get().objects.get(name=track_name)
        except:
            pass
    return track


def calculate_trackname(vehicle, row):
    """
        Use the timestamp in the row to look up or create a flight.
        :param vehicle: the vehicle
        :param row: the first row of the csv
        :return: the flight
        """
    if 'timestamp' in row:
        the_time = dateparser(row['timestamp'])
    else:
        the_time = timezone.now()
    return get_next_available_track_name(the_time.strftime('%Y%m%d'), vehicle.name)


def do_import(yaml_file_path, csv_file_path, vehicle_name=None, flight_name=None, defaults={}, track_name=None, force=False):
    """
    Do an import with a path to a configuration yaml file and a path to a csv file
    :param yaml_file_path: The path to the yaml configuration file for import
    :param csv_file_path: The path to the csv file to import
    :param vehicle_name: The name of the vehicle
    :param flight_name: The name of the flight
    :param defaults: Optional additional defaults to add to objects
    :param track_name: The name of the track
    :return: the imported items
    """

    config = csvImporter.configure(yaml_file_path, csv_file_path, vehicle_name, flight_name, defaults, force)

    if not track_name:
        if flight_name:
            track_name = flight_name
        else:
            if config['flight']:
                track_name = config['flight'].name
            else:
                # try to make the flight
                row = list(config['csv_reader'])[0]
                config['csv_file'].seek(0)
                config['flight'] = csvImporter.get_or_make_flight(config['vehicle'], row)
                if config['flight']:
                    track_name = config['flight'].name
                else:
                    # calculate it from the csv file timestamp.
                    track_name = calculate_trackname(config['vehicle'], row)

    track = create_track(track_name, config['vehicle'], config['flight'])
    if track:
        config['defaults'].update({'track_id': track.id})
        return csvImporter.load_csv(config, config['vehicle'], config['flight'], config['csv_file'], config['csv_reader'])
    else:
        raise Exception('Could not create track for some reason')




