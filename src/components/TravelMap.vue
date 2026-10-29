<script setup>
import { onMounted, onBeforeUnmount, watch } from 'vue'
import * as L from 'leaflet/dist/leaflet-src.esm.js'
const props = defineProps({ places: Array, selected: Array })
const emit = defineEmits(['select'])
let map, layer
function draw() {
 if (!map) return
 layer.clearLayers()
 props.places.forEach(p => {
  const index = props.selected.indexOf(p.id)
  const label=document.createElement('span'); label.textContent=p.name
  L.marker([p.lat,p.lng], { icon: L.divIcon({ className: '', html: `<span class="map-pin ${index >= 0 ? 'chosen' : ''}">${index >= 0 ? index + 1 : '•'}</span>`, iconSize: [32,32], iconAnchor: [16,32] }) }).addTo(layer).bindTooltip(label).on('click', () => emit('select', p.id))
 })
 const points = props.selected.map(id => props.places.find(p=>p.id===id)).filter(Boolean).map(p=>[p.lat,p.lng])
 if(points.length > 1) L.polyline(points, { color: '#1685d2', weight: 4, dashArray: '8 8' }).addTo(layer)
}
onMounted(() => {
 map=L.map('travel-map',{scrollWheelZoom:false}).setView([52.15,15.16],8)
 L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom:18}).addTo(map)
 layer=L.layerGroup().addTo(map); draw()
})
watch(()=>[props.selected,props.places],draw,{deep:true})
onBeforeUnmount(()=>map?.remove())
</script>
<template><div id="travel-map" aria-label="Mapa miejsc w województwie lubuskim"></div></template>
