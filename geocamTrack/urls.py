# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

from django.conf.urls import patterns

from geocamTrack import views
import settings

urlpatterns = patterns(
    '',

    (r'^$', views.getIndex,
     {'readOnly': True}, 'geocamTrack_index'),

    (r'^resources.json$', views.getResourcesJson,
     {'readOnly': True}),
    (r'^icon/(\S+)', views.getIcon,
     {'readOnly': True}),
    (r'^liveMap/$', views.getLiveMap,
     {'readOnly': True}),
    (r'^liveMap.kml$', views.getKmlNetworkLink,
     {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']}),
    (r'^latest.kml$', views.getKmlLatest,
     {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']}),
    (r'^post/$', views.postPosition,
     {'challenge': 'basic'  # for best support of future mobile apps
      }),
    (r'^tracks.kml$', views.getCurrentPosKml,
     {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']},
     'geocamTrack_tracks'),
    (r'^recent/tracks.kml$', views.getRecentTracksKml,
     {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']},
     'geocamTrack_recentTracks'),
    (r'^cached/tracks.kml$', views.getCachedTracksKml,
     {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']},
     'geocamTrack_cachedTracks'),
    (r'^trackIndex.kml$', views.getTrackIndexKml,
     {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']},
     'geocamTrack_trackIndex'),
    (r'^csvTrackIndex/$', views.getCsvTrackIndex,
     {'readOnly': True},
     'geocamTrack_csvTrackIndex'),
    (r'^track/([^\./]+\.csv)$', views.getTrackCsv,
     {'readOnly': True},
     'geocamTrack_trackCsv'),
    (r'^track/(?P<trackName>[\w-]+)$', views.getTrackKml,
     {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']},
     'geocamTrack_trackKml'),
    (r'^animated/track/(?P<trackName>[\w\d\s-]+)$', views.getAnimatedTrackKml,
#     {'readOnly': True, 'loginRequired': False, 'securityTags': ['kml', 'readOnly']},
     {'securityTags': ['kml', 'readOnly']},
     'geocamTrack_trackKml_animated'),
    (r'^mapJsonTrack/(?P<uuid>[\w-]+)$', views.mapJsonTrack, {'loginRequired': True}, 'geocamTrack_mapJsonTrack'),
    (r'^mapJsonPosition/(?P<id>[\d]+)$', views.mapJsonPosition, {'loginRequired': True}, 'geocamTrack_mapJsonPosition'),

)

if settings.XGDS_SSE:
    from sse_wrapper.views import EventStreamView
    urlpatterns += patterns('',
                            (r'^live/test/$', views.getLiveTest, {}, 'geocamTrack_liveTest'),
                            (r'^live/test/(?P<trackId>[\d-]+)$', views.getLiveTest, {}, 'geocamTrack_liveTest'),
                            (r'^live/testPositions/$', views.testPositions, {}, 'geocamTrack_testPositions'),
                            (r'^live/testPositions/(?P<trackId>[\d-]+)$', views.testPositions, {}, 'geocamTrack_testPositions'),
                            (r'^live/startStreaming/$', views.sendActivePositions, {}, 'geocamTrack_startStreaming'),

                            (r'^live/positions/(?P<trackId>[\d-]+)$', views.getActivePositionsJson, {}, 'geocamTrack_livePositions'),
                            (r'^live/positions-stream/(?P<channel_extension>[\w]+)/$', EventStreamView.as_view(channel='live/positions'), {}, 'geocamTrack_livePositions_stream'),

                            (r'^live/positions/$', views.getActivePositionsJson, {}, 'geocamTrack_livePositions'),
                            (r'^live/positions-stream/$', EventStreamView.as_view(channel='live/positions'), {}, 'geocamTrack_livePositions_stream'),

                            (r'^mapJsonTrack/(?P<channel_extension>[\w]+)/$', EventStreamView.as_view(channel='mapJsonTrack'), {'loginRequired': True}, 'geocamTrack_mapJsonTrack_stream'),
                            (r'^mapJsonPosition/(?P<channel_extension>[\w]+)/$', EventStreamView.as_view(channel='mapJsonPosition'), {'loginRequired': True}, 'geocamTrack_mapJsonPosition_stream'),

                            )
