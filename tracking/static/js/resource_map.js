"use strict";
const geoserver_wmts_url = geoserver_url + "/gwc/service/wmts?service=WMTS&request=GetTile&version=1.0.0&tilematrixset=gda94&tilematrix=gda94:{z}&tilecol={x}&tilerow={y}";
const geoserver_wmts_url_base = geoserver_wmts_url + "&format=image/jpeg";
const geoserver_wmts_url_overlay = geoserver_wmts_url + "&format=image/png";

// Base layers
const mapboxStreets = L.tileLayer(
  geoserver_wmts_url_base + "&layer=dbca:mapbox-streets",
  {
    tileSize: 1024,
    zoomOffset: -2,
  },
);
const landgateOrthomosaic = L.tileLayer(
  geoserver_wmts_url_base + "&layer=landgate:virtual_mosaic",
  {
    tileSize: 1024,
    zoomOffset: -2,
  },
);
const stateMapBase = L.tileLayer(
  geoserver_wmts_url_base + "&layer=cddp:state_map_base",
  {
    tileSize: 1024,
    zoomOffset: -2,
  },
);

// Overlay layers
const dbcaBushfires = L.tileLayer(
  geoserver_wmts_url_overlay + "&layer=landgate:dbca_going_bushfires_dbca-001",
  {
    tileSize: 1024,
    zoomOffset: -2,
    transparent: true,
    opacity: 0.75,
  }
);
const dfesBushfires = L.tileLayer(
  geoserver_wmts_url_overlay + "&layer=landgate:authorised_fireshape_dfes-032",
  {
    tileSize: 1024,
    zoomOffset: -2,
    transparent: true,
    opacity: 0.75,
  }
);
const dbcaRegions = L.tileLayer(
  geoserver_wmts_url_overlay + "&layer=cddp:kaartdijin-boodja-public_CPT_DBCA_REGIONS",
  {
    tileSize: 1024,
    zoomOffset: -2,
  },
);
const lgaBoundaries = L.tileLayer(
  geoserver_wmts_url_overlay + "&layer=cddp:local_gov_authority",
  {
    tileSize: 1024,
    zoomOffset: -2,
  },
);

// Icon classes (note that URLs are injected into the base template.)
const iconCar = L.icon({
  iconUrl: car_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconUte = L.icon({
  iconUrl: ute_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconLightUnit = L.icon({
  iconUrl: light_unit_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconGangTruck = L.icon({
  iconUrl: gang_truck_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconCommsBus = L.icon({
  iconUrl: comms_bus_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconRotary = L.icon({
  iconUrl: rotary_aircraft_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconPlane = L.icon({
  iconUrl: plane_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconDozer = L.icon({
  iconUrl: dozer_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconLoader = L.icon({
  iconUrl: loader_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconFloat = L.icon({
  iconUrl: float_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconFuelTruck = L.icon({
  iconUrl: fuel_truck_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconPerson = L.icon({
  iconUrl: person_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconOther = L.icon({
  iconUrl: other_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});


function setDeviceStyle(feature, layer) {
  var callsign;
  if (feature.properties.callsign) {
    callsign = feature.properties.callsign;
  } else {
    callsign = '';
  }
  layer.bindTooltip(
    `
    ID: ${feature.properties.id}<br>
    Registration: ${feature.properties.registration}<br>
    Callsign: ${callsign}<br>
    Type: ${feature.properties.symbol}<br>
    Seen: ${feature.properties.age_text}
    `
  );
  // Set the feature icon.
  if (feature.properties.icon == 'sss-2_wheel_drive') {
    layer.setIcon(iconCar);
  } else if (feature.properties.icon == 'sss-4_wheel_drive_passenger') {
    layer.setIcon(iconCar);
  } else if (feature.properties.icon == 'sss-4_wheel_drive_ute') {
    layer.setIcon(iconUte);
  } else if (feature.properties.icon == 'sss-light_unit') {
    layer.setIcon(iconLightUnit);
  } else if (feature.properties.icon == 'sss-gang_truck') {
    layer.setIcon(iconGangTruck);
  } else if (feature.properties.icon == 'sss-comms_bus') {
    layer.setIcon(iconCommsBus);
  } else if (feature.properties.icon == 'sss-rotary_aircraft') {
    layer.setIcon(iconRotary);
  } else if (feature.properties.icon == 'sss-spotter_aircraft') {
    layer.setIcon(iconPlane);
  } else if (feature.properties.icon == 'sss-dozer') {
    layer.setIcon(iconDozer);
  } else if (feature.properties.icon == 'sss-float') {
    layer.setIcon(iconFloat);
  } else if (feature.properties.icon == 'sss-loader') {
    layer.setIcon(iconLoader);
  } else if (feature.properties.icon == 'sss-aviation_fuel_truck') {
    layer.setIcon(iconFuelTruck);
  } else if (feature.properties.icon == 'sss-person') {
    layer.setIcon(iconPerson);
  } else {
    layer.setIcon(iconOther);
  }
}

// Add the (initially) empty devices layer to the map.
const trackedDevices = L.geoJSON(null, {
  onEachFeature: setDeviceStyle
});

function refreshTrackedDevicesLayer(trackedDevicesLayer) {
  // Remove any existing data from the GeoJSON layer.
  trackedDevicesLayer.clearLayers();
  // Initial notification.
  Toastify({
    text: "Refreshing tracked device data",
    duration: 1500
  }).showToast();
  // Query the API endpoint for device data.
  $.getJSON(
    device_geojson_url,
    function (data) {
      // Add the device data to the GeoJSON layer.
      trackedDevicesLayer.addData(data);
      // Success notification.
      Toastify({
        text: "Tracked device data refreshed",
        duration: 1500
      }).showToast();
    },
  );
};
// Immediately run the function, once.
refreshTrackedDevicesLayer(trackedDevices);

// Define map.
var map = L.map('map', {
  crs: L.CRS.EPSG4326,  // WGS 84
  center: [-31.96, 115.87],
  zoom: 12,
  minZoom: 4,
  maxZoom: 18,
  layers: [mapboxStreets, trackedDevices],  // Sets default selections.
  attributionControl: false,
});

// Define layer groups.
var baseMaps = {
  'Mapbox streets': mapboxStreets,
  'Landgate orthomosaic': landgateOrthomosaic,
  'State map base 250K': stateMapBase,
};
var overlayMaps = {
  'Tracked devices': trackedDevices,
  'DBCA Going Bushfires': dbcaBushfires,
  'DFES Going Bushfires': dfesBushfires,
  'DBCA regions': dbcaRegions,
  'LGA boundaries': lgaBoundaries,
};

// Define layer control.
L.control.layers(baseMaps, overlayMaps).addTo(map);

// Define scale bar
L.control.scale({ maxWidth: 500, imperial: false }).addTo(map);

// Add a fullscreen control to the map.
const fullScreen = new L.control.fullscreen();
map.addControl(fullScreen);

// Device registration search
const searchControl = new L.Control.Search({
  layer: trackedDevices,
  propertyName: 'registration',
  textPlaceholder: 'Search registration',
  delayType: 1000,
  textErr: 'Registration not found',
  zoom: 16,
  circleLocation: true,
  autoCollapse: true
});
map.addControl(searchControl);

const refreshButton = L.easyButton(
  `<img src="${refresh_icon_url}">`,
  function (btn, map) {
    refreshTrackedDevicesLayer(trackedDevices);
  }
).addTo(map);
