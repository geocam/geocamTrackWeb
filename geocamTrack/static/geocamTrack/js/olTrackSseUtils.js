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
	olPositions: {},
	olTracks: {},
	initialize: function() {
		trackSse.tracksGroup = new ol.layer.Group({name:"liveTracks"});
		app.map.map.getLayers().push(trackSse.tracksGroup);
		trackSse.positionsGroup = new ol.layer.Group({name:"livePositions"});
		app.map.map.getLayers().push(trackSse.positionsGroup);
		trackSse.subscribe();
	},
	createPosition: function(channel, data){
		trackSse.positions[channel] = data;
		trackSse.setupPositionIcon(channel);
		data.displayName = channel;
		var elements = Position.constructElements([data], true);
		trackSse.positionsGroup.getLayers().push(elements);
		trackSse.olPositions[channel] = elements;
		trackSse.getTrack(channel, data);
	},
	modifyPosition: function(channel, data){
		var position = trackSse.olPositions[channel];
		var features = position.getSource().getFeatures();
		var f = features[0];
		var newCoords = transform([data.lon, data.lat]);
		f.getGeometry().setCoordinates(newCoords);
	},
	renderTrack: function(channel, data) {
		var elements = Track.constructElements([data]);
		trackSse.tracksGroup.getLayers().push(elements);
		trackSse.olTracks[channel] = elements;
	},
	updateTrack: function(channel, data) {
		var elements = trackSse.olTracks[channel];
		//TODO add data to the end of the track as a new position or linestring.
		//console.log('update track');
	},
	getCurrentPositions: function() {
		
	}
});