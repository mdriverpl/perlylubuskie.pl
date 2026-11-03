<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as L from 'leaflet/dist/leaflet-src.esm.js'
import {readApiJson} from '../apiResponse.js'
import {preferredMap,rememberMap,osmTileUrl} from '../mapPreferences.js'
import {pointClusters,validMapPoint} from '../mapClusters.js'
const props = defineProps({ places: Array, trackOnly:Boolean, minimal:Boolean, focusLocation: Object, distanceArea: Object, selected: {type:Array,default:()=>[]}, geometry: Object, geometryApproximate: Boolean, draggablePoints: Boolean, userLocation: Object, searchLocation: Object, fitPlaces: Boolean, allowCustomPoints: Boolean })
const emit = defineEmits(['select','create-point','move-point'])
let map, layer, markerLayer, tiles, resizeObserver, disposed=false, copyrights={},lastViewportKey,lastGeometry,lastFocus,clusterIndex,clusterKey,hereErrors=0
const provider=ref('osm'), mapStyle=ref('terrain'), mapError=ref(''),switchingMap=ref(false)
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
 if(tiles){map.removeLayer(tiles);tiles.off();tiles=null}
 if(props.trackOnly)return
 const here=provider.value==='here'
 hereErrors=0
 map.setMaxZoom(here?20:19)
 tiles=L.tileLayer(here?`/api/maps/tiles/${mapStyle.value}/{z}/{x}/{y}`:osmTileUrl,{attribution:here?'':osmAttribution,maxZoom:here?20:19,updateWhenIdle:true,keepBuffer:1})
 if(here)tiles.on('tileerror',()=>{if(disposed||++hereErrors<3)return;mapError.value='Nie udało się wczytać map HERE. Dostępna jest mapa OpenStreetMap.';provider.value='osm';setTiles()})
 else tiles.on('tileerror',()=>{if(!disposed&&++hereErrors>=3)mapError.value='Mapa OpenStreetMap jest chwilowo niedostępna. Spróbuj ponownie lub wybierz HERE.'})
 tiles.addTo(map);updateAttribution()
}
async function selectProvider(value){
 if(switchingMap.value)return
 mapError.value=''
 if(value==='osm'){provider.value='osm';rememberMap('osm');setTiles();return}
 switchingMap.value=true
 try{
  const response=await fetch('/api/maps/config',{signal:AbortSignal.timeout(12000)})
  const config=await readApiJson(response,'Mapy HERE są chwilowo niedostępne.')
  if(disposed)return
  if(config.provider!=='here')throw Error('Mapy HERE nie są skonfigurowane.')
  copyrights=config.copyrights||{};provider.value='here';rememberMap('here');setTiles()
 }catch(error){if(!disposed){mapError.value=error.message+' Dostępna jest mapa OpenStreetMap.';provider.value='osm';setTiles()}}
 finally{if(!disposed)switchingMap.value=false}
}
function drawPlace(p){
 const index=props.selected.indexOf(p.id)
 const label=document.createElement('span');label.textContent=p.name
 const marker=L.marker([p.lat,p.lng],{draggable:props.draggablePoints&&index>=0,zIndexOffset:index>=0?1000:0,icon:L.divIcon({className:'',html:`<span class="map-pin ${p.details?.kind==='custom'?'custom-point':''} ${index>=0?'chosen':''}">${index>=0?index+1:'•'}</span>`,iconSize:[32,32],iconAnchor:[16,32]})}).addTo(markerLayer).bindTooltip(label).on('click',()=>emit('select',p.id))
 marker.on('dragend',()=>{const {lat,lng}=marker.getLatLng();emit('move-point',{id:p.id,lat:+lat.toFixed(6),lng:+lng.toFixed(6)})})
}
function drawMarkers(){
 if(!map||!markerLayer||!clusterIndex)return
 markerLayer.clearLayers()
 const bounds=map.getBounds().pad(.1)
 const lookup=new Map(props.places.map(p=>[p.id,p]))
 const clusters=clusterIndex.getClusters([bounds.getWest(),bounds.getSouth(),bounds.getEast(),bounds.getNorth()],Math.floor(map.getZoom()))
 for(const item of clusters){
  if(!item.properties.cluster){const place=lookup.get(item.properties.placeId);if(place)drawPlace(place);continue}
  const [lng,lat]=item.geometry.coordinates,propsCluster=item.properties
  const marker=L.marker([lat,lng],{title:`${propsCluster.point_count} miejsc — kliknij, aby rozwinąć`,icon:L.divIcon({className:'',html:`<span class="map-cluster">${propsCluster.point_count_abbreviated}</span>`,iconSize:[42,42],iconAnchor:[21,21]})}).addTo(markerLayer)
  marker.on('click',()=>{
   const zoom=clusterIndex.getClusterExpansionZoom(propsCluster.cluster_id)
   if(zoom<=16){map.setView([lat,lng],zoom);return}
   const list=document.createElement('div');list.className='map-cluster-list'
   for(const leaf of clusterIndex.getLeaves(propsCluster.cluster_id,Infinity)){
    const place=lookup.get(leaf.properties.placeId);if(!place)continue
    const button=document.createElement('button');button.type='button';button.textContent=place.name;button.addEventListener('click',event=>{event.stopPropagation();emit('select',place.id)});list.append(button)
   }
   marker.bindPopup(list,{autoPan:false}).openPopup()
  })
 }
 props.places.filter(p=>validMapPoint(p)&&(props.selected.includes(p.id)||p.details?.kind==='custom')).forEach(drawPlace)
}
const mapElement=ref(null)
function draw() {
 if (!map) return
 const catalogPoints=props.places.filter(p=>p.details?.kind!=='custom')
 const viewportKey=JSON.stringify([catalogPoints.map(p=>[p.id,p.lat,p.lng]).sort((a,b)=>a[0]-b[0]),props.searchLocation?.lat,props.searchLocation?.lng,props.distanceArea])
 const refit=viewportKey!==lastViewportKey||props.geometry!==lastGeometry
 lastViewportKey=viewportKey;lastGeometry=props.geometry
 layer.clearLayers()
 const nextClusterKey=JSON.stringify([props.places.map(p=>[p.id,p.lat,p.lng,p.details?.kind,p.name]).sort((a,b)=>a[0]-b[0]),props.selected,props.draggablePoints])
 if(nextClusterKey!==clusterKey){clusterIndex=pointClusters(props.places,props.selected);clusterKey=nextClusterKey;drawMarkers()}
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
 const area=props.distanceArea
 let distanceCircle
 if(validMapPoint(area)&&Number.isFinite(area.radiusKm)&&area.radiusKm>0){
  distanceCircle=L.circle([area.lat,area.lng],{radius:area.radiusKm*1000,color:'#19744f',weight:2,fillOpacity:.06}).addTo(layer)
 }
 const points=props.geometry?.coordinates?.map(p=>[p[1],p[0]])||[]
 const routeLine=points.length>1?L.polyline(points,{color:'#1685d2',weight:5,dashArray:props.geometryApproximate?'8 8':undefined}).addTo(layer):null
 const focus=props.focusLocation
 const focusChanged=focus!==lastFocus;lastFocus=focus
 if(!distanceCircle&&Number.isFinite(focus?.lat)&&Math.abs(focus.lat)<=90&&Number.isFinite(focus?.lng)&&Math.abs(focus.lng)<=180){
  if(refit||focusChanged)map.setView([focus.lat,focus.lng],Number.isFinite(focus.zoom)?Math.max(8,Math.min(16,focus.zoom)):14)
  return
 }
 if(routeLine){if(refit)map.fitBounds(routeLine.getBounds(),{padding:[45,45],maxZoom:14})}
 else if(distanceCircle){if(refit)map.fitBounds(distanceCircle.getBounds(),{padding:[30,30],maxZoom:14})}
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
  if(!props.allowCustomPoints||event.originalEvent?.target?.closest?.('.leaflet-marker-icon,.leaflet-control,.leaflet-popup'))return
  const {lat,lng}=event.latlng||{}
  if(Number.isFinite(lat)&&Number.isFinite(lng)&&lat>=-90&&lat<=90&&lng>=-180&&lng<=180)emit('create-point',{lat:+lat.toFixed(6),lng:+lng.toFixed(6)})
 })
 setTiles();map.on('moveend zoomend',()=>{updateAttribution();drawMarkers()})
 layer=L.layerGroup().addTo(map);markerLayer=L.layerGroup().addTo(map);draw()
 if(typeof ResizeObserver!=='undefined'){
  resizeObserver=new ResizeObserver(()=>{if(!disposed){map.invalidateSize({pan:false});lastViewportKey=undefined;draw()}})
  resizeObserver.observe(mapElement.value)
 }
 if(!props.trackOnly&&preferredMap()==='here')await selectProvider('here')
})
watch(mapStyle,setTiles)
watch(()=>props.trackOnly,setTiles)
watch(()=>[props.selected,props.places,props.geometry,props.userLocation,props.searchLocation,props.draggablePoints,props.focusLocation,props.distanceArea],draw,{deep:true})
onBeforeUnmount(()=>{disposed=true;resizeObserver?.disconnect();map?.remove();tiles?.off()})
</script>
<template><div class="travel-map" :class="{'track-only':trackOnly}"><div ref="mapElement" class="travel-map-canvas" aria-label="Mapa miejsc i tras w Polsce"></div><div v-if="!minimal&&!trackOnly" class="map-provider-switch" role="group" aria-label="Dostawca mapy"><button :aria-pressed="provider==='osm'" :disabled="switchingMap" @click="selectProvider('osm')">OpenStreetMap</button><button :aria-pressed="provider==='here'" :disabled="switchingMap" @click="selectProvider('here')">{{switchingMap?'HERE…':'HERE'}}</button></div><div v-if="provider==='here'&&!minimal&&!trackOnly" class="map-style-switch" role="group" aria-label="Rodzaj mapy HERE"><button v-for="style in [{id:'map',label:'Mapa'},{id:'satellite',label:'Satelita'},{id:'terrain',label:'Teren'}]" :key="style.id" :aria-pressed="mapStyle===style.id" @click="mapStyle=style.id">{{style.label}}</button></div><p v-if="mapError" class="map-provider-error" role="status">{{mapError}}</p></div></template>
<style scoped>
.map-provider-switch{position:absolute;top:14px;right:14px;z-index:500;display:flex;gap:3px;padding:4px;background:#fff;border-radius:22px;box-shadow:0 2px 9px #173d2920}.map-provider-switch button{font:600 11px/1.4 system-ui;padding:8px 12px;border:0;border-radius:18px;background:transparent;color:#294b36;cursor:pointer}.map-provider-switch button[aria-pressed=true]{background:#18774f;color:white}.map-provider-switch button:disabled{opacity:.6;cursor:wait}.map-provider-switch button:focus-visible{outline:2px solid #19744f;outline-offset:2px}
.travel-map{position:relative;width:100%;height:100%;min-height:inherit}.map-style-switch{position:absolute;top:61px;right:14px;z-index:500;display:flex;gap:3px;padding:4px;background:#fff;border-radius:22px;box-shadow:0 2px 9px #173d2920}.map-style-switch button{font:600 11px/1.4 system-ui;padding:8px 12px;border:0;border-radius:18px;background:transparent;color:#294b36;cursor:pointer}.map-style-switch button[aria-pressed=true]{background:#18774f;color:white}.map-provider-error{position:absolute;bottom:36px;left:12px;right:12px;z-index:500;background:#fff8e9ed;padding:9px 12px;border-radius:7px;font:11px/1.5 system-ui;color:#775024;pointer-events:none}
</style>
<style>
.map-cluster{display:grid;place-items:center;width:42px;height:42px;border-radius:50%;border:5px solid #c9e6b5;background:#19744f;color:#fff;font:700 13px/1 system-ui;box-shadow:0 2px 9px #173d2938}.map-cluster-list{max-height:240px;overflow:auto;display:grid;gap:5px;min-width:180px}.map-cluster-list button{text-align:left;white-space:normal;border:1px solid #dce7d3;border-radius:6px;padding:9px;color:#1e5436;background:#f5f9ef;font:12px/1.6 system-ui;cursor:pointer}.map-cluster-list button:focus-visible{outline:2px solid #19744f;outline-offset:1px}
</style>
<style scoped>
@media(max-width:600px){.map-provider-switch{top:58px;right:12px}.map-style-switch{top:105px;right:12px}}
</style>

<style scoped>.travel-map.track-only .travel-map-canvas{background:#f6f8f2}</style>
