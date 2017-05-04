// render json track information on the openlayers map (as a layer from the tree)

var Actual_Traverse = {
        initStyles: function() {
            if (_.isUndefined(this.styles)){
                this.styles = {};
                this.styles['lineStyle'] = new ol.style.Style({
                    stroke: new ol.style.Stroke({
                        color: '#67fb09',
                        width: 2
                      })
                    });
                this.styles['dot'] = new ol.style.Style({
                    image: new ol.style.Circle({
                        	radius: 5,
                        	fill: new ol.style.Fill({
                        	    color: '67fb09'
                        	})
                      })
                });
             };
        },
        constructElements: function(tracksJson){
            if (_.isEmpty(tracksJson)){
                return null;
            }
            this.initStyles();
            var olFeatures = [];
            for (var i = 0; i < tracksJson.length; i++) {
                olFeatures = olFeatures.concat(this.construct(tracksJson[i]));
            }
            var vectorLayer = new ol.layer.Vector({
                name: "Tracks",
                source: new ol.source.Vector({
                    features: olFeatures
                })
            });  
            return vectorLayer;
        },
        construct: function(trackJson){
            var allFeatures = [];
            var coords = trackJson.coords;
            var coord;
            var lsstyle = this.styles['lineStyle'];
            var dotstyle = this.styles['dot'];
            if (!_.isUndefined(trackJson.color)){
                color = "#" + trackJson.color;
                lsstyle = new ol.style.Style({
                    stroke: new ol.style.Stroke({
                        color: color,
                        alpha: trackJson.alpha,
                        width: 2
                      })
                    });
                dotstyle = new ol.style.Style({
                    image: new ol.style.Circle({
                	radius: 5,
                	fill: new ol.style.Fill({
                	    color: color
                	})
                    })
              });
            }

            if (coords != undefined) {
	            for (var c = 0; c < coords.length; c++){
		        	if (coords[c].length > 1){
		                    var lineFeature = new ol.Feature({
		                        name: trackJson.id + "_" + c,
		                        geometry: new ol.geom.LineString(coords[c]).transform(LONG_LAT, DEFAULT_COORD_SYSTEM)
		                    });
		                    lineFeature.setStyle(lsstyle);
		                    this.setupLinePopup(lineFeature, trackJson);
		                    allFeatures.push(lineFeature);
		        	} else if (coords[c].length == 1) {
		                    var feature = new ol.Feature({
		                        name: trackJson.id + "_" + c,
		                    	geometry: new ol.geom.Point(coords[c][0]).transform(LONG_LAT, DEFAULT_COORD_SYSTEM)
		                    });
		                    feature.setStyle(dotstyle);
		                    this.setupLinePopup(feature, trackJson);
		                    allFeatures.push(feature);
		        	}
	            }
            }
            return allFeatures;
        },
        setupLinePopup: function(feature, trackJson) {
            feature['popup'] = trackJson.name;
        }
}