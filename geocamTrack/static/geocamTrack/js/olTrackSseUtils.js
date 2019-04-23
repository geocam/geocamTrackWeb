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
	staticIconPrefix: '/static/geocamTrack/icons/',
	olPositions: {},
	olTracks: {},
	initialize: function() {
		trackSse.getCurrentPositions();
		trackSse.tracksGroup = new ol.layer.Group({name:"liveTracks"});
		trackSse.tracksGroup.setOpacity(0.45);
		app.map.map.getLayers().insertAt(3,trackSse.tracksGroup);
		trackSse.positionsGroup = new ol.layer.Group({name:"livePositions"});
		app.map.map.getLayers().push(trackSse.positionsGroup);
		trackSse.subscribe()
		setInterval(function() {trackSse.allChannels(trackSse.checkStale);}, trackSse.STALE_TIMEOUT);
		app.vent.on('live:pause', function() {trackSse.handle_pause()});
		app.vent.on('live:play', function() {trackSse.handle_play()});
	},
	lookupImage: function(url){
		var result = undefined;
		$.each(trackSse.preloadedIcons, function(index, theImg){
			if (theImg.src == url){
				result = theImg;
			}
		});
		return result;
		
	},
	buildStyle: function(channel, name){
		var pointerPath = trackSse.staticIconPrefix + channel.toLowerCase() + '_' + name + '.png';
		var theImg = trackSse.lookupImage(pointerPath);
		// these were preloaded in MapView.html
		var theIcon = new ol.style.Icon(/** @type {olx.style.IconOptions} */ ({
            src: pointerPath,
            img: theImg,  // this is for preload to fix Chrome.
            scale: 0.5
            }));

		var theStyle = new ol.style.Style({
            image: theIcon
        });
		theStyle['name'] = name;
		return theStyle;
	},
	setupPositionIcon: function(channel){
		Position.initStyles();
		if (!(channel in Position.styles)){
			var channelStyleDict = {'pointer': trackSse.buildStyle(channel, 'pointer'),
									'circle': trackSse.buildStyle(channel, 'circle'),
									'stop': trackSse.buildStyle(channel, 'stop')};
			Position.styles[channel] = channelStyleDict;
		}
	},
	createPosition: function(channel, data, nonSse){
		if (nonSse == undefined){
			nonSse = false;
		}
		trackSse.positions[channel] = data;
		trackSse.last_times[channel] = data.timestamp;
		trackSse.setupPositionIcon(channel);
		data.displayName = channel;
		var elements = Position.constructElements([data], true);
		trackSse.positionsGroup.getLayers().push(elements);
		trackSse.olPositions[channel] = elements;
		trackSse.getTrack(channel, data);
		if (nonSse) {
			trackSse.showDisconnected(channel);
		}
	},
	modifyPosition: function(channel, data, disconnected){

		var position = trackSse.olPositions[channel];
		if (position != undefined) {
			if (data != undefined){
					trackSse.last_times[channel] = trackSse.positions[channel].timestamp;
					trackSse.positions[channel] = data;
			}
			var features = position.getSource().getFeatures();
			var f = features[0];
			if (disconnected) {
				data = trackSse.positions[channel];
				f.setStyle(Position.getLiveStyles(data, true));
			} else {
				f.setStyle(Position.getLiveStyles(data, false));
			}
			var newCoords = transform([data.lon, data.lat]);
			f.getGeometry().setCoordinates(newCoords);
		}
	},
	showDisconnected: function(channel) {
		trackSse.modifyPosition(channel, null, true);
	},
	renderTrack: function(channel, data) {
		var elements = Track.constructElements([data]);
		trackSse.tracksGroup.getLayers().push(elements);
		trackSse.olTracks[channel] = elements;
	},
	updateTrack: function(channel, data) {
		var elements = trackSse.olTracks[channel];
		if (elements == undefined){
			return;
		}
		var newCoords = transform([data.lon, data.lat]);
		var features = elements.getSource().getFeatures();
		// TODO check the time of the last update; if the current one is close in time then we continue
		if (features.length > 0){
			var lastFeature = features[features.length - 1];
			var geom = lastFeature.getGeometry();
			if (geom.getType() == 'LineString'){
				// append
				var coords = geom.getCoordinates();
				coords.push(newCoords);
				if (trackSse.playing) {
					geom.setCoordinates(coords);
				}
			} else {
				// remove the last point and create a linestring
			}
		} else {
			// maybe best to get the track from scratch ...
		}
			
		//TODO add data to the end of the track as a new position or linestring.
	}
});

$.extend(Position, {
	getLiveStyles: function(positionJson, disconnected) {
		if (positionJson == null){
			return;
		}
		if (disconnected === undefined) {
			disconnected = false;
		}
    	var styles = [this.styles['pointer']];
		if (positionJson.displayName in this.styles){
			var channel = this.styles[positionJson.displayName];
			if (disconnected){
				styles[0] = channel.stop;
			} else {
				if (_.isNumber(positionJson.heading)){
					var heading = positionJson.heading;
					if (HEADING_UNITS === 'degrees') {
						heading = positionJson.heading * (Math.PI / 180);
					}
	    			styles[0] = channel.pointer;
					styles[0].getImage().setRotation(heading);
	    		} else {
	    			styles[0] = channel.circle;
	    		}
			}
		} else {
			var theText = new ol.style.Text(this.styles['text']);
            theText.setText(positionJson.displayName);
            var textStyle = new ol.style.Style({
                text: theText
            });
            styles.push(textStyle);
		}
		return styles;
    },
});
