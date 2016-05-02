"use strict"
L.toJson = function(map) {
    var data = {};
    data.center = [map.getCenter().lat,map.getCenter().lng];
    var bounds = map.getBounds();
    data.bounds = [bounds.getSouthWest().lat,bounds.getSouthWest().lng,bounds.getNorthEast().lat,bounds.getNorthEast().lng];
    data.zoom = map.getZoom();
    data.wms_layers = [];
    data.markers = [];
    data.polylines = [];
    map.eachLayer(function (layer){
        var settings = {}
        if (layer instanceof L.Marker) {
            settings.point = [layer.getLatLng().lat,layer.getLatLng().lng];
            settings.options = {
                opacity:layer.options.opacity,
                icon:layer.options.icon.options,
            };
            data.markers.push(settings);
        } else if( layer instanceof L.TileLayer.WMS) {
            settings.url = layer._url;
            settings.options = {
                opacity:layer.options.opacity,
                tileSize:layer.options.tileSize,
                crs: layer.options.crs.code,
                zIndex:layer.options.zIndex,
            };
            settings.wmsParams = layer.wmsParams;
            data.wms_layers.push(settings);
        } else if( layer instanceof L.Polyline) {
            settings.points = []
            _.each(layer.getLatLngs(), function(point) {
                settings.points.push([point.lat,point.lng]);
            })
            settings.options = layer.options;
            if (layer.label != null) {
                settings.label = {};
                settings.label.label = layer.label._content;
                settings.label.options = layer.label.options;
            }
            data.polylines.push(settings);
        }
    });

    return data;
}
