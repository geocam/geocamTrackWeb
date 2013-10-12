# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.conf.urls import patterns, include

from geocamTrack import settings
from geocamTrack import views

urlpatterns = patterns(
    '',

    (r'^$', views.getIndex,
     {'readOnly': True}),

    (r'^resources.json$', views.getResourcesJson,
     {'readOnly': True}),
    (r'^icon/(\S+)', views.getIcon,
     {'readOnly': True}),
    (r'^liveMap/$', views.getLiveMap,
     {'readOnly': True}),
    (r'^liveMap.kml$', views.getKmlNetworkLink,
     {'readOnly': True,
      'challenge': 'basic'  # Google Earth can't handle django challenge
      }),
    (r'^latest.kml$', views.getKmlLatest,
     {'readOnly': True,
      'challenge': 'basic'  # Google Earth can't handle django challenge
      }),

    (r'^post/$', views.postPosition,
     {'challenge': 'basic'  # for best support of future mobile apps
      }),
    (r'^tracks.kml$', views.getCurrentPosKml,
     {'challenge': 'basic',
      'readOnly': True},
     'geocamTrack_tracks'),
    (r'^recent/tracks.kml$', views.getRecentTracksKml,
     {'challenge': 'basic',
      'readOnly': True},
     'geocamTrack_recentTracks'),
    (r'^cached/tracks.kml$', views.getCachedTracksKml,
     {'challenge': 'basic',
      'readOnly': True},
     'geocamTrack_cachedTracks'),
    (r'^trackIndex.kml$', views.getTrackIndexKml,
     {'challenge': 'basic',
      'readOnly': True},
     'geocamTrack_trackIndex'),
    (r'^csvTrackIndex/$', views.getCsvTrackIndex,
     {'readOnly': True},
     'geocamTrack_csvTrackIndex'),
    (r'^track/([^\./]+\.csv)$', views.getTrackCsv,
     {'readOnly': True},
     'geocamTrack_trackCsv'),

)

if settings.GEOCAM_TRACK_LATITUDE_ENABLED:
    # make latitude-related urls available
    urlpatterns += patterns([(r'^latitude/', include('geocamTrack.latitude.urls'))])
