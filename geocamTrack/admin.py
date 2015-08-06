# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
# __END_LICENSE__

from django.contrib import admin

# pylint: disable=W0401

from geocamTrack.models import *
from django.conf import settings

admin.site.register(Resource)
admin.site.register(IconStyle)
admin.site.register(LineStyle)
admin.site.register(Track)
admin.site.register(ResourcePosition)
admin.site.register(PastResourcePosition)
