"use strict";

// Define the (initially) empty device layer.
const trackedDeviceLayer = L.geoJSON(null, {});

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

// Function to style the marker icon.
function setDeviceMarkerIcon(device, marker) {
  if (device.icon == "sss-2_wheel_drive") {
    marker.setIcon(iconCar);
  } else if (device.icon == "sss-4_wheel_drive_passenger") {
    marker.setIcon(iconCar);
  } else if (device.icon == "sss-4_wheel_drive_ute") {
    marker.setIcon(iconUte);
  } else if (device.icon == "sss-light_unit") {
    marker.setIcon(iconLightUnit);
  } else if (device.icon == "sss-gang_truck") {
    marker.setIcon(iconGangTruck);
  } else if (device.icon == "sss-comms_bus") {
    marker.setIcon(iconCommsBus);
  } else if (device.icon == "sss-rotary_aircraft") {
    marker.setIcon(iconRotary);
  } else if (device.icon == "sss-spotter_aircraft") {
    marker.setIcon(iconPlane);
  } else if (device.icon == "sss-dozer") {
    marker.setIcon(iconDozer);
  } else if (device.icon == "sss-float") {
    marker.setIcon(iconFloat);
  } else if (device.icon == "sss-loader") {
    marker.setIcon(iconLoader);
  } else if (device.icon == "sss-aviation_fuel_truck") {
    marker.setIcon(iconFuelTruck);
  } else if (device.icon == "sss-person") {
    marker.setIcon(iconPerson);
  } else {
    marker.setIcon(iconOther);
  }
}

// Define map.
const map = L.map("map", {
  center: [-31.96, 115.87],
  zoom: 12,
  minZoom: 4,
  maxZoom: 18,
  layers: [trackedDeviceLayer],
});
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

function refreshTrackedDeviceLayer(trackedDeviceLayer, device) {
  // Declare a regex pattern to parse the EWKT string.
  const pattern = /^.+\((?<lon>.+)\s(?<lat>.+)\)/;
  const point = pattern.exec(device.point).groups;
  // Remove any existing data from the layer.
  trackedDeviceLayer.clearLayers();
  // Generate a marker for the device and add it to the layer.
  //const marker = L.marker([point.lat, point.lon], {});
  const deviceMarker = L.marker([point.lat, point.lon], {});
  // Set the marker icon.
  setDeviceMarkerIcon(device, deviceMarker);
  // Add the marker to the layer.
  deviceMarker.addTo(trackedDeviceLayer);
  map.flyTo([point.lat, point.lon], map.getZoom());
}

const deviceDataEl = document.getElementById("device-data-stream");
let ping = 0;

// Ping event, to help maintain the connection.
eventSource.addEventListener("ping", function (event) {
  ping++;
  // console.log("ping");
});

// The standard "message" event indicates that the device has updated.
eventSource.onmessage = function (event) {
  const device = JSON.parse(event.data);
  device.seen = new Date(device.seen);
  deviceDataEl.innerHTML = `Identifier: ${device.deviceid}<br>
    Last seen: ${device.seen.toString()}<br>
    Registration: ${device.registration}<br>
    Type: ${device.type}`;
  refreshTrackedDeviceLayer(trackedDeviceLayer, device);
  Toastify({
    text: "Device location updated",
    duration: 1500,
  }).showToast();
};

const deviceListLink = L.easyButton("fa-solid fa-list", function () {
  window.open(device_list_url, "_self");
}).addTo(map);
