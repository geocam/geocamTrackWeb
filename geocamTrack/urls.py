# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

from django.conf.urls import url, include

from geocamTrack import views
from django.conf import settings

urlpatterns = [url(r'^$', views.getIndex,{}, 'geocamTrack_index'),
               #url(r'^resources.json$', views.getResourcesJson,{}),
               #url(r'^icon/(\S+)', views.getIcon,{}),
               #url(r'^liveMap/$', views.getLiveMap,{}),
               #url(r'^liveMap.kml$', views.getKmlNetworkLink,{}),
               #url(r'^latest.kml$', views.getKmlLatest,{}),
               url(r'^post/$', views.postPosition,{'challenge': 'basic' }),
               #url(r'^rest/tracks.kml$', views.getCurrentPosKml,{},'geocamTrack_tracks'),
               #url(r'^recent/tracks.kml$', views.getRecentTracksKml,{},'geocamTrack_recentTracks'),
               #url(r'^cached/tracks.kml$', views.getCachedTracksKml,{},'geocamTrack_cachedTracks'),
               #url(r'^trackIndex.kml$', views.getTrackIndexKml,{},'geocamTrack_trackIndex'),
               url(r'^csvTrackIndex/$', views.getCsvTrackIndex,{},'geocamTrack_csvTrackIndex'),
               url(r'^track/([^\./]+\.csv)$', views.getTrackCsv,{},'geocamTrack_trackCsv'),
               url(r'^track/csv/(?P<trackName>[\w-]+)$', views.getTrackCsv,{},'geocamTrack_trackCsv_byname'),
               #url(r'^track/(?P<trackName>[\w-]+)$', views.getTrackKml,{},'geocamTrack_trackKml'),
               #url(r'^animated/track/(?P<trackName>[\w\d\s-]+)$', views.getAnimatedTrackKml,{},'geocamTrack_trackKml_animated'),
               #url(r'^mapJsonTrack/(?P<uuid>[\w-]+)$', views.mapJsonTrack, {}, 'geocamTrack_mapJsonTrack'),
               #url(r'^mapJsonPosition/(?P<id>[\d]+)$', views.mapJsonPosition, {}, 'geocamTrack_mapJsonPosition'),
               url(r'importTrack/$', views.importTrack, {}, 'geocamTrack_importTrack'),
               #url(r'track/pk/json$', views.getActiveTrackPKs, {}, 'geocamTrack_active_track_pk'),
               #url(r'position/active/json$', views.getActivePositionsJSON, {}, 'geocamTrack_active_positions_json'),
               url(r'^rest/', include('geocamTrack.restUrls')),
               url('', include('geocamTrack.restUrls')),
               ]

