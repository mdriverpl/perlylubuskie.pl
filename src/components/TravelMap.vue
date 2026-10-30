<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as L from 'leaflet/dist/leaflet-src.esm.js'
const props = defineProps({ places: Array, focusLocation: Object, selected: {type:Array,default:()=>[]}, geometry: Object, geometryApproximate: Boolean, draggablePoints: Boolean, userLocation: Object, searchLocation: Object, fitPlaces: Boolean, allowCustomPoints: Boolean })
const emit = defineEmits(['select','create-point','move-point'])
let map, layer, tiles, resizeObserver, disposed=false, copyrights={},lastViewportKey,lastGeometry,lastFocus
const provider=ref('osm'), mapStyle=ref('terrain'), mapError=ref('')
const osmAttribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
function hereAttribution(){
 const bounds=map.getBounds(),zoom=map.getZoom()
 const labels=(copyrights[mapStyle.value]||[]).filter(n=>zoom>=(n.minLevel??0)&&zoom<=(n.maxLevel??20)&&(!n.boxes?.length||n.boxes.some(b=>bounds.intersects([[b[0],b[1]],[b[2],b[3]]])))).map(n=>String(n.label||''))
 const text=document.createElement('span');text.textContent=[...new Set(labels)].filter(Boolean).join(', ')
 return `© ${new Date().getFullYear()} <a href="https://legal.here.com/terms/general-content-supplier-terms-and-notices" target="_blank" rel="noopener noreferrer">HERE</a>${text.textContent?', '+text.innerHTML:''}`
}
let attribution=''
function updateAttribution(){
 if(provider.value!=='here'||!map)return
 if(attribution)map.attributionControl.removeAttribution(attribution)
 attribution=hereAttribution();map.attributionControl.addAttribution(attribution)
}
function setTiles(){
 if(!map||disposed)return
 if(attribution){map.attributionControl.removeAttribution(attribution);attribution=''}
 if(tiles){map.removeLayer(tiles);tiles.off()}
 const here=provider.value==='here'
 tiles=L.tileLayer(here?`/api/maps/tiles/${mapStyle.value}/{z}/{x}/{y}`:'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:here?'':osmAttribution,maxZoom:here?20:18,updateWhenIdle:true})
 if(here)tiles.once('tileerror',()=>{if(disposed)return;mapError.value='Mapy HERE są niedostępne. Wyświetlam OpenStreetMap.';provider.value='osm';setTiles()})
 tiles.addTo(map);updateAttribution()
}
const mapElement=ref(null)
function draw() {
 if (!map) return
 const catalogPoints=props.places.filter(p=>p.details?.kind!=='custom')
 const viewportKey=JSON.stringify([catalogPoints.map(p=>[p.id,p.lat,p.lng]).sort((a,b)=>a[0]-b[0]),props.userLocation?.lat,props.userLocation?.lng,props.searchLocation?.lat,props.searchLocation?.lng])
 const refit=viewportKey!==lastViewportKey||props.geometry!==lastGeometry
 lastViewportKey=viewportKey;lastGeometry=props.geometry
 layer.clearLayers()
 props.places.forEach(p => {
  const index = props.selected.indexOf(p.id)
  const label=document.createElement('span'); label.textContent=p.name
  const marker=L.marker([p.lat,p.lng], { draggable:props.draggablePoints&&index>=0, icon: L.divIcon({ className: '', html: `<span class="map-pin ${p.details?.kind==='custom'?'custom-point':''} ${index >= 0 ? 'chosen' : ''}">${index >= 0 ? index + 1 : '•'}</span>`, iconSize: [32,32], iconAnchor: [16,32] }) }).addTo(layer).bindTooltip(label).on('click', () => emit('select', p.id))
  marker.on('dragend',()=>{const {lat,lng}=marker.getLatLng();emit('move-point',{id:p.id,lat:+lat.toFixed(6),lng:+lng.toFixed(6)})})
 })
 if(props.userLocation){
  const {lat,lng,accuracy}=props.userLocation
  if(accuracy)L.circle([lat,lng],{radius:accuracy,color:'#1876d2',weight:1,fillOpacity:.08}).addTo(layer)
  L.circleMarker([lat,lng],{radius:8,color:'#fff',weight:3,fillColor:'#1876d2',fillOpacity:1}).addTo(layer).bindTooltip('Tu jesteś')
 }
 if(props.searchLocation){
  const point=props.searchLocation
  const label=document.createElement('span');label.textContent=point.name
  L.circleMarker([point.lat,point.lng],{radius:9,color:'#fff',weight:3,fillColor:'#ce7b28',fillOpacity:1}).addTo(layer).bindTooltip(label,{permanent:true,direction:'top'})
 }
 const focus=props.focusLocation
 const focusChanged=focus!==lastFocus;lastFocus=focus
 if(Number.isFinite(focus?.lat)&&Math.abs(focus.lat)<=90&&Number.isFinite(focus?.lng)&&Math.abs(focus.lng)<=180){
  if(refit||focusChanged)map.setView([focus.lat,focus.lng],Number.isFinite(focus.zoom)?Math.max(8,Math.min(16,focus.zoom)):14)
  return
 }
 const points = props.geometry?.coordinates?.map(p=>[p[1],p[0]]) || []
 if(points.length > 1) {
  const line=L.polyline(points, { color: '#1685d2', weight: 5, dashArray:props.geometryApproximate?'8 8':undefined }).addTo(layer)
  if(refit)map.fitBounds(line.getBounds(),{padding:[45,45],maxZoom:14})
 }
 else if(props.searchLocation){if(refit)map.setView([props.searchLocation.lat,props.searchLocation.lng],13)}
 else if(props.fitPlaces&&refit){
  const bounds=(props.allowCustomPoints&&catalogPoints.length?catalogPoints:props.places).map(p=>[p.lat,p.lng])
  if(bounds.length)map.fitBounds(bounds,{padding:[45,45],maxZoom:13})
  else map.setView([52.15,15.16],8)
 }
}
onMounted(async () => {
 map=L.map(mapElement.value,{scrollWheelZoom:false,doubleClickZoom:!props.allowCustomPoints}).setView([52.15,15.16],8)
 map.on('dblclick',event=>{
  if(!props.allowCustomPoints||event.originalEvent?.target?.closest?.('.leaflet-marker-icon,.leaflet-control'))return
  const {lat,lng}=event.latlng||{}
  if(Number.isFinite(lat)&&Number.isFinite(lng)&&lat>=-90&&lat<=90&&lng>=-180&&lng<=180)emit('create-point',{lat:+lat.toFixed(6),lng:+lng.toFixed(6)})
 })
 setTiles();map.on('moveend zoomend',updateAttribution)
 layer=L.layerGroup().addTo(map); draw()
 if(typeof ResizeObserver!=='undefined'){
  resizeObserver=new ResizeObserver(()=>{if(!disposed){map.invalidateSize({pan:false});lastViewportKey=undefined;draw()}})
  resizeObserver.observe(mapElement.value)
 }
 try{
  const response=await fetch('/api/maps/config',{signal:AbortSignal.timeout(12000)})
  if(!response.ok){
   const error=await response.json()
   if(!disposed&&typeof error.detail==='string')mapError.value=error.detail+' Wyświetlam OpenStreetMap.'
   throw Error('Map config unavailable')
  }
  const config=await response.json()
  if(disposed)return
  if(config.provider==='here'){copyrights=config.copyrights||{};provider.value='here';setTiles()}
 }catch{if(!disposed&&!mapError.value)mapError.value='Nie udało się wczytać map HERE. Wyświetlam OpenStreetMap.'}
})
watch(mapStyle,setTiles)
watch(()=>[props.selected,props.places,props.geometry,props.userLocation,props.searchLocation,props.draggablePoints,props.focusLocation],draw,{deep:true})
onBeforeUnmount(()=>{disposed=true;resizeObserver?.disconnect();map?.remove();tiles?.off()})
</script>
<template><div class="travel-map"><div ref="mapElement" class="travel-map-canvas" aria-label="Mapa miejsc w województwie lubuskim"></div><div v-if="provider==='here'" class="map-style-switch" role="group" aria-label="Rodzaj mapy HERE"><button v-for="style in [{id:'map',label:'Mapa'},{id:'satellite',label:'Satelita'},{id:'terrain',label:'Teren'}]" :key="style.id" :aria-pressed="mapStyle===style.id" @click="mapStyle=style.id">{{style.label}}</button></div><p v-if="mapError" class="map-provider-error" role="status">{{mapError}}</p></div></template>
<style scoped>
.travel-map{position:relative;width:100%;height:100%;min-height:inherit}.map-style-switch{position:absolute;top:14px;right:14px;z-index:500;display:flex;gap:3px;padding:4px;background:#fff;border-radius:22px;box-shadow:0 2px 9px #173d2920}.map-style-switch button{font:600 11px/1.4 system-ui;padding:8px 12px;border:0;border-radius:18px;background:transparent;color:#294b36;cursor:pointer}.map-style-switch button[aria-pressed=true]{background:#18774f;color:white}.map-provider-error{position:absolute;bottom:36px;left:12px;right:12px;z-index:500;background:#fff8e9ed;padding:9px 12px;border-radius:7px;font:11px/1.5 system-ui;color:#775024;pointer-events:none}
</style>
<style scoped>
@media(max-width:600px){.map-style-switch{top:58px;right:12px}}
</style>
