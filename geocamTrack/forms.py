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
from geocamUtil.forms.AbstractImportForm import AbstractImportForm
from geocamUtil.extFileField import ExtFileField
from xgds_core.forms import SearchForm

Resource = LazyGetModelByName(settings.GEOCAM_TRACK_RESOURCE_MODEL)
TRACK_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_TRACK_MODEL)
POSITION_MODEL = LazyGetModelByName(settings.GEOCAM_TRACK_PAST_POSITION_MODEL)

from django.forms.models import ModelChoiceField
from django.forms import CharField


class AbstractImportTrackedForm(AbstractImportForm):
    resource = ModelChoiceField(required=False, queryset=Resource.get().objects.filter(primary=True), label=settings.GEOCAM_TRACK_RESOURCE_VERBOSE_NAME)
    
    def getResource(self):
        if self.cleaned_data['resource']:
            return self.cleaned_data['resource']
        else:
            return None
    
    class meta:
        abstract=True


class ImportTrackForm(AbstractImportTrackedForm):
    sourceFile = ExtFileField(ext_whitelist=(".gpx", ), required=True)


class SearchTrackForm(SearchForm):
    name = CharField(required=False)
    resource = ModelChoiceField(required=False, queryset=Resource.get().objects.filter(primary=True), label=settings.GEOCAM_TRACK_RESOURCE_VERBOSE_NAME)

    class Meta:
        model = TRACK_MODEL.get()
        fields = TRACK_MODEL.get().getSearchFormFields()


class SearchPositionForm(SearchForm):

    class Meta:
        model = POSITION_MODEL.get()
        fields = POSITION_MODEL.get().getSearchFormFields()
