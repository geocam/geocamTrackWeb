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
        }
    });

    app.views.TrackView = Marionette.View.extend({
        template: _.noop,
        flat_times: [],
        flat_coords: [],
        playback : {
                lastUpdate: undefined,
                invalid: false,
                initialized: false,
                initialize: function() {
                    if (this.initialized){
                        return;
                    }
                    this.initialized = true;
                },
                doSetTime: function(currentTime){
                    if (currentTime === undefined){
                        return;
                    }
                    this.lastUpdate = moment(currentTime);
                    this.context.updateVehiclePosition(currentTime);
//                    app.vent.trigger('updateVehicleTime', currentTime);
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
            },
        storeNode: function(){
            this.trackNode = app.nodeMap[this.key];
        },
        updateVehiclePosition: function(input_time){
            var foundIndex = this.findClosestTimeIndex(input_time.valueOf());
            if (foundIndex >= 0){
                var new_coords = this.flat_coords[foundIndex];
                var locationDict = {location:transform(new_coords), rotation:null};
                app.vent.trigger('vehicle:change', locationDict);
            }
        },
        findClosestTimeIndex: function(input_time){
            var foundIndex = _.findIndex(this.flat_times, function(value){
				return Math.abs((input_time - value)/1000) < this.intervalSeconds;
			}, this);
            return foundIndex;
        },
        organizeData: function() {
            // this.data[0].times[0][0]
            var context = this;
            _.forEach(this.data, function(track){
                _.forEach(track.times, function(time_array){
                  _.forEach(time_array, function(time_string){
                      context.flat_times.push(Date.parse(time_string));
                  });
                });
                _.forEach(track.coords, function(coords_array){
                  _.forEach(coords_array, function(coords){
                      context.flat_coords.push(coords);
                  });
                })
            }, this);
            if (this.flat_times.length > 1){
                this.intervalSeconds = Math.abs(this.flat_times[1] - this.flat_times[0])/1000.0;
            }
        },
        dataExists: function() {
            // callback for when we know the actual track json data is loaded.
            this.data = this.trackNode.objectsJson;
            this.organizeData();
            this.playback.context = this;
            this.createVehicle();
            playback.addListener(this.playback);
            app.vent.trigger('mapSearch:fit');
        },
        initialize: function(options){
            this.key = options.key;
            this.data = undefined;
            this.listenTo(app.vent, 'app.nodeMap:exists', function(key) { if (key === this.key) {this.storeNode();}});
            this.listenTo(app.vent, 'cacheJSON', function(key) { if (key == this.key) {this.dataExists()}});
            this.track = new app.models.TrackModel(options);
            this.track_metadata = options;
            options.selected = true;  // setting this to true forces render immediately
            app.vent.trigger('mapNode:create', options);  // this will actually render it on the map
        },
        getFirstCoords: function() {
            if (this.flat_coords.length > 0){
                  return transform(this.flat_coords[0]);
            }
            return undefined;
        },
        createVehicle: function() {
            if (this.vehicleView === undefined){
                if (this.flat_coords.length > 0){
                    var vehicleJson = {name:this.track.name,
                                       startPoint:this.getFirstCoords()};
                    this.vehicleView = new app.views.OLVehicleView({featureJson:vehicleJson});
                    app.map.map.addLayer(this.vehicleView.vectorLayer);
                }
            }
        },

    });


});