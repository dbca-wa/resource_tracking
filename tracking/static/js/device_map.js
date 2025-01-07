"use strict";

// Function to set the icon and popup for each device feature added to the layer.
function setDeviceStyle(feature, layer) {
  let callsign;
  if (feature.properties.callsign) {
    callsign = feature.properties.callsign;
  } else {
    callsign = "";
  }
  layer.bindPopup(
    `ID: ${feature.properties.id}<br>
    Registration: ${feature.properties.registration}<br>
    Callsign: ${callsign}<br>
    Type: ${feature.properties.symbol}<br>
    Seen: ${feature.properties.age_text}<br>
    <a href="/devices/${feature.properties.id}/">Follow</a>`
  );
  // Set the feature icon.
  if (feature.properties.icon == "sss-2_wheel_drive") {
    layer.setIcon(iconCar);
  } else if (feature.properties.icon == "sss-4_wheel_drive_passenger") {
    layer.setIcon(iconCar);
  } else if (feature.properties.icon == "sss-4_wheel_drive_ute") {
    layer.setIcon(iconUte);
  } else if (feature.properties.icon == "sss-light_unit") {
    layer.setIcon(iconLightUnit);
  } else if (feature.properties.icon == "sss-gang_truck") {
    layer.setIcon(iconGangTruck);
  } else if (feature.properties.icon == "sss-comms_bus") {
    layer.setIcon(iconCommsBus);
  } else if (feature.properties.icon == "sss-rotary_aircraft") {
    layer.setIcon(iconRotary);
  } else if (feature.properties.icon == "sss-spotter_aircraft") {
    layer.setIcon(iconPlane);
  } else if (feature.properties.icon == "sss-dozer") {
    layer.setIcon(iconDozer);
  } else if (feature.properties.icon == "sss-float") {
    layer.setIcon(iconFloat);
  } else if (feature.properties.icon == "sss-loader") {
    layer.setIcon(iconLoader);
  } else if (feature.properties.icon == "sss-aviation_fuel_truck") {
    layer.setIcon(iconFuelTruck);
  } else if (feature.properties.icon == "sss-person") {
    layer.setIcon(iconPerson);
  } else {
    layer.setIcon(iconOther);
  }
}

// Define the (initially) empty devices layer and add it to the map.
const trackedDevices = L.geoJSON(null, {
  onEachFeature: setDeviceStyle,
}).addTo(map);

// Function to refresh tracking devices from the source endpoint.
function refreshTrackedDevicesLayer(trackedDevicesLayer) {
  // Remove any existing data from the layer.
  trackedDevicesLayer.clearLayers();
  // Query the API endpoint for device data.
  fetch(context.device_geojson_url)
    // Parse the response as JSON.
    .then((resp) => resp.json())
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
refreshTrackedDevicesLayer(trackedDevices);

// Layers control.
L.control.layers(baseMaps, overlayMaps).addTo(map);

// Device registration search
new L.Control.Search({
  layer: trackedDevices,
  propertyName: "registration",
  textPlaceholder: "Search registration",
  delayType: 1000,
  textErr: "Registration not found",
  zoom: 16,
  circleLocation: true,
  autoCollapse: true,
}).addTo(map);
//
// Refresh tracked devices control.
L.easyButton("fa-solid fa-arrows-rotate", function () {
  refreshTrackedDevicesLayer(trackedDevices);
}).addTo(map);
