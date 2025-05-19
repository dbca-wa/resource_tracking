'use strict';

// Define the (initially) empty device layer and add it to the map.
const trackedDeviceLayer = L.geoJSON(null, {
  onEachFeature: setDeviceStyle,
}).addTo(map);

// Define an empty device route polyline object and add it to the map.
let trackedDeviceRoute = new L.Polyline([], {}).addTo(map);

// Link to device map view.
L.easyButton('fa-solid fa-map', () => window.open(context.device_map_url, '_self'), 'Device map', 'idDeviceMapControl').addTo(map);

const refreshTrackedDeviceLayer = function (data) {
  const feature_properties = data;
  feature_properties.seen = new Date(feature_properties.seen);
  // Update the top row HTML content.
  deviceDataEl.innerHTML = `Device ID: ${feature_properties.deviceid}<br>
    Registration: ${feature_properties.registration}<br>
    Type: ${feature_properties.type}<br>
    Last seen: ${feature_properties.seen.toString()}`;
  // Wrangle the single feature into a GeoJSON Feature to replace the layer contents.
  const pattern = /^.+\((?<lon>.+)\s(?<lat>.+)\)/;
  const point = pattern.exec(feature_properties.point).groups;
  const geojson = {
    type: 'Feature',
    properties: feature_properties,
    geometry: {
      type: 'Point',
      coordinates: [point.lon, point.lat],
    },
  };
  // Remove existing data from the layer, then re-add the updated data.
  trackedDeviceLayer.clearLayers();
  trackedDeviceLayer.addData(geojson);
  map.flyTo([point.lat, point.lon], map.getZoom());
  toastRefresh.show();
};

// The EventSource URL is defined on the HTML template.
let eventSource = new EventSource(context.event_source_url);
// Ping event, to help maintain the connection.
let ping = 0;
eventSource.addEventListener('ping', function (event) {
  ping++;
});

// The standard "message" event indicates that the device has updated.
const deviceDataEl = document.getElementById('device-data-stream');
eventSource.onmessage = function (event) {
  refreshTrackedDeviceLayer(JSON.parse(event.data));
};
eventSource.onerror = () => toastError.show();

// Function to query the tracking device's route data for the previous n hours
function queryDeviceRoute(hours) {
  let start = new Date();
  start.setHours(start.getHours() - hours);
  const url = `${context.device_route_url}?start=${start.toISOString()}`;
  fetch(url)
    // Parse the response as JSON.
    .then((resp) => resp.json())
    .then(function (data) {
      let deviceRouteFeatures = [];
      // Instantiate a Polyline object from the list of coordinates.
      for (const feature of data['features']) {
        const coord = feature['geometry']['coordinates'][0];
        // GeoJSON coordinates are returned in [x, y], so reverse these for [lat, lng].
        deviceRouteFeatures.push([coord[1], coord[0]]);
      }
      trackedDeviceRoute.setLatLngs(deviceRouteFeatures);
    });
}
// Immediately run the query device route function to populate the polyline.
queryDeviceRoute(24);

// Function to prepend a new point to the device route polyline.
function updateDeviceRoute(point) {
  let deviceRouteFeatures = trackedDeviceRoute.getLatLngs();
  deviceRouteFeatures = [[point['lat'], point['lon']], ...deviceRouteFeatures];
  trackedDeviceRoute.setLatLngs(deviceRouteFeatures);
}
