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

trackSse = {}; //namespace

$.extend(trackSse, {
	initialize: function() {
		trackSse.positionsGroup = new ol.layer.Group({name:"livePositions"});
		app.map.map.getLayers().push(trackSse.positionsGroup);
		trackSse.subscribe();
	},
	subscribe: function() {
		// get the channels, for each channel that may have a position subscribe to it.
		var channels = sse.getChannels();
		for (var i=0; i<channels.length; i++){
			var channel = channels[i];
			if (channel != 'sse') {
				sse.subscribe('position', trackSse.handlePositionEvent, channel);
			}
		}
	},
	handlePositionEvent: function(event){
		var data = JSON.parse(event.data);
		var channel = sse.parseEventChannel(event);
		trackSse.updateOLPosition(channel, data);
		trackSse.updateOLTrack(channel, data);
	},
	positions: {},
	createOLPosition: function(channel, data){
		data.displayName = channel;
		var elements = Position.constructElements([data], true);
		trackSse.positionsGroup.getLayers().push(elements);
		trackSse.positions[channel] = elements;
	},
	modifyOLPosition: function(position, data){
		var features = position.getSource().getFeatures();
		var f = features[0];
		var newCoords = transform([data.lon, data.lat]);
		f.getGeometry().setCoordinates(newCoords);
	},
	setupPositionIcon: function(channel){
		Position.initStyles();
		if (!(channel in Position.styles)){
			var pointerPath = '/static/basaltApp/icons/' + channel.toLowerCase() + '_pointer.png';
			console.log(pointerPath);
			Position.styles[channel] = new ol.style.Style({
                image: new ol.style.Icon(/** @type {olx.style.IconOptions} */ ({
                    src: pointerPath,
                    scale: 0.5
                    }))
            });
		}
	},
	updateOLPosition: function(channel, data){
		if (!(channel in trackSse.positions)){
			trackSse.setupPositionIcon(channel);
			trackSse.createOLPosition(channel, data);
		} else {
			var position = trackSse.positions[channel];
			trackSse.modifyOLPosition(position, data);
		}
	},
	updateOLTrack: function(channel, data) {
		
	},
	getCurrentPositions: function() {
		
	}
});