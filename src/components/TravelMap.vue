<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as L from 'leaflet/dist/leaflet-src.esm.js'
const props = defineProps({ places: Array, selected: {type:Array,default:()=>[]}, geometry: Object, userLocation: Object, fitPlaces: Boolean })
const emit = defineEmits(['select'])
let map, layer
const mapElement=ref(null)
function draw() {
 if (!map) return
 layer.clearLayers()
 props.places.forEach(p => {
  const index = props.selected.indexOf(p.id)
  const label=document.createElement('span'); label.textContent=p.name
  L.marker([p.lat,p.lng], { icon: L.divIcon({ className: '', html: `<span class="map-pin ${index >= 0 ? 'chosen' : ''}">${index >= 0 ? index + 1 : '•'}</span>`, iconSize: [32,32], iconAnchor: [16,32] }) }).addTo(layer).bindTooltip(label).on('click', () => emit('select', p.id))
 })
 if(props.userLocation){
  const {lat,lng,accuracy}=props.userLocation
  if(accuracy)L.circle([lat,lng],{radius:accuracy,color:'#1876d2',weight:1,fillOpacity:.08}).addTo(layer)
  L.circleMarker([lat,lng],{radius:8,color:'#fff',weight:3,fillColor:'#1876d2',fillOpacity:1}).addTo(layer).bindTooltip('Tu jesteś')
 }
 const points = props.geometry?.coordinates?.map(p=>[p[1],p[0]]) || []
 if(points.length > 1) {
  const line=L.polyline(points, { color: '#1685d2', weight: 5 }).addTo(layer)
  map.fitBounds(line.getBounds(),{padding:[45,45],maxZoom:14})
 }
 else if(props.fitPlaces){
  const bounds=props.places.map(p=>[p.lat,p.lng])
  if(props.userLocation)bounds.push([props.userLocation.lat,props.userLocation.lng])
  if(bounds.length)map.fitBounds(bounds,{padding:[45,45],maxZoom:13})
  else map.setView([52.15,15.16],8)
 }
}
onMounted(() => {
 map=L.map(mapElement.value,{scrollWheelZoom:false}).setView([52.15,15.16],8)
 L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom:18}).addTo(map)
 layer=L.layerGroup().addTo(map); draw()
})
watch(()=>[props.selected,props.places,props.geometry,props.userLocation],draw,{deep:true})
onBeforeUnmount(()=>map?.remove())
</script>
<template><div ref="mapElement" class="travel-map-canvas" aria-label="Mapa miejsc w województwie lubuskim"></div></template>
