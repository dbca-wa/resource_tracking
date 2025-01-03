"use strict";

const geoserver_wmts_url =
  geoserver_url +
  "/gwc/service/wmts?service=WMTS&request=GetTile&version=1.0.0&tilematrixset=mercator&tilematrix=mercator:{z}&tilecol={x}&tilerow={y}";
const geoserver_wmts_url_base = geoserver_wmts_url + "&format=image/jpeg";
const geoserver_wmts_url_overlay = geoserver_wmts_url + "&format=image/png";

// Base layers
const mapboxStreets = L.tileLayer(geoserver_wmts_url_base + "&layer=dbca:mapbox-streets");
const landgateOrthomosaic = L.tileLayer(geoserver_wmts_url_base + "&layer=landgate:virtual_mosaic");
const stateMapBase = L.tileLayer(geoserver_wmts_url_base + "&layer=cddp:state_map_base");
const openStreetMap = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png");

// Overlay layers
const dbcaBushfires = L.tileLayer(geoserver_wmts_url_overlay + "&layer=landgate:dbca_going_bushfires_dbca-001", {
  transparent: true,
  opacity: 0.75,
});
const dfesBushfires = L.tileLayer(geoserver_wmts_url_overlay + "&layer=landgate:authorised_fireshape_dfes-032", {
  transparent: true,
  opacity: 0.75,
});
const dbcaRegions = L.tileLayer(geoserver_wmts_url_overlay + "&layer=cddp:kaartdijin-boodja-public_CPT_DBCA_REGIONS");
const lgaBoundaries = L.tileLayer(geoserver_wmts_url_overlay + "&layer=cddp:local_gov_authority");

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

const toastRefresh = bootstrap.Toast.getOrCreateInstance(document.getElementById("toastRefresh"));
const toastError = bootstrap.Toast.getOrCreateInstance(document.getElementById("toastError"));
const map = L.map("map", {
  center: [-31.96, 115.87],
  zoom: 12,
  minZoom: 4,
  maxZoom: 18,
  // layers: [mapboxStreets, trackedDevices], // Sets default selections.
  attributionControl: false,
});
// Scale bar
L.control.scale({ maxWidth: 500, imperial: false }).addTo(map);
// Fullscreen control
L.control.fullscreen().addTo(map);
// Link to device list view.
L.easyButton("fa-solid fa-list", () => window.open(device_list_url, "_self"), "Device list", "idDeviceListControl").addTo(map);

// Define layer groups.
const baseMaps = {
  "Mapbox streets": mapboxStreets,
  "Landgate orthomosaic": landgateOrthomosaic,
  "State map base 250K": stateMapBase,
  OpenStreetMap: openStreetMap,
};
const overlayMaps = {
  "DBCA Going Bushfires": dbcaBushfires,
  "DFES Going Bushfires": dfesBushfires,
  "DBCA regions": dbcaRegions,
  "LGA boundaries": lgaBoundaries,
};
