L.SssMap = L.mapbox.Map.extend({
    _initControlPos:function () {
        L.mapbox.Map.prototype._initControlPos.call(this);

        var corners = this._controlCorners;
        var l = 'leaflet-';
        var container = this._controlContainer;
 
        function createCorner(vSide, hSide) {
            var className = l + vSide + ' ' + l + hSide;

            corners[vSide + hSide] = L.DomUtil.create('div', className, container);
        }

        createCorner('before', 'left');
        createCorner('before', 'right');
        createCorner('after', 'left');
        createCorner('after', 'right');

    },
});

