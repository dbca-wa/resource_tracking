'use strict';

// Parse additional variables from the DOM element.
const context = JSON.parse(document.getElementById('javascript_context').textContent);

const geoserver_wmts_url = `${context.geoserver_url}/gwc/service/wmts?service=WMTS&request=GetTile&version=1.0.0&tilematrixset=mercator&tilematrix=mercator:{z}&tilecol={x}&tilerow={y}`;
const geoserver_wmts_url_base = `${geoserver_wmts_url}&format=image/jpeg`;
const geoserver_wmts_url_overlay = `${geoserver_wmts_url}&format=image/png`;

// Base layers
const mapboxStreets = L.tileLayer(`${geoserver_wmts_url_base}&layer=dbca:mapbox-streets`);
const landgateOrthomosaic = L.tileLayer(`${geoserver_wmts_url_base}&layer=landgate:virtual_mosaic`);
const stateMapBase = L.tileLayer(`${geoserver_wmts_url_base}&layer=cddp:state_map_base`);
const openStreetMap = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png');

// Overlay layers
const dbcaBushfires = L.tileLayer(`${geoserver_wmts_url_overlay}&layer=landgate:dbca_going_bushfires_dbca-001`, {
  transparent: true,
  opacity: 0.75,
});
const dfesBushfires = L.tileLayer(`${geoserver_wmts_url_overlay}&layer=landgate:authorised_fireshape_dfes-032`, {
  transparent: true,
  opacity: 0.75,
});
const dbcaRegions = L.tileLayer(`${geoserver_wmts_url_overlay}&layer=cddp:kaartdijin-boodja-public_CPT_DBCA_REGIONS`, { opacity: 0.75 });
const lgaBoundaries = L.tileLayer(`${geoserver_wmts_url_overlay}&layer=cddp:local_gov_authority`, { opacity: 0.75 });

// Icon classes (note that URLs are injected into the base template.)
const iconCar = L.icon({
  iconUrl: context.car_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconUte = L.icon({
  iconUrl: context.ute_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconLightUnit = L.icon({
  iconUrl: context.light_unit_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconGangTruck = L.icon({
  iconUrl: context.gang_truck_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconCommsBus = L.icon({
  iconUrl: context.comms_bus_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconRotary = L.icon({
  iconUrl: context.rotary_aircraft_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconPlane = L.icon({
  iconUrl: context.plane_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconDozer = L.icon({
  iconUrl: context.dozer_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconLoader = L.icon({
  iconUrl: context.loader_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconFloat = L.icon({
  iconUrl: context.float_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconFuelTruck = L.icon({
  iconUrl: context.fuel_truck_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconPerson = L.icon({
  iconUrl: context.person_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const iconOther = L.icon({
  iconUrl: context.other_icon_url,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

const toastRefresh = bootstrap.Toast.getOrCreateInstance(document.getElementById('toastRefresh'));
const toastError = bootstrap.Toast.getOrCreateInstance(document.getElementById('toastError'));

// Define layer groups.
const baseMaps = {
  OpenStreetMap: openStreetMap,
  'Mapbox streets': mapboxStreets,
  'Landgate orthomosaic': landgateOrthomosaic,
  'State map base 250K': stateMapBase,
};
const overlayMaps = {
  'DBCA Going Bushfires': dbcaBushfires,
  'DFES Going Bushfires': dfesBushfires,
  'DBCA regions': dbcaRegions,
  'LGA boundaries': lgaBoundaries,
};
const map = L.map('map', {
  center: [-31.96, 115.87],
  zoom: 12,
  minZoom: 4,
  maxZoom: 18,
  layers: [openStreetMap],
  attributionControl: false,
});
// Scale bar
L.control.scale({ maxWidth: 500, imperial: false }).addTo(map);
// Fullscreen control
L.control.fullscreen().addTo(map);
// Link to device list view.
L.easyButton('fa-solid fa-list', () => window.open(context.device_list_url, '_self'), 'Device list', 'idDeviceListControl').addTo(map);
