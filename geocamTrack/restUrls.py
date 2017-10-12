# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

from django.conf.urls import url

from geocamTrack import views
from django.conf import settings

urlpatterns = [url(r'^resources.json$', views.getResourcesJson,{}),
               url(r'^icon/(\S+)', views.getIcon,{}),
               url(r'^liveMap.kml$', views.getKmlNetworkLink,{}),
               url(r'^latest.kml$', views.getKmlLatest,{}),
               url(r'^tracks.kml$', views.getCurrentPosKml,{},'geocamTrack_tracks'),
               url(r'^recent/tracks.kml$', views.getRecentTracksKml,{},'geocamTrack_recentTracks'),
               url(r'^cached/tracks.kml$', views.getCachedTracksKml,{},'geocamTrack_cachedTracks'),
               url(r'^trackIndex.kml$', views.getTrackIndexKml,{},'geocamTrack_trackIndex'),
               url(r'^track/(?P<trackName>[\w-]+)$', views.getTrackKml,{},'geocamTrack_trackKml'),
               url(r'^animated/track/(?P<trackName>[\w\d\s-]+)$', views.getAnimatedTrackKml,{},'geocamTrack_trackKml_animated'),
               url(r'^mapJsonTrack/(?P<uuid>[\w-]+)$', views.mapJsonTrack, {}, 'geocamTrack_mapJsonTrack'),
               url(r'^mapJsonPosition/(?P<id>[\d]+)$', views.mapJsonPosition, {}, 'geocamTrack_mapJsonPosition'),
               url(r'track/pk/json$', views.getActiveTrackPKs, {}, 'geocamTrack_active_track_pk'),
               url(r'position/active/json$', views.getActivePositionsJSON, {}, 'geocamTrack_active_positions_json'),
               ]
