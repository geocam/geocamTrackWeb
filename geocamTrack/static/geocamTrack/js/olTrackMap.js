// render json track information on the openlayers map (as a layer from the tree)

var AbstractTrack = {
        initStyles: function() {
            if (_.isUndefined(this.styles)){
                this.styles = {};
                this.styles['lineStyle'] = new ol.style.Style({
                    stroke: new ol.style.Stroke({
                        color: '#67fb09',
                        width: 2
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
            if (!_.isUndefined(trackJson.color)){
                color = "#" + trackJson.color;
                lsstyle = new ol.style.Style({
                    stroke: new ol.style.Stroke({
                        color: color,
                        alpha: trackJson.alpha,
                        width: 2
                      })
                    });
            }
            
            for (c = 0; c < coords.length; c++){
                var lineFeature = new ol.Feature({
                    name: trackJson.uuid + "_" + c,
                    geometry: new ol.geom.LineString(coords[c]).transform(LONG_LAT, DEFAULT_COORD_SYSTEM)
                });
                lineFeature.setStyle(lsstyle);
                this.setupLinePopup(lineFeature, trackJson);
                allFeatures.push(lineFeature);
            }
            return allFeatures;
        },
        setupLinePopup: function(feature, trackJson) {
//            var trString = "<tr><td>%s</td><td>%s</td></tr>";
//            var formattedString = "<table>";
//            for (var k = 0; k< 1; k++){
//                formattedString = formattedString + trString;
//            }
//            formattedString = formattedString + "</table>";
//            var data = ["Track:", trackJson.name];
//            feature['popup'] = vsprintf(formattedString, data);
            feature['popup'] = trackJson.name;
        }
}