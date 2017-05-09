# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

from django.conf.urls import url

from geocamTrack import views
from django.conf import settings

urlpatterns = [url(r'^$', views.getIndex,
                   {'readOnly': True}, 'geocamTrack_index'),

               url(r'^resources.json$', views.getResourcesJson,
                   {'readOnly': True}),
               url(r'^icon/(\S+)', views.getIcon,
                   {'readOnly': True}),
               url(r'^liveMap/$', views.getLiveMap,
                   {'readOnly': True}),
               url(r'^liveMap.kml$', views.getKmlNetworkLink,
                   {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']}),
               url(r'^latest.kml$', views.getKmlLatest,
                   {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']}),
               url(r'^post/$', views.postPosition,
                   {'challenge': 'basic'  # for best support of future mobile apps
                }),
               url(r'^tracks.kml$', views.getCurrentPosKml,
                   {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']},
                   'geocamTrack_tracks'),
               url(r'^recent/tracks.kml$', views.getRecentTracksKml,
                   {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']},
                   'geocamTrack_recentTracks'),
               url(r'^cached/tracks.kml$', views.getCachedTracksKml,
                   {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']},
                   'geocamTrack_cachedTracks'),
               url(r'^trackIndex.kml$', views.getTrackIndexKml,
                   {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']},
                   'geocamTrack_trackIndex'),
               url(r'^csvTrackIndex/$', views.getCsvTrackIndex,
                   {'readOnly': True},
                   'geocamTrack_csvTrackIndex'),
               url(r'^track/([^\./]+\.csv)$', views.getTrackCsv,
                   {'readOnly': True},
                   'geocamTrack_trackCsv'),
               url(r'^track/csv/(?P<trackName>[\w-]+)$', views.getTrackCsv,
                   {'readOnly': True},
                   'geocamTrack_trackCsv_byname'),
               url(r'^track/(?P<trackName>[\w-]+)$', views.getTrackKml,
                   {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']},
                   'geocamTrack_trackKml'),
               url(r'^animated/track/(?P<trackName>[\w\d\s-]+)$', views.getAnimatedTrackKml,
                   #     {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']},
                   {'securityTags': ['kml', 'readOnly']},
                   'geocamTrack_trackKml_animated'),
               url(r'^mapJsonTrack/(?P<uuid>[\w-]+)$', views.mapJsonTrack, {'loginRequired': True}, 'geocamTrack_mapJsonTrack'),
               url(r'^mapJsonPosition/(?P<id>[\d]+)$', views.mapJsonPosition, {'loginRequired': True}, 'geocamTrack_mapJsonPosition'),
               url(r'importTrack/$', views.importTrack, {'loginRequired': True}, 'geocamTrack_importTrack'),
               url(r'track/pk/json$', views.getActiveTrackPKs, {}, 'geocamTrack_active_track_pk'),
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

                    url(r'^mapJsonTrack/(?P<channel_extension>[\w]+)/$', EventStreamView.as_view(channel='mapJsonTrack'), {'loginRequired': True}, 'geocamTrack_mapJsonTrack_stream'),
                    url(r'^mapJsonPosition/(?P<channel_extension>[\w]+)/$', EventStreamView.as_view(channel='mapJsonPosition'), {'loginRequired': True}, 'geocamTrack_mapJsonPosition_stream')
]
