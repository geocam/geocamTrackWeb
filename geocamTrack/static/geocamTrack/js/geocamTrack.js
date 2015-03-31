// __BEGIN_LICENSE__
//Copyright (c) 2015, United States Government, as represented by the
//Administrator of the National Aeronautics and Space Administration.
//All rights reserved.
// __END_LICENSE__
// __BEGIN_APACHE_LICENSE__
//Copyright (c) 2015, United States Government, as represented by the 
//Administrator of the National Aeronautics and Space Administration. 
//All rights reserved.
//
//The xGDS platform is licensed under the Apache License, Version 2.0 
//(the "License"); you may not use this file except in compliance with the License. 
//You may obtain a copy of the License at 
//http://www.apache.org/licenses/LICENSE-2.0.
//
//Unless required by applicable law or agreed to in writing, software distributed 
//under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR 
//CONDITIONS OF ANY KIND, either express or implied. See the License for the 
//specific language governing permissions and limitations under the License.
// __END_APACHE_LICENSE__

var geocamTrack = {
    markersById: {},
    markerCount: 0,

    nullOrUndefined: function(x) {
        return (x === null) || (x === undefined);
    },

    initFeature: function(feature) {
        var pos = new google.maps.LatLng(feature.geometry.coordinates[1],
                                         feature.geometry.coordinates[0]);
        var marker = geocamTrack.markersById[feature.id];
        if (marker === undefined) {
            var icon;
            if (geocamTrack.markerCount < 26) {
                var letter = String.fromCharCode(65 + geocamTrack.markerCount);
                icon = ('http://maps.google.com/mapfiles/marker' +
                        letter + '.png');
            } else {
                icon = 'http://maps.google.com/mapfiles/marker.png';
            }
            var title;
            if (geocamTrack.nullOrUndefined(feature.properties.displayName)) {
                title = feature.properties.userName;
            } else {
                title = feature.properties.displayName;
            }

            marker = new google.maps.Marker({
                position: pos,
                title: title,
                icon: icon
            });
            marker.setMap(geocamCore.mapG.gmap);
            geocamTrack.markersById[feature.id] = marker;
            geocamTrack.markerCount++;
        }
        if (!pos.equals(marker.position)) {
            marker.setPosition(pos);
        }
    },

    handleResourcePositionsResponse: function(response) {
        if (!geocamTrack.nullOrUndefined(response.result)) {
            $.each(response.result.features,
                   function(i, feature) {
                       geocamTrack.initFeature(feature);
                   });
        }
    },

    updateResourcePositions: function() {
        $.getJSON(geocamCore.settings.SCRIPT_NAME +
                  'tracking/resources.json',
                  geocamTrack.handleResourcePositionsResponse);
    },

    updateResourcePositionsLoop: function() {
        geocamTrack.updateResourcePositions();
        setTimeout(geocamTrack.updateResourcePositionsLoop, 5000);
    },

    startTracking: function() {
        geocamTrack.updateResourcePositionsLoop();
    }
};
