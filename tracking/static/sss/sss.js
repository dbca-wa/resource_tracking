"use strict";
var sss = (function (s) {
    //the default opacity for tile layer
    s.default_opacity = 80;

    //the min z index for tile layer
    s.zindex_min = 10001;
    //the max z index for tile layer
    s.zindex_max = 100000000;
    //the initial interval between two adjacent tile layer's z index. 
    //this is used to improve the performance by only modifing the affected layer's z index instead of changing all of the layer's z index
    s.zindex_interval = 4096;

    //get the layer's zindex based on up layer z index and down layer z index
    //In the first, all layer's z index will get the value by adding or minus "s.zindex_interval" from the neighbour's zindex value.
    //if up_layer z index is null, means the layer will be added to the top
    //if down_layer z index is null, means the layer will be added to the bottom
    //if both up_layer z index and down_layer z index are null, means this is the first layer
    //return the z index, if successfully;otherwise,return null, means all layer's z index need to be recalculated again.
    s.getZIndex = function(up_layer_index,down_layer_index) {
        if (up_layer_index != null && down_layer_index != null) {
            var zindex = Math.floor((up_layer_index - down_layer_index) / 2) + down_layer_index
            if (zindex == down_layer_index) {
                //no more space to insert a new layer, recalculated all layer's z index
                return null;
            } else {
                return zindex;
            }
        } else if (up_layer_index == null && down_layer_index == null) {
            //try to get a zindex in the middle value of the avaialbe z index range 
            var maximum_layers = Math.floor((s.zindex_max - s.zindex_min) / s.zindex_interval)
            //assume we can have maximum 1000 active layers. and try to get the first layers z index at the middle place
            return (Math.floor((maximum_layers - 1000) / 2) * s.zindex_interval) + s.zindex_min;
        } else if (up_layer_index == null) {
            var zindex = down_layer_index + s.zindex_interval;
            if (zindex > s.zindex_max) {
                //no more space to add a new layer at the top, recalculated all layers' z index
                return null;
            } else {
                return zindex;
            }
        } else {
            var zindex = up_layer_index - s.zindex_interval;
            if (zindex < s.zindex_min) {
                //no more space to add a new layer at the bottom, recalculated all layers' z index
                return null;
            } else {
                return zindex;
            }
        }
    }

    // Ractive setup
    s.ractive = new Ractive({
        el: '#sidebar', 
        template: '#template'
        });


    s.get = function(url, func) {
        // ajax shim for auth
        $.ajax({
            url: url,
            xhrFields: {
                withCredentials: true
            }
        }).then(func);
    }

    // Cached loader
    //url : the url to fetch the data 
    //extract: a function to extract the data from the data fetched from the url
    //cache: cachable flag, true: cache; false: not cache
    //key: the cache key and ractive Key
    s.load = function(url, key, extract, cache) {
        /* if no extract function, just save raw data
           load cached data if it exists, load actual data later and update cache
           extract should be run on loaded data and return json object */
        if (!extract) { var extract = function(data) { return data }};
        var load = function() {
            $("a[href=#settings] i").addClass("fa-spin");
            s.get(url, function(data) {
                s.ractive.set(key, extract(data));
                localforage.setItem(key, s.ractive.get(key));
                $("a[href=#settings] i").removeClass("fa-spin");
            });
        }
        if (cache) {
            //cachable, try to get the data from cache
            localforage.getItem(key).then(function(value) { 
                if (!value) { 
                    //data is not cached
                    load() 
                } else {
                    //data is cached
                    s.ractive.set(key, value);
                    //data is already cached, why need to call load again.
                    load();
                };
            },function() {
                load();
            })
        } else { 
            //not cachable. load the data directly
            load() 
        };
    };

    s.refreshCount = 0;
    s.layerRefreshCount = 0;
    //refresh is repeated invoked function, the invocation interval is 1 second.
    //refreshCount: control the device refresh; is the total seconds passed after the last device refresh.
    //layerRefreshCount: control the layer refresh; is the 10 times slower than device refresh.
    s.refresh = function() {
        // on refresh load devices
        // Ractive observers cascade remaining actions
        var interval = s.ractive.get("refreshInterval");
        if (s.ractive.get("_devices") && s.refreshCount < interval * 60) {
            s.ractive.set("secondsLeft", (interval * 60) - s.refreshCount);
            s.ractive.set("layerMinutesLeft", (interval * 10) - s.layerRefreshCount);
            s.refreshCount += 1;
        } else {
            s.load("/api/v1/device/?limit=10000&point__isnull=false", "_devices", function(data) {
                return data["objects"]
            });
            s.refreshCount = 0;
            //refresh layers 10 times slower than devices
            if (s.layerRefreshCount < 10) {
                s.layerRefreshCount += 1;
            } else {
                s.map.eachLayer(function(mapLayer) {
                    if (mapLayer._sss_id) {
                        mapLayer.setParams({refreshParam: Math.random()});
                    };
                });
                s.layerRefreshCount = 0;
            };
        };
        setTimeout(s.refresh, 1000);
    }

    // lunr.js indexes
    s.idx_layers = lunr(function() {
        this.field("name");
        this.field("title");
        this.field("abstract");
        this.field("onmap");
        this.ref("id");
    });

    s.idx_devices = lunr(function() {
        this.field("deviceid");
        this.field("name");
        this.field("callsign");
        this.field("symbol");
        this.field("category");
        this.field("make");
        this.field("model");
        this.field("rego");
        this.ref("deviceid");
    });

    // WMS catalog loader
    s.load_wms_catalog = function(catalog) {
        var layers = {}
        //$(catalog).find("Capability Layer Layer").each(function() {
        $(catalog.getElementsByTagNameNS('http://www.opengis.net/cat/csw/2.0.2','Record')).each(function() {
            http://purl.org/dc/elements/1.1/
            var name = $(this.getElementsByTagNameNS('http://purl.org/dc/elements/1.1/',"identifier")[0]).text();
            var id = name.replace(".", "_");  
            var title = $(this.getElementsByTagNameNS('http://purl.org/dc/elements/1.1/',"title")[0]).text();
            var abstract = $(this.getElementsByTagNameNS('http://purl.org/dc/terms/',"abstract")[0]).text();
            var wfs_url = false;
            var wms_url = false;
            var wms_parameters = {};
            var preview_url = false;
            var wms_url_match_type = null;
            function init_url(url) {
                if( url.charAt(url.length - 1) == "?" || url.charAt(url.length - 1) == "&") {
                    return url
                } else if (url.indexOf("?") >= 0) {
                    return url + "&";
                } else {
                    return url + "?"
                }
            }
            $(this.getElementsByTagNameNS('http://purl.org/dc/terms/',"references")).each(function() {
                try {
                    var scheme = null;
                    var params = null;
                    scheme = JSON.parse($(this).attr("scheme").replace(/&quot;/g,'"'))
                    if (scheme["protocol"] == "OGC:WFS") {
                        wfs_url = init_url(scheme["linkage"]);
                        params = {
                            service:"wfs",
                            version:scheme["version"],
                        }
                        if (params["version"] == "2.0.0") {
                            params["typeName"] = name;
                        } else {
                            params["typeName"] = name;
                        }
                        wfs_url = init_url(wfs_url + $.param(params))
                    }
                    else if (scheme["protocol"] == "OGC:WMS") {
                        if (wms_url_match_type == "gwc_match") {
                            return true;
                        }
                        if ("width" in scheme && scheme["width"] == "1024") {
                            //gwc endpoint
                            if ("crs" in scheme && scheme["crs"] == "EPSG:4326") {
                                wms_url_match_type = "gwc_match";
                            } else if(wms_url_match_type == "gwc_tile_match"){
                                return true;
                            } else {
                                //can't use multiple srs at the same time.
                                //wms_url_match_type = "gwc_tile_match"
                                wms_url_match_type = "gwc_endpoint_match"
                            }
                        } else if ("width" in scheme && scheme["width"] != "1024") {
                            //gwc endpoint ,but tile not match
                            if (wms_url_match_type == null) {
                                wms_url_match_type = "gwc_endpoint_match"
                            } else {
                                return true;
                            }
                        } else if (!("width" in scheme)) {
                            //wms endpoint
                            if (wms_url_match_type == null || wms_url_match_type == "gwc_endpoint_match") {
                                wms_url_match_type = "wms_match"
                            } else {
                                return true;
                            }
                        }
                        wms_url = init_url(scheme["linkage"])
                        params = {
                            //service:"wms",
                            //version:scheme["version"],
                        }
                        wms_parameters = {
                            tileSize:1024,
                            transparent:true,
                        }
                        if (wms_url_match_type == "gwc_match" || wms_url_match_type == "gwc_tile_match") {
                            wms_parameters["crs"] = scheme["crs"]
                        }
                        wms_parameters["format"] = ("format" in scheme)?scheme["format"]:"image/png";
                        wms_url = init_url(wms_url + $.param(params));
                        preview_url = $(this).text();
                    } 
                    if (wfs_url && wms_url_match_type == "gwc_match") {
                        return false;
                    }
                }
                catch(err) {
                    alert(err);
                    //ignore
                }
            })
            if (wms_url) {
                var layer = {
                    "name": name,
                    "id": id, 
                    "title": title.replace(/_/g, " "),
                    "abstract": abstract,
                    "wfs_url": wfs_url,
                    "wms_url":wms_url,
                    "wms_parameters":wms_parameters,
                    "preview_url":preview_url,
                    "zindex":null,
                }
                layers[id] = _.extend(s.ractive.get("_layers."+id) || {}, layer);
                //if opacity is not customized, use the default one.
                if  (layers[id].opacity == null) {
                    layers[id].opacity = s.default_opacity;
                }
            }
        });
        return layers
    };

    // Ractive observers
    s.filterDevices = function(search) {
        var devices_full = s.ractive.get('_devices');
        if (search) {
            devices = _.map(s.idx_devices.search(search), function(device) {
                return _.extend(device, _.where(devices_full, {deviceid: device.ref})[0]);
            });
        } else { var devices = devices_full };
        s.ractive.set('devices', _.filter(devices, function(device) {
            if (device.point.search("0.0") == 7) { return false;
            } else { return true };
        }));
    };
    s.ractive.observe('deviceSearch', s.filterDevices);
    s.ractive.observe('history', function(deviceid, previous) {
        if (!deviceid) { return };
        s.toggleHistory(s.markers["device-" + deviceid.toString()]);
    });

    s.ractive.observe('_devices', function(_devices) {
        if (!_devices) { return };
        _.map(_devices, function(device) { s.idx_devices.update(device) });
        s.filterDevices(s.ractive.get('deviceSearch'));
        // update history if displayed
        if (s.ractive.get('history')) {
            var id = s.ractive.get('history');
            s.ractive.set('history', false);
            s.ractive.set('history', id);
        }
    });

    s.filterLayers = function(search) {
        var search = search || '';
        var full_layers = s.ractive.get('_layers');
        if (!full_layers) { return };

        //To get the active layers in correct order, get active layers from activeLayers instead of map,
        /*
        var lyrs = [];
        s.map.eachLayer(function(mapLayer) {
            if (mapLayer._sss_id) {
                lyrs.push(mapLayer._sss_id);
            };
        });
        lyrs.reverse();
        */
        var filterLayerIds = null;

        if (search.length > 0) {
            filterLayerIds = _.map(s.idx_layers.search(search),function(o) {return o.ref;}); 
        } else {
            filterLayerIds = _.keys(full_layers);
        }
        filterLayerIds = _.difference(filterLayerIds,s.activeLayerIds || []);

        var activeLayers = _.map(s.activeLayerIds || [], function(layer) {
            return full_layers[layer];
        });

        var layers = _.map(filterLayerIds, function(layer) {
            return full_layers[layer];
        });

        s.ractive.set('layers', layers);
        s.ractive.set('activeLayers', activeLayers);
    };
    s.ractive.observe('layerSearch', s.filterLayers);

    s.ractive.observe('_layers', function(layers) {
        if (!layers) { 
            return;
        } else if (!s.restoredLayers) {
            // try remember layers between reloads
            s.ractive.set("wms_layercount", _.size(layers));
            var addLayers = function(layers) {
                if (layers && layers.length > 0) {
                    //The layers' order is from top to bottom; so we need to add the layer with reverse order
                    for (var i = layers.length - 1;i >= 0;i --) {
                        s.constructLayer(layers[i], "restore");
                    }
                }
            }
            localforage.getItem("activeLayerIds").then(addLayers);
            s.restoredLayers = true;
        } else {
            // update cache
            localforage.setItem("_layers", layers)
            localforage.setItem("activeLayerIds", s.activeLayerIds);
            if (s.activeLayerIds.length > 0) { 
                s.ractive.set("hasActiveLayers", true) } else { 
                s.ractive.set("hasActiveLayers", false) };
        }
        if (s.activeLayerIds.length == 0) {
            s.baseLayer.addTo(s.map).bringToBack(); // if no custom layers, add osm base back
        } else {
            s.map.removeLayer(s.baseLayer); // idempotent
        }
    });
    s.ractive.observe('activeLayers.*.cql', function(new_cql,old_cql,key_path) {
        var layer = s.ractive.get(key_path.substring(0,key_path.length - 4))
        if (layer == null) return;
        
        var mapLayer = s.map._layers[layer._leaflet_id]
        //At first, mapLayer.wmsParams.cql_filter is "undefined"; 
        //if layer.cql is "", the condition "" != "undefined" will be true, and a useless http request will be send.
        if (new_cql != null)  {
            new_cql = new_cql.trim()
            if (new_cql == "") {
                new_cql = null
            }
        }
        if (mapLayer && new_cql != mapLayer.wmsParams.cql_filter) {
            s.load(layer.wfs_url + $.param({request:"GetFeature",resultType:"hits",cql_filter:new_cql}), "_layers."+layer.id+".hits", function(data) {
                var hits = $(data).find('[numberMatched]').attr("numberMatched");
                if (hits > 0) { mapLayer.setParams({cql_filter: new_cql}) 
                } else if (mapLayer.wmsParams.cql_filter) {
                    delete mapLayer.wmsParams.cql_filter;
                    mapLayer.redraw();
                };
                return hits
            });
        }
    });

    s.ractive.observe('activeLayers.*.opacity', function(new_opacity,old_opacity,key_path) {
        var layer = s.ractive.get(key_path.substring(0,key_path.length - 8))
        if (layer == null) return;
        s.constructLayer(layer.id, "changeOpacity");
        localforage.setItem("_layers", s.ractive.get("_layers"));
        
    });

    s.ractive.observe('activeLayers', function(layer) {
        if (layer == null) return;
        if (s.restoredLayers) {
            //get the active layers with new order
            var activeLayers = s.ractive.get("activeLayers");
            //change the zindex;
            if (activeLayers.length > 0) {
                var down_layer_index = null;
                var up_layer_index = null;
                var recalculate = false;
                var layer_zindex = null;
                for (var i = activeLayers.length - 1;i >= 0; i--) {
                    if (i == 0) {
                        up_layer_index = null;
                    } else {
                        up_layer_index = activeLayers[i - 1].zindex;
                    }
                    if ((activeLayers[i].zindex == null) || (up_layer_index != null && activeLayers[i].z_index > up_layer_index) || (down_layer_index != null && activeLayers[i].zindex < down_layer_index)) {
                        layer_zindex = s.getZIndex(up_layer_index,down_layer_index);
                        if (layer_zindex == null) {
                            recalculate = true;
                            break;
                        } else {
                            activeLayers[i].zindex = layer_zindex;
                            s.constructLayer(activeLayers[i].id, "changeZIndex");
                        }
                    }
                    down_layer_index = activeLayers[i].zindex;
                }
                if (recalculate) {
                    down_layer_index = null;
                    for (var i = activeLayers.length - 1;i >= 0; i--) {
                        activeLayers[i].zindex = s.getZIndex(null,down_layer_index);
                        s.constructLayer(activeLayers[i].id, "changeZIndex");
                        down_layer_index = activeLayers[i].zindex;
                    }
                }
                s.activeLayerIds = _.map(activeLayers,function(l) {return l.id;});
            } else {
                s.activeLayerIds = [];
            }
            
            //cache it
            localforage.setItem("activeLayerIds", s.activeLayerIds);
        }
        
    });

    s.ractive.observe('_layers.*', function(layer) {
        s.idx_layers.update(layer);
        s.filterLayers(s.ractive.get('layerSearch'))
    });


    s.activeLayerIds = [];
    s.constructLayer = function (id, action)  {
        var layer = s.ractive.get("_layers." + id);
        var name = layer.name;
        var params = {layers: name,opacity:layer.opacity / 100}
        if (false && !layer.wfs_url) { // disable opaque backing layers for now
            params.format = "image/jpeg";
            params.transparent = false;
            params.opacity = 1;
        }
        if (action == "restore") {
            layer.zindex = null;
            layer._leaflet_id = null;
        }
        if ("crs" in layer.wms_parameters) {
            var crs = layer.wms_parameters['crs'];
            if (typeof crs == "string") {
                if (crs == "EPSG:3857") {
                    params["crs"] = L.CRS.EPSG3857
                } else if (crs == "EPSG:4326") {
                    params["crs"] = L.CRS.EPSG4326
                } else if (crs == "EPSG:3395") {
                    params["crs"] = L.CRS.EPSG3395
                }
            }
        }
        var mapLayer = s.map._layers[layer._leaflet_id] || L.tileLayer.betterWms(
            layer.wms_url,  _.extend(layer.wms_parameters,params));
        mapLayer._sss_id = id;
        if (action == "remove") {
            s.map.removeLayer(mapLayer);
            layer.zindex = null;
            delete layer._leaflet_id;
            delete layer.onmap;
            s.activeLayerIds = _.without(s.activeLayerIds, id);
        } else if (action == "add" || action == "restore") {
            mapLayer.on("loading load", s.loadCheck).addTo(s.map);
            if (mapLayer.wmsParams.transparent == false) {
                mapLayer.bringToBack();
            }
            layer._leaflet_id = mapLayer._leaflet_id;
            layer.onmap = true;
            //add the layer at the top of the array
            s.activeLayerIds.splice(0,0,id);
        } else if (action == "changeOpacity") {
            var opacity = layer.opacity;
            mapLayer.setOpacity(opacity / 100);
            return
        } else if (action == "changeZIndex") {
            var zindex = layer.zindex;
            mapLayer.setZIndex(zindex);
            return
        };
        s.ractive.set("_layers." + id, layer)
        if (layer.wfs_url) {
            s.load(layer.wfs_url + $.param({request:"DescribeFeatureType"}), "_layers."+id+".columns", function(data) {
                var columns = []
                $(data).find('[type]').each(function(index, val) {
                    columns.push($(val).attr("name"));
                });
                return columns;
            }, true);
            s.load(layer.wfs_url + $.param({request:"GetFeature",resultType:"hits"}), "_layers."+id+".totalHits", function(data) {
                return $(data).find('[numberMatched]').attr("numberMatched");
            }, true);
        };
    };

    s.latlngString = function(latlng) {
        return latlng.lat + " , " + latlng.lng;
    }
    // Entrypoint
    s.launch = function() { 
        L.mapbox.accessToken =  'pk.eyJ1IjoiZHBhd2FzaSIsImEiOiJtVjY5WmlFIn0.whc76euXLk2PkyxOkZ5xlQ'

        //var map = (new L.SssMap('map')).setView([-26, 120], 6);
        var map = L.mapbox.map('map',null,{crs:L.CRS.EPSG4326}).setView([-26, 120], 6);
        //assign the map object to s.map directly, because some callback methods reference s.map and will cause javascript exception. 
        s.map = map;
        map.removeControl(map.zoomControl);
        s.sidebar = L.control.sidebar('sidebar').addTo(map).close();
        map.zoomControl = new L.Control.Zoom({ position: 'topright' }).addTo(map);
        L.control.coordinates({ position: 'bottomright', useDMS: true }).addTo(map);
        L.control.scale({ position: 'bottomright', imperial: false, metric:true,maxWidth:500 }).addTo(map);
        s.hash = L.hash(map);
        s.loading = {}
        s.loadCheck = function(evt) {
            s.loading[evt.target._leaflet_id] = evt.type;
            if (_.without(_.values(s.loading), "load").length === 0) {
                s.ractive.set("loaded", true);
            } else {
                s.ractive.set("loaded", false);
            }
        };
        //initialize "loaded" to true.
        s.ractive.set("loaded", true);

        s.printDPI = 150;
        
        s.baseLayer = L.mapbox.tileLayer('dpawasi.k9a74ich').on("loading load", s.loadCheck);

        // on pageload get catalogs
        s.load(s.csw_url+"?service=CSW&request=GetRecords&version=2.0.2&ElementSetName=full&typeNames=csw:Record&outputFormat=application/xml&resultType=results&maxRecords=1000", "_layers", s.load_wms_catalog, true);
        s.ractive.set("refreshInterval", 1);
        s.refresh()
        $("div#resources").on("click", "li", function() {
            var id = $(this).attr("id").slice(7);
            if (id == s.ractive.get("history")) {
                s.map.removeLayer(s.device_history);
                s.ractive.set("history", false);
            } else {
                s.ractive.set("history", id);
            };
        }).on("click", "a.zoom", function() {
            map.fitBounds(s.device_markers.getBounds());
        });
        $("input#geocomplete").geocomplete().bind("geocode:result", function(event, result){
            if (result.geometry.viewport) {
                var ne = _.values(result.geometry.viewport.getNorthEast())
                var sw = _.values(result.geometry.viewport.getSouthWest())
                s.map.fitBounds([ne,sw]);
            } else {
                s.map.setView([result.geometry.location.lat(), result.geometry.location.lng()], s.map.getMaxZoom());
            }
        });
        $("div#layers,div#catalog").on("click", "button#geolocate", function() {
            navigator.geolocation.getCurrentPosition(function(position) {
                s.map.panTo([position.coords.latitude, position.coords.longitude])
            });
        });
        $("div#layers,div#catalog").on("click", "li button", function() {
            s.constructLayer($(this).attr("data-name"), $(this).attr("data-action"));
        }).on("mouseover", "li", function() {
            var id = $(this).attr("id").slice(6);
            var layer = s.ractive.get("_layers."+id);
            var url = layer.preview_url ;
            s.preview_url = url
            $("div#layer-preview").html('<img style="border:1px solid #999; opacity:1.0;background-color:#ffffff;" width="400" height="400" src="' + url + '" alt="'+layer.name+' preview..." >');
        }).on("mouseout", "ul", function() {
            s.preview_url = '';
            $("div#layer-preview").html('');
        });

        var latlngString = function(latlng) {
            return latlng.lat + " , " + latlng.lng;
        }
        var map_grid = null;
        var grid_number = 8;
        var grid_precision = 0;
        var beforePrint = function() {
            if (s.ractive.get("printing")) { return };
            s.ractive.set("printing", true);
            $("li i.fa-print").addClass("fa-spin");
            var lon_span = s.map.getBounds().getEast() - s.map.getBounds().getWest();
            var lat_span = s.map.getBounds().getNorth() - s.map.getBounds().getSouth();
            var grid_interval = (lon_span > lat_span)?lat_span / grid_number:lon_span / grid_number;
            if (grid_interval > 1) {
                grid_interval = Math.round(grid_interval);
                grid_precision = 0;
            } else if (grid_interval > 0.1) {
                grid_interval = (Math.round(grid_interval * 10) / 10).toFixed(1);
                grid_precision = 1;
            } else if (grid_interval > 0.01) { 
                grid_interval = (Math.round(grid_interval * 100) / 100).toFixed(2);
                grid_precision = 2;
            } else if (grid_interval > 0.001) {
                grid_interval = (Math.round(grid_interval * 1000) / 1000).toFixed(3);
                grid_precision = 3;
            } else if (grid_interval > 0.0004) {
                grid_interval = 0.001;
                grid_precision = 3;
            } else {
                grid_interval = 0;
                grid_precision = 0;
            }
            if (grid_interval > 0) {
                if (map_grid == null){
                    map_grid = L.simpleGraticule({
                        interval:grid_interval,
                        showOriginLabel:true,
                        precision:grid_precision,
                        redraw:'move'
                    });
                    map_grid.addTo(s.map);
                } else {
                    map_grid.options.interval = grid_interval;
                    map_grid.options.precision = grid_precision;
                    map_grid.show();
                }
            } else if(map_grid != null) {
                map_grid.hide();
            }
        };

        var afterPrint = function() {
            $("li i.fa-print").removeClass("fa-spin");
            s.ractive.set("printing", false);
            if (map_grid != null) {
                map_grid.clearLayers();
                map_grid.hide();
            }
        };

        $("i.fa-print").click(function(evt) {
            evt.stopImmediatePropagation();
            beforePrint();
            var actuallyPrint = function() {
                $(s.map._container).print({
                    stylesheet:"/static/sss/sss.print.css",
                    no_print_selector:".leaflet-control-container , .leaflet-popup-pane",
                    extra_fields: {
                        map_zoom_level:s.map.getZoom(),
                        map_bbox:s.map.getBounds().toBBoxString(),
                        map_scale:$(".leaflet-control-scale.leaflet-control"),
                        map_south_west:latlngString(s.map.getBounds().getSouthWest()),
                        map_north_east:latlngString(s.map.getBounds().getNorthEast()),
                        map_north_west:latlngString(s.map.getBounds().getNorthWest()),
                        map_south_east:latlngString(s.map.getBounds().getSouthEast()),
                        map_creator:s.ractive.get('username'),
                        map_create_time:(new Date()).toLocaleString(),
                    },
                    scale_selector:".leaflet-control-scale.leaflet-control",
                    iframe:true,
                    after_print:afterPrint,
                });
            }
            var print = function() {
                if (s.ractive.get("loaded")) {
                    // give browser a tick to render
                    setTimeout(actuallyPrint(), 1000);
                } else {
                    setTimeout(print, 100);
                }
            }
            print();
        });

        // Map dependent ractive observers
        s.ractive.observe('devices', function(devices) {
            if (!devices) { return };
            if (s.device_markers) { map.removeLayer(s.device_markers) };
            s.device_markers = L.featureGroup();
            _.each(devices, function(device) {
                var marker = L.marker(omnivore.wkt.parse(device.point).getLayers()[0].getLatLng(), {
                    icon: L.AwesomeMarkers.icon({
                        icon: device.icon, 
                        iconColor: 'black',
                        markerColor: device.age_colour, 
                        prefix: 'fa'
                    })
                });
                marker.device = device;
                marker.bindPopup('<i class="fa fa-cog fa-spin"></i>');
                s.device_markers.addLayer(marker);
                s.markers = s.markers || {};
                s.markers["device-"+device.id] = marker
            });
            map.addLayer(s.device_markers);
            s.device_markers.on('mouseover', function(e) {
                var deviceli = $("li#device-"+e.layer.device.id)
                e.layer.setPopupContent(deviceli[0].innerHTML).openPopup();
            });
        });

        s.ractive.observe('device_history.*', function(points) {
            if (s.device_history) { map.removeLayer(s.device_history) };
            if (!points) { return };
            var now = new Date();
            var history_line = [];
            var history_times = [];
            _.each(points, function(point) {
                history_line.push(omnivore.wkt.parse(point.point).getLayers()[0].getLatLng());
                history_times.push(point.seen);
            });
            var history_lines = _.zip(history_line.slice(0,-1), history_line.slice(1));
            s.device_history = L.featureGroup();
            var index = 0
            _.each(history_lines, function(points) {
                var seen = history_times[index].split("T")[1]
                var previousSeen = history_times[index+1].split("T")[1]
                var age_ms = now - (new Date(history_times[index]));
                // Fade over last 24 hrs
                var opacity = (24 * 3600 * 1000 - age_ms) / (24 * 3600 * 1000);
                if (opacity < 0) {
                    return true;
                } else {
                    var segment = L.polyline(points, {color: '#3d5358', opacity: opacity.toString().slice(0,4)}).addTo(s.device_history);
                    segment.bindLabel(seen + " to " + previousSeen);
                }
                index += 1;
            });
            var marker = s.markers["device-" + s.ractive.get("history")];
            if (marker) { // avoid marker dissapearing when resources reload
                marker.openPopup();
                map.panTo(marker.getLatLng());
            }
            if (s.device_history.getBounds()._northEast) {
                map.addLayer(s.device_history).fitBounds(s.device_history.getBounds());
            }
        });

        s.toggleHistory = function(marker) {
            marker.setPopupContent($("li#device-"+marker.device.id)[0].innerHTML);
            var now = new Date().getTime()
            now = now - now % (60 * 1000)
            s.load("/api/v1/loggedpoint/?"+$.param({
                "limit": 10000,
                "offset": 0,
                "device": marker.device.id,
                "seen__gte": new Date(new Date(now) - 24 * 3600 * 1000).toISOString()
            }), "device_history."+marker.device.id, function(data) { return data["objects"] }, true);
        };

        //s.map = map;

    };

    // Login setup
    s.csw_url = csw_url;
    s.ractive.set("username",login_user.name);
    s.launch();
return s; }(sss || {}));
