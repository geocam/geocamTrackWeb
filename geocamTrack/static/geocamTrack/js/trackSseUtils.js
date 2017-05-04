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
		trackSse.allChannels(trackSse.subscribe);
		setInterval(function() {trackSse.allChannels(trackSse.checkStale);}, 11000);
	},
	allChannels: function(theFunction){
		var channels = sse.getChannels();
		for (var i=0; i<channels.length; i++){
			var channel = channels[i];
			if (channel != 'sse') {
				theFunction(channel);
			}
		}
	},
	checkStale: function(channel) {
		var connected = false
		if (trackSse.positions[channel] != undefined){
			var nowmoment =  moment();
			var diff = moment.duration(nowmoment.diff(trackSse.positions[channel].timestamp));
			console.log('LAST POSITION: ' + trackSse.positions[channel].timestamp + ' NOW: ' + nowmoment.format() + ' DIFF: ' + diff.asSeconds());
			if (diff.asSeconds() <= 10) {
				connected = true;
			}
		}
		if (!connected){
			trackSse.showDisconnected(channel);
		}
	},
	showDisconnected: function(channel) {
		console.log(channel + ' DISCONNECTED');
	},
	subscribe: function(channel) {
		sse.subscribe('position', trackSse.handlePositionEvent, channel);
	},
	handlePositionEvent: function(event){
		var data = JSON.parse(event.data);
		var channel = sse.parseEventChannel(event);
		trackSse.updatePosition(channel, data);
		trackSse.updateTrack(channel, data);
	},
	positions: {},
	tracks: {},
	createPosition: function(channel, data){
		// in this example we just store the data
		trackSse.positions[channel] = data;
		trackSse.getTrack(channel, data);
	},
	modifyPosition: function(position, data, disconnected){
		trackSse.positions[channel] = data;
	},
	updatePosition: function(channel, data){
		if (!(channel in trackSse.positions)){
			trackSse.createPosition(channel, data);
		} else {
			trackSse.modifyPosition(channel, data, false);
			trackSse.updateTrack(channel, data);
		}
	},
	renderTrack: function(channel, data){
		// right now rendering is done by openlayers in olTrackSseUtils
	},
	updateTrack: function(channel, position) {
		
	},
	getTrackModel: function() {
		return app.options.searchModels['Track'].model;
	},
	getTrack: function(channel, data) {
		
		var trackUrl = '/xgds_map_server/mapJson/' + trackSse.getTrackModel() + '/pk:' + data.track_pk
		$.ajax({
            url: trackUrl,
            dataType: 'json',
            success: $.proxy(function(data) {
            	if (data != null && data.length == 1){
                    trackSse.tracks[channel] = data;
                    trackSse.renderTrack(channel, data[0]);
            	}
            }, this)
          });
		
	}
});