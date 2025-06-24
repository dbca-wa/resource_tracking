'use strict';

// Define the (initially) empty devices layer and add it to the map.
const trackedDevicesLayer = L.geoJSON(null, {
  // onEachFeature is a function called on each feature in the layer. It receives two arguments:
  // `feature` (the GeoJSON feature) and `layer` (the Leaflet layer that created the feature).
  onEachFeature: setDeviceStyle,
}).addTo(map);

// Function to refresh tracking devices from the source endpoint.
function refreshTrackedDevicesLayer(trackedDevicesLayer) {
  // Remove any existing data from the layer.
  trackedDevicesLayer.clearLayers();
  // Get the current map bounds.
  const bounds = map.getBounds();
  const ne = bounds.getNorthEast();
  const [lat1, lng1] = [ne['lat'], ne['lng']];
  const sw = bounds.getSouthWest();
  const [lat2, lng2] = [sw['lat'], sw['lng']];
  // Query the API endpoint for device data.
  const url = `${context.device_geojson_url}?days=14&bbox=${lat1},${lng1},${lat2},${lng2}`;
  fetch(url)
    // Parse the response as GeoJSON.
    //.then((resp) => resp.json())
    .then(function (resp) {
      return resp.json();
    })
    // Replace the data in the tracked devices layer.
    .then(function (data) {
      // Add the device data to the GeoJSON layer.
      trackedDevicesLayer.addData(data);
      // Success notification.
      toastRefresh.show();
    })
    // Error notification.
    .catch(function () {
      toastError.show();
    });
}
// Immediately run the "refresh" function to populate the layer.
refreshTrackedDevicesLayer(trackedDevicesLayer);
// Begin a timer to refresh the tracked devices layer every 60 seconds.
let trackedDevicesLayerTimer = setInterval(refreshTrackedDevicesLayer, 60000, trackedDevicesLayer);

const formatDeviceListData = function (geojson) {
  // The formatData callback function needs to return an object having
  // See the _defaultFormatData function of the Leaflet Search control.
  const devices = {};

  for (const feature of geojson.features) {
    devices[feature.properties.registration] = L.latLng(feature.geometry.coordinates[1], feature.geometry.coordinates[0]);
  }
  return devices;
};

// Device registration search control.
new L.Control.Search({
  // url endpoint is queried for a GeoJSON response.
  url: `${context.device_list_url}?q={s}&format=json`,
  // formatData is a callback that formats the response so Leaflet Search can use it.
  formatData: formatDeviceListData,
  tooltipLimit: 10,
  textPlaceholder: 'Search registration',
  delayType: 1000,
  textErr: 'Not found',
  zoom: 16,
  circleLocation: true,
  autoCollapse: true,
}).addTo(map);

// Map zoom and move events.
// The moveend event covers panning and zooming.
map.on('moveend', function (_) {
  refreshTrackedDevicesLayer(trackedDevicesLayer);
  // Reset the interval timer and start a new one.
  clearInterval(trackedDevicesLayerTimer);
  trackedDevicesLayerTimer = setInterval(refreshTrackedDevicesLayer, 60000, trackedDevicesLayer);
});
