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
	STALE_TIMEOUT: 5000,
	playing: true,
	initialize: function() {
		trackSse.getCurrentPositions();
		trackSse.subscribe();
		setInterval(function() {trackSse.allChannels(trackSse.checkStale);}, trackSse.STALE_TIMEOUT);
		app.vent.on('live:pause', function() {trackSse.handle_pause()});
		app.vent.on('live:play', function() {trackSse.handle_play()});
	},
	handle_pause: function() {
		this.playing = false;
	},
	handle_play: function() {
		this.playing = true;
	},
	subscribe: function() {
		sse.subscribe('position', trackSse.handlePositionEvent, "handlePositionEvent", trackSse.getChannels());
	},
	getChannels: function() {
		// get the active channels over AJAX
		if (this.activeChannels === undefined){
			$.ajax({
	            url: '/track/sseActiveTracks',
	            dataType: 'json',
	            async: false,
	            success: $.proxy(function(data) {
	                this.activeChannels = data;
	            }, this)
	          });
		}
		return this.activeChannels;
	},
	allChannels: function(theFunction){
		var channels = this.getChannels();
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
			var nowmoment = moment(trackSse.positions[channel].timestamp);
			var lastmoment = undefined;
			if (trackSse.last_times[channel] != undefined) {
				lastmoment = moment(trackSse.last_times[channel])
				trackSse.last_times[channel] = undefined;
			} else {
				lastmoment = moment();
			}
			var diff = moment.duration(nowmoment.diff(lastmoment));
			var diff_seconds = diff.asSeconds();
			if (_.isNaN(diff_seconds)) {
				connected = false;
			} else if (Math.abs(diff_seconds) <= (trackSse.STALE_TIMEOUT / 1000)) {
				connected = true;
			}
		}
		if (!connected){
			trackSse.showDisconnected(channel);
		}
	},
	showDisconnected: function(channel) {
//		console.log(channel + ' DISCONNECTED');
	},
	// subscribe: function(channel) {
	// 	console.log('SUBSCRIBINg position ' + channel)
	// 	sse.subscribe('position', trackSse.handlePositionEvent, channel);
	// },
	handlePositionEvent: function(event){
		var data = JSON.parse(event.data);
		var channel = sse.parseEventChannel(event);
		trackSse.updatePosition(channel, data);
		trackSse.updateTrack(channel, data);
	},
	positions: {},
	last_times: {},
	tracks: {},
	createPosition: function(channel, data, nonSse){
		// in this example we just store the data
		trackSse.positions[channel] = data;
		trackSse.last_times[channel] = data.timestamp;
		trackSse.getTrack(channel, data);
	},
	modifyPosition: function(channel, data, disconnected){
		trackSse.last_times[channel] = trackSse.positions[channel].timestamp;
		trackSse.positions[channel] = data;
	},
	updatePosition: function(channel, data){
		data.displayName = channel;
		if (!(channel in trackSse.positions)){
			trackSse.createPosition(channel, data);
		} else {
			if (this.playing) {
				trackSse.modifyPosition(channel, data, false);
			}
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
	convertTrackNameToChannel: function(track_name){
		var splits = track_name.split('_');
        var last = splits[splits.length - 1];
        return last.toLowerCase();
	},
	getCurrentPositions: function() {
		var trackPKUrl = '/track/position/active/json'
		$.ajax({
            url: trackPKUrl,
            dataType: 'json',
            success: $.proxy(function(data) {
            	if (data != null){
            		// should return dictionary of channel: position
            		for (var track_name in data){
            			var channel = trackSse.convertTrackNameToChannel(track_name);
            			if (!(channel in trackSse.positions)){
            				trackSse.createPosition(channel, data[track_name], true);
            			}
            		}
            	}
            }, this)
          });
	},
	// when we get the position, it then gets the track.  No need for this.
//	getCurrentTracks: function() {
//		var trackPKUrl = '/track/track/pk/json'
//		$.ajax({
//            url: trackPKUrl,
//            dataType: 'json',
//            success: $.proxy(function(data) {
//            	if (data != null){
//            		// should return dictionary of channel: trackpk
//            		for (var track_name in data){
//            			var channel = trackSse.convertTrackNameToChannel(track_name);
//            		    trackSse.getTrack(channel, {'track_pk':data[track_name]});
//            		}
//            	}
//            }, this)
//          });
//	},
	getTrack: function(channel, data) {
		// first check if we already got it
		if (!_.isEmpty(trackSse.tracks[channel])){
			return;
		}
		
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