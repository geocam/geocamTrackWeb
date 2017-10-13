# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

from django.conf.urls import url, include

from geocamTrack import views
from django.conf import settings

urlpatterns = [url(r'^$', views.getIndex,{}, 'geocamTrack_index'),
               url(r'^post/$', views.postPosition,{'challenge': 'basic' }),
               url(r'^csvTrackIndex/$', views.getCsvTrackIndex,{},'geocamTrack_csvTrackIndex'),
               url(r'^track/csv/(?P<trackName>[\w-]+)$', views.getTrackCsv,{},'geocamTrack_trackCsv_byname'),
               url(r'importTrack/$', views.importTrack, {}, 'geocamTrack_importTrack'),
               
               # Including these in this order ensures that reverse will return the non-rest urls for use in our server
               url(r'^rest/', include('geocamTrack.restUrls')),
               url('', include('geocamTrack.restUrls')),
               ]

