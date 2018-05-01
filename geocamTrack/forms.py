# __BEGIN_LICENSE__
#Copyright (c) 2015, United States Government, as represented by the 
#Administrator of the National Aeronautics and Space Administration. 
#All rights reserved.
#
#The xGDS platform is licensed under the Apache License, Version 2.0 
#(the "License"); you may not use this file except in compliance with the License. 
#You may obtain a copy of the License at 
#http://www.apache.org/licenses/LICENSE-2.0.
#
#Unless required by applicable law or agreed to in writing, software distributed 
#under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR 
#CONDITIONS OF ANY KIND, either express or implied. See the License for the 
#specific language governing permissions and limitations under the License.
# __END_LICENSE__

from django.conf import settings
from geocamUtil.loader import LazyGetModelByName
from geocamUtil.extFileField import ExtFileField
from xgds_core.forms import SearchForm, AbstractImportVehicleForm

TRACK_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_TRACK_MODEL)
POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)
VEHICLE_MODEL = LazyGetModelByName(settings.XGDS_CORE_VEHICLE_MODEL)


from django.forms.models import ModelChoiceField
from django.forms import CharField


class ImportTrackForm(AbstractImportVehicleForm):
    sourceFile = ExtFileField(ext_whitelist=(".gpx", ), required=True)


class SearchTrackForm(SearchForm):
    name = CharField(required=False)
    vehicle = ModelChoiceField(required=False, queryset=VEHICLE_MODEL.get().objects.filter(primary=True), label=settings.XGDS_CORE_VEHICLE_MONIKER)

    class Meta:
        model = TRACK_MODEL.get()
        fields = TRACK_MODEL.get().getSearchFormFields()


class SearchPositionForm(SearchForm):
    track__vehicle = ModelChoiceField(required=False, queryset=VEHICLE_MODEL.get().objects.filter(primary=True),
                                      label=settings.XGDS_CORE_VEHICLE_MONIKER)

    class Meta:
        model = POSITION_MODEL.get()
        fields = POSITION_MODEL.get().getSearchFormFields()
