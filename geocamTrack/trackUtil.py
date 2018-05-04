# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

from uuid import uuid4

from django.db import connection

from geocamUtil.loader import LazyGetModelByName
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from xgds_core.flightUtils import getNextAlphabet

PAST_POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)
TRACK_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_TRACK_MODEL)
ICON_STYLE_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_ICON_STYLE_MODEL)
LINE_STYLE_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_LINE_STYLE_MODEL)


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


def get_line_style(name):
    """
    Get the line style
    :param name: the name of the line style
    :return: the line style, or default line style
    """
    try:
        line_style = LINE_STYLE_MODEL.get().objects.get(name=name)
    except ObjectDoesNotExist:
        line_style = LINE_STYLE_MODEL.get().objects.get(name='default')
    return line_style


def get_icon_style(name):
    """
    Get the icon style
    :param name: the name of the icon style
    :return: the icon style, or default icon style
    """
    try:
        icon_style = ICON_STYLE_MODEL.get().objects.get(name=name)
    except ObjectDoesNotExist:
        icon_style = ICON_STYLE_MODEL.get().objects.get(name='default')
    return icon_style


def get_next_available_track_name(prefix, vehicle_name):
    """
    Get the next available track name.  Right now the pattern
    :param prefix: the beginning of the track name.
    :return:
    """
    character = 'A'
    tModel = TRACK_MODEL.get()
    while True:
        try:
            name = prefix + character
            if vehicle_name:
                name = name + '_' + vehicle_name
            tModel.objects.get(name)
            character = getNextAlphabet(character)
        except:
            return prefix + character
    return prefix + character  # should never happen


def get_or_create_track(name, vehicle, flight=None, parameters={}, extras=''):
    """
    Find or create a track.  If the track already exists it will not be modified.
    :param name: The name of the track
    :param vehicle: The vehicle
    :param flight: The flight
    :param parameters: (dictionary) Any extra parameters used to construct the model
    :param extras: (string) json data stored with the track
    :return: the track
    """
    tModel = TRACK_MODEL.get()
    try:
        track = tModel.objects.get(name=name)
    except ObjectDoesNotExist:
        params = {'vehicle': vehicle,
                  'flight': flight,
                  'name': name,
                  'extras': extras,
                  'iconStyle': get_icon_style(vehicle.name),
                  'lineStyle': get_line_style(vehicle.name),
                  'uuid': uuid4()}

        params.update(parameters)
        track = tModel(**params)
        track.save()
    return track


