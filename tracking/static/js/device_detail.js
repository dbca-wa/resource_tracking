// Function to style the marker icon.
function setDeviceMarkerIcon(device, marker) {
  if (device.icon == 'sss-2_wheel_drive') {
    marker.setIcon(iconCar);
  } else if (device.icon == 'sss-4_wheel_drive_passenger') {
    marker.setIcon(iconCar);
  } else if (device.icon == 'sss-4_wheel_drive_ute') {
    marker.setIcon(iconUte);
  } else if (device.icon == 'sss-light_unit') {
    marker.setIcon(iconLightUnit);
  } else if (device.icon == 'sss-gang_truck') {
    marker.setIcon(iconGangTruck);
  } else if (device.icon == 'sss-comms_bus') {
    marker.setIcon(iconCommsBus);
  } else if (device.icon == 'sss-rotary_aircraft') {
    marker.setIcon(iconRotary);
  } else if (device.icon == 'sss-spotter_aircraft') {
    marker.setIcon(iconPlane);
  } else if (device.icon == 'sss-dozer') {
    marker.setIcon(iconDozer);
  } else if (device.icon == 'sss-float') {
    marker.setIcon(iconFloat);
  } else if (device.icon == 'sss-loader') {
    marker.setIcon(iconLoader);
  } else if (device.icon == 'sss-aviation_fuel_truck') {
    marker.setIcon(iconFuelTruck);
  } else if (device.icon == 'sss-person') {
    marker.setIcon(iconPerson);
  } else if (device.icon == 'sss-boat') {
    marker.setIcon(iconBoat);
  } else {
    marker.setIcon(iconOther);
  }
}

// Define the (initially) empty device layer and add it to the map.
const trackedDeviceLayer = L.geoJSON(null, {}).addTo(map);

// Layers control.
L.control.layers(baseMaps, overlayMaps).addTo(map);
// Link to device map view.
L.easyButton('fa-solid fa-map', () => window.open(context.device_map_url, '_self'), 'Device map', 'idDeviceMapControl').addTo(map);

// Function to consume streamed device data and repopulate the layer.
function refreshTrackedDeviceLayer(trackedDeviceLayer, device) {
  // Declare a regex pattern to parse the EWKT string.
  const pattern = /^.+\((?<lon>.+)\s(?<lat>.+)\)/;
  const point = pattern.exec(device.point).groups;
  // Remove any existing data from the layer.
  trackedDeviceLayer.clearLayers();
  // Generate a marker for the device and add it to the layer.
  const deviceMarker = L.marker([point.lat, point.lon]);
  // Set the marker icon.
  setDeviceMarkerIcon(device, deviceMarker);
  // Add the marker to the layer and fly to that location.
  deviceMarker.addTo(trackedDeviceLayer);
  map.flyTo([point.lat, point.lon], map.getZoom());
}

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
  const device = JSON.parse(event.data);
  device.seen = new Date(device.seen);
  deviceDataEl.innerHTML = `Identifier: ${device.deviceid}<br>
    Registration: ${device.registration}<br>
    Type: ${device.type}<br>
    Last seen: ${device.seen.toString()}`;
  refreshTrackedDeviceLayer(trackedDeviceLayer, device);
  toastRefresh.show();
};
eventSource.onerror = () => toastError.show();
