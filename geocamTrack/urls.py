# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.conf.urls import patterns

from geocamTrack import views

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

)
