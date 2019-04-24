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
        addData: function(data) {
          // add new data to the cache
            var flat_coords = this.get('flat_coords');
            var flat_times = this.get('flat_times');
            flat_times.push(Date.parse(data.timestamp));

            var columns = appOptions.searchModels.Position.coords_array_order;
            var coords = [];
            _.each(columns, function(col) {
                coords.push(data[col]);
            });
            flat_coords.push(coords);
            return coords;
        },
        buildCoords: function(coords) {
            var heading_index = this.get('heading_index');
            var heading = null;
            if (heading_index > -1){
                heading = coords[heading_index];
            }
            var ll = [coords[0], coords[1]];
            return {location:transform(ll), rotation:heading};
        },
        getCoords: function(index) {
            if (this.get('flat_coords').length > 0 && index > -1){
                var coords = this.get('flat_coords')[index];
                return this.buildCoords(coords);
            }
            return undefined;
        },
        getLastCoords: function() {
            return this.getCoords(this.get('flat_coords').length - 1);
        },
        dataExists: function(data) {
            // callback for when we know the actual track json data is loaded.
            this.data = data;
            this.vehicle = data[0].vehicle;
            this.organizeData();
            var coords_array_order = this.data[0].coords_array_order;
            this.set('coords_array_order', coords_array_order);
            var heading_index = coords_array_order.indexOf('heading');
            if (heading_index == -1){
                heading_index = coords_array_order.indexOf('yaw');
            }
            this.set('heading_index', heading_index);
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
                var locationDict = this.getCoords(foundIndex);
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
            //this.data = undefined;
            this.hide_track = false;
            if ('hide_track' in options) {
                this.hide_track = options.hide_track;
            }
            this.vehicle_name = options.data.vehicle.toLowerCase();
            this.track = new app.models.TrackModel(options);
            this.listenTo(app.vent, 'app.nodeMap:exists', function(key) { if (key === this.key) {this.storeNode(key);}});

            this.listenTo(app.vent, 'cacheJSON', function(key) {
                if (key == this.key) {
                    this.setupWithData(key);
                    var context = this;
                    app.vent.on(this.vehicle_name + ':position', function(data) {
                        context.addTrackData(data);
                    });
                }
            });

            if (!this.hide_track) {
                options.selected = true;  // setting this to true forces render immediately
                app.vent.trigger('mapNode:create', options);  // this will actually render it on the map
                this.listenTo(app.vent, 'olNode:rendered', function (key) {
                    if (key == this.key) {
                        app.vent.trigger('mapSearch:fit', this.trackNode.node.mapView.mapElement);
                    }
                });
            }

        },
        updateTrack: function(coordinate) {
          if (!_.isUndefined(this.trackNode) && !_.isUndefined(this.track.data)) {
              var mapped_track = this.trackNode.mapElement;
              var layer = mapped_track.getLayersArray()[0];
              var source = layer.getSource();
              var features = source.getFeatures();
              var feature = features[features.length - 1];
              var line_string = feature.getGeometry();

              //TODO on the back end when we retrieve the json data for a track we are separating based on
              // a maximum distance.  We ought to do the same thing on the front end.
              // see https://github.com/geocam/geocamTrackWeb/blob/55416781f1b1281a8550320ce2cb0a6bbc0ac4b4/geocamTrack/models.py#L572

              if (line_string.getType() !== 'LineString') {
                  // the last one is a point, add a linestring
                  var key = this.track.get('name') + '_line';
                  var style = Track.styles[key];

                  var first_coord = line_string.getCoordinates();
                  var second_coord = transform(coordinate);
                  var new_feature = Track.constructLineString(this.track.get('name') + '_' + features.length, [first_coord, second_coord], style);
                  source.addFeature(new_feature);
                  source.changed();
              } else {
                  line_string.appendCoordinate(transform(coordinate));
              }
          }
        },
        setupWithData: function(key){
            this.track.dataExists(this.trackNode.objectsJson);
            this.vehicle = this.track.vehicle;
            this.createVehicle();
            this.playback = new app.models.PlaybackModel({context:this});
            playback.addListener(this.playback);
        },
        createVehicle: function() {
            if (this.vehicleView === undefined){
                var length = this.track.get('flat_coords').length;
                if (length > 0){
                    var vehicleJson = {name:this.track.name,
                                       vehicle:this.track.vehicle,
                                       startPoint:this.track.getCoords(length - 1)};
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
        addTrackData: function(data){
            var coords = this.track.addData(data);
            if (data.update){
                app.vent.trigger(this.vehicle + ':change', this.track.getLastCoords());
                this.updateTrack(coords);
            }
        }

    });


});