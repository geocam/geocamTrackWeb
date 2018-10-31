//__BEGIN_LICENSE__
//Copyright (c) 2015, United States Government, as represented by the
//Administrator of the National Aeronautics and Space Administration.
//All rights reserved.

//The xGDS platform is licensed under the Apache License, Version 2.0
//(the "License"); you may not use this file except in compliance with the License.
//You may obtain a copy of the License at
//http://www.apache.org/licenses/LICENSE-2.0.

//Unless required by applicable law or agreed to in writing, software distributed
//under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
//CONDITIONS OF ANY KIND, either express or implied. See the License for the
//specific language governing permissions and limitations under the License.
//__END_LICENSE__


$(function() {
    app.views = app.views || {};
    app.models = app.models || {};

    app.models.TrackModel = Backbone.Model.extend({
        initialize: function(data){
            // This takes the data from the treejson node
            this.set('name', data.title);
            this.set('url', data.data.json);
            this.set('uuid', data.key);
            this.set('flat_coords', []);
            this.set('flat_times', []);
            this.set('interval_seconds', 1);
        },
        organizeData: function() {
            var context = this;
            var flat_coords = this.get('flat_coords');
            var flat_times = this.get('flat_times');
            _.forEach(this.data, function(track){
                _.forEach(track.times, function(time_array){
                  _.forEach(time_array, function(time_string){
                      flat_times.push(Date.parse(time_string));
                  });
                });
                _.forEach(track.coords, function(coords_array){
                  _.forEach(coords_array, function(coords){
                      flat_coords.push(coords);
                  });
                })
            }, this);
            if (flat_times.length > 1){
                this.set('interval_seconds', Math.abs(flat_times[1] - flat_times[0])/1000.0);
            }
        },
        getFirstCoords: function() {
            if (this.get('flat_coords').length > 0){
                  return transform(this.get('flat_coords')[this.get('flat_coords').length - 1]);
            }
            return undefined;
        },
        dataExists: function(data) {
            // callback for when we know the actual track json data is loaded.
            this.data = data;
            this.vehicle = data[0].vehicle;
            this.organizeData();
        },
        findClosestTimeIndex: function(input_time){
            var foundIndex = _.findIndex(this.get('flat_times'), function(value){
				return Math.abs((input_time - value)/1000) < this.get('interval_seconds');
			}, this);
            return foundIndex;
        },
        updateVehiclePosition: function(input_time){
            var foundIndex = this.findClosestTimeIndex(input_time.valueOf());
            if (foundIndex >= 0){
                var new_coords = this.get('flat_coords')[foundIndex];
                var locationDict = {location:transform(new_coords), rotation:null};
                var key = this.vehicle + ':change';
                app.vent.trigger(key, locationDict)
            }
        },
    });

    app.models.PlaybackModel = Backbone.Model.extend({
        invalid: false,
        lastUpdate: undefined,

        initialized: false,
        initialize: function(arguments, options) {
            if (this.initialized){
                return;
            }
            if (!_.isUndefined(arguments) && 'context' in arguments) {
                this.context = arguments.context;
            }
            this.initialized = true;
        },
        doSetTime: function(currentTime){
            if (currentTime === undefined){
                return;
            }
            this.lastUpdate = moment(currentTime);
            this.context.track.updateVehiclePosition(currentTime);
        },
        start: function(currentTime){
            this.doSetTime(currentTime);
        },
        update: function(currentTime){
            if (this.lastUpdate === undefined){
                this.doSetTime(currentTime);
                return;
            }
            var delta = currentTime.diff(this.lastUpdate);
            if (Math.abs(delta) >= 100) {
                this.doSetTime(currentTime);
            }
        },
        pause: function() {
            // noop
        }
    });

    app.views.TrackView = Marionette.View.extend({
        template: _.noop,
        vehicle: undefined,
        storeNode: function(key){
            this.trackNode = app.nodeMap[key];
        },

        initialize: function(options){
            this.key = options.key;
            this.data = undefined;
            this.track = new app.models.TrackModel(options);
            this.listenTo(app.vent, 'app.nodeMap:exists', function(key) { if (key === this.key) {this.storeNode(key);}});
            this.listenTo(app.vent, 'cacheJSON', function(key) {
                if (key == this.key) {
                    this.setupWithData(key);
                }
            });
            options.selected = true;  // setting this to true forces render immediately
            app.vent.trigger('mapNode:create', options);  // this will actually render it on the map
        },
        setupWithData: function(key){
            this.track.dataExists(this.trackNode.objectsJson);
            this.vehicle = this.track.vehicle;
            this.createVehicle();
            this.playback = new app.models.PlaybackModel({context:this});
            playback.addListener(this.playback);
            app.vent.trigger('mapSearch:fit');
        },
        createVehicle: function() {
            if (this.vehicleView === undefined){
                if (this.track.get('flat_coords').length > 0){
                    var vehicleJson = {name:this.track.name,
                                       vehicle:this.track.vehicle,
                                       startPoint:this.track.getFirstCoords()};
                    if ('icon_url' in this.track.data[0]) {
                        vehicleJson['icon_url'] = this.track.data[0].icon_url;
                        vehicleJson['icon_color'] = this.track.data[0].icon_color;
                        vehicleJson['icon_scale'] = this.track.data[0].icon_scale;
                    }
                    this.vehicleView = new app.views.OLVehicleView({featureJson:vehicleJson});
                    app.map.map.addLayer(this.vehicleView.vectorLayer);
                }
            }
        },

    });


});