// render json track information on the openlayers map (as a layer from the tree)

var Track = {
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
                        	radius: 3,
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
        constructLineString: function(name, coords, style) {
            var lineFeature = new ol.Feature({
                            name: name,
                            geometry: new ol.geom.LineString(coords).transform(LONG_LAT, DEFAULT_COORD_SYSTEM)
                        });
            lineFeature.setStyle(style);
            return lineFeature;
        },
        constructPoint: function(name, coords, style) {
            var pointFeature = new ol.Feature({
                name: name,
                geometry: new ol.geom.Point(coords).transform(LONG_LAT, DEFAULT_COORD_SYSTEM)
            });
            pointFeature.setStyle(style);
            return pointFeature;
        },
        constructPointStyle: function(name, color, alpha){
            //TODO deal with alpha
            var key = name + '_point';
            if (!(key in this.styles)) {
                var pointStyle = new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: 3,
                        fill: new ol.style.Fill({
                            color: color
                        })
                    })
                });
                this.styles[key] = pointStyle;
            }
            return this.styles[key];
        },
        constructLineStyle: function(name, color, alpha) {
            var key = name + '_line';
            if (!(key in this.styles)) {
                var lineStyle = new ol.style.Style({
                    stroke: new ol.style.Stroke({
                        color: color,
                        alpha: alpha,
                        width: 2
                    })
                });
                this.styles[key] = lineStyle;
            }
            return this.styles[key];
        },
        construct: function(trackJson){
            var allFeatures = [];
            var coords = trackJson.coords;
            var coord;
            var lsstyle = this.styles['lineStyle'];
            var dotstyle = this.styles['dot'];
            if (!_.isUndefined(trackJson.color)){
                color = "#" + trackJson.color;
                lsstyle = this.constructLineStyle(trackJson.name, color, trackJson.alpha);
                dotstyle = this.constructPointStyle(trackJson.name, color, trackJson.alpha);
            }
            
            for (var c = 0; c < coords.length; c++){
                if (coords[c].length > 1){
                        var lineFeature = this.constructLineString(trackJson.id + "_" + c, coords[c], lsstyle)
                        this.setupLinePopup(lineFeature, trackJson);
                        allFeatures.push(lineFeature);
                } else if (coords[c].length == 1) {
                        var pointFeature = this.constructPoint(trackJson.id + "_" + c, coords[c][0], dotstyle);
                        this.setupLinePopup(pointFeature, trackJson);
                        allFeatures.push(pointFeature);
                }
            }
            return allFeatures;
        },
        setupLinePopup: function(feature, trackJson) {
            feature['popup'] = trackJson.name;
        }
}