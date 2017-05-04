// render json position information on the openlayers map (as a layer from the tree)

var Position = {
        initStyles: function() {
            if (_.isUndefined(this.styles)){
                this.styles = {};
                this.styles['dot'] = new ol.style.Style({
                    image: new ol.style.Circle({
                        	radius: 5,
                        	fill: new ol.style.Fill({
                        	    color: 'blue'
                        	})
                      })
                });
                this.styles['compass'] = new ol.style.Style({
                    image: new ol.style.Icon(/** @type {olx.style.IconOptions} */ ({
                        src: '/static/geocamTrack/icons/compassRoseSm.png',
                        scale: .15
                        }))
                      });
                this.styles['pointer'] = new ol.style.Style({
                    image: new ol.style.Icon(/** @type {olx.style.IconOptions} */ ({
                        src: '/static/geocamTrack/icons/pointer.png',
                        scale: 0.6
                        }))
                      });
                this.styles['stop'] = new ol.style.Style({
                    image: new ol.style.Icon(/** @type {olx.style.IconOptions} */ ({
                        src: '/static/geocamTrack/icons/stop.png',
                        scale: 0.6
                        }))
                      });
                this.styles['text'] = {
                    font: '12px Calibri,sans-serif',
                    fill: new ol.style.Fill({
                        color: 'black'
                    }),
                    stroke: new ol.style.Stroke({
                        color: 'yellow',
                        width: 2
                    }),
                    offsetY: 0
                };
             };
        },
        constructElements: function(positionsJson, isLive){
            if (_.isEmpty(positionsJson)){
                return null;
            }
            this.initStyles();
            var olFeatures = [];
            if (isLive === undefined){
            	isLive = false;
            }
            for (var i = 0; i < positionsJson.length; i++) {
                olFeatures = olFeatures.concat(this.construct(positionsJson[i], isLive));
            }
            var vectorLayer = new ol.layer.Vector({
                name: "Positions",
                source: new ol.source.Vector({
                    features: olFeatures
                })
            });  
            return vectorLayer;
        },
        construct: function(positionJson, isLive){
            var coords = transform([positionJson.lon, positionJson.lat]);
            var feature = new ol.Feature({
                name: positionJson.displayName,
                uuid: positionJson.id,
                geometry: new ol.geom.Point(coords)
            });
            if (isLive == true){
            	feature.setStyle(this.getLiveStyles(positionJson, false));
            } else {
            	feature.setStyle(this.getStyles(positionJson));
            }
            this.setupPopup(feature, positionJson);
            return feature;
        },
        getStyles: function(positionJson) {
            var styles = [this.styles['dot']];
            return styles;
        },
        getLiveStyles: function(positionJson, disconnected) {
        	var styles = [this.styles['pointer']];
        	if (disconnected) {
        		styles[0] = this.styles['stop'];
        	}
        	if (positionJson.displayName in this.styles){
        		styles[0] = this.styles[positionJson.displayName];
//        		var theText = new ol.style.Text(this.styles['text']);
//	            theText.setText(positionJson.displayName);
//	            var textStyle = new ol.style.Style({
//	                text: theText
//	            });
//	            styles.push(textStyle);
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
        setupPopup: function(feature, positionJson) {
            var trString = "<tr><td>%s</td><td>%s</td></tr>";
            var formattedString = "<table>";
            for (var k = 0; k< 4; k++){
                formattedString = formattedString + trString;
            }
            formattedString = formattedString + "</table>";
            var data = ["Lat:", positionJson.lat,
                        "Lon:", positionJson.lon,
                        "Track:", positionJson.displayName,
                        "Time:", positionJson.timestamp];
            feature['popup'] = vsprintf(formattedString, data);
        }
}