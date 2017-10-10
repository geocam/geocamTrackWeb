# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

from django.conf.urls import url

from geocamTrack import views
from django.conf import settings

urlpatterns = [url(r'^$', views.getIndex,
                   {}, 'geocamTrack_index'),

               url(r'^resources.json$', views.getResourcesJson,
                   {}),
               url(r'^icon/(\S+)', views.getIcon,
                   {}),
               url(r'^liveMap/$', views.getLiveMap,
                   {}),
               url(r'^liveMap.kml$', views.getKmlNetworkLink,
                   {}),
               url(r'^latest.kml$', views.getKmlLatest,
                   {}),
               url(r'^post/$', views.postPosition,
                   {'challenge': 'basic'  # for best support of future mobile apps
                }),
               url(r'^tracks.kml$', views.getCurrentPosKml,
                   {},
                   'geocamTrack_tracks'),
               url(r'^recent/tracks.kml$', views.getRecentTracksKml,
                   {},
                   'geocamTrack_recentTracks'),
               url(r'^cached/tracks.kml$', views.getCachedTracksKml,
                   {},
                   'geocamTrack_cachedTracks'),
               url(r'^trackIndex.kml$', views.getTrackIndexKml,
                   {},
                   'geocamTrack_trackIndex'),
               url(r'^csvTrackIndex/$', views.getCsvTrackIndex,
                   {},
                   'geocamTrack_csvTrackIndex'),
               url(r'^track/([^\./]+\.csv)$', views.getTrackCsv,
                   {},
                   'geocamTrack_trackCsv'),
               url(r'^track/csv/(?P<trackName>[\w-]+)$', views.getTrackCsv,
                   {},
                   'geocamTrack_trackCsv_byname'),
               url(r'^track/(?P<trackName>[\w-]+)$', views.getTrackKml,
                   {},
                   'geocamTrack_trackKml'),
               url(r'^animated/track/(?P<trackName>[\w\d\s-]+)$', views.getAnimatedTrackKml,
                   {},
                   'geocamTrack_trackKml_animated'),
               url(r'^mapJsonTrack/(?P<uuid>[\w-]+)$', views.mapJsonTrack, {}, 'geocamTrack_mapJsonTrack'),
               url(r'^mapJsonPosition/(?P<id>[\d]+)$', views.mapJsonPosition, {}, 'geocamTrack_mapJsonPosition'),
               url(r'importTrack/$', views.importTrack, {}, 'geocamTrack_importTrack'),
               url(r'track/pk/json$', views.getActiveTrackPKs, {}, 'geocamTrack_active_track_pk'),
               url(r'position/active/json$', views.getActivePositionsJSON, {}, 'geocamTrack_active_positions_json'),
               ]

if False and settings.XGDS_SSE:
    from sse_wrapper.views import EventStreamView
    urlpatterns += [url(r'^live/test/$', views.getLiveTest, {}, 'geocamTrack_liveTest'),
                    url(r'^live/test/(?P<trackId>[\d-]+)$', views.getLiveTest, {}, 'geocamTrack_liveTest'),
                    url(r'^live/testPositions/$', views.testPositions, {}, 'geocamTrack_testPositions'),
                    url(r'^live/testPositions/(?P<trackId>[\d-]+)$', views.testPositions, {}, 'geocamTrack_testPositions'),
                    url(r'^live/startStreaming/$', views.sendActivePositions, {}, 'geocamTrack_startStreaming'),

                    url(r'^live/positions/(?P<trackId>[\d-]+)$', views.getActivePositionsJson, {}, 'geocamTrack_livePositions'),
                    url(r'^live/positions-stream/(?P<channel_extension>[\w]+)/$', EventStreamView.as_view(channel='live/positions'), {}, 'geocamTrack_livePositions_stream'),

                    url(r'^live/positions/$', views.getActivePositionsJson, {}, 'geocamTrack_livePositions'),
                    url(r'^live/positions-stream/$', EventStreamView.as_view(channel='live/positions'), {}, 'geocamTrack_livePositions_stream'),

                    url(r'^mapJsonTrack/(?P<channel_extension>[\w]+)/$', EventStreamView.as_view(channel='mapJsonTrack'), {}, 'geocamTrack_mapJsonTrack_stream'),
                    url(r'^mapJsonPosition/(?P<channel_extension>[\w]+)/$', EventStreamView.as_view(channel='mapJsonPosition'), {}, 'geocamTrack_mapJsonPosition_stream')
]
