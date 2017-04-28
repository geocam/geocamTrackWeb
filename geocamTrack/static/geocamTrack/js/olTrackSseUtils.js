// __BEGIN_LICENSE__
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
// __END_LICENSE__


$.extend(trackSse, {
	initialize: function() {
		trackSse.positionsGroup = new ol.layer.Group({name:"livePositions"});
		app.map.map.getLayers().push(trackSse.positionsGroup);
		trackSse.subscribe();
	},
	createPosition: function(channel, data){
		trackSse.setupPositionIcon(channel);
		data.displayName = channel;
		var elements = Position.constructElements([data], true);
		trackSse.positionsGroup.getLayers().push(elements);
		trackSse.positions[channel] = elements;
		trackSse.getTrack(data);
	},
	modifyPosition: function(channel, data){
		var position = trackSse.positions[channel];
		var features = position.getSource().getFeatures();
		var f = features[0];
		var newCoords = transform([data.lon, data.lat]);
		f.getGeometry().setCoordinates(newCoords);
	},
	updateTrack: function(channel, data) {
		
	},
	getCurrentPositions: function() {
		
	}
});