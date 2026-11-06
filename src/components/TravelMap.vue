<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as L from 'leaflet/dist/leaflet-src.esm.js'
import {readApiJson} from '../apiResponse.js'
import {preferredMap,rememberMap,osmTileUrl,preferredOsmTone,rememberOsmTone} from '../mapPreferences.js'
import {pointClusters,validMapPoint} from '../mapClusters.js'
import {routeDirectionArrows} from '../navigationDirections.js'
import {readOfflineMap,downloadOfflineMap,removeOfflineMap,offlineMapChanged,offlineFeatureStyle,validateMapArea} from '../offlineMaps.js'
import Download from 'lucide-vue-next/dist/esm/icons/download.js'
import WifiOff from 'lucide-vue-next/dist/esm/icons/wifi-off.js'
import Trash2 from 'lucide-vue-next/dist/esm/icons/trash-2.js'
const props = defineProps({ places: Array, roadsOnly:Boolean, hideOfflineControls:Boolean, nearbyPeople:{type:Array,default:()=>[]}, endpointPlaces:{type:Array,default:()=>[]}, travelledTrack:{type:Array,default:()=>[]}, trackOnly:Boolean, minimal:Boolean, directionalPosition:Boolean, routeDirections:Boolean, focusLocation: Object, distanceArea: Object, selected: {type:Array,default:()=>[]}, geometry: Object, geometryApproximate: Boolean, draggablePoints: Boolean, userLocation: Object, searchLocation: Object, fitPlaces: Boolean, allowCustomPoints: Boolean })
const emit = defineEmits(['select','create-point','move-point'])
let map, layer, markerLayer, userLayer, arrowLayer, userMarker, accuracyCircle, tiles, resizeObserver, disposed=false, copyrights={},lastViewportKey,lastGeometry,lastFocus,clusterIndex,clusterKey,hereErrors=0
let offlineLayer,travelledLayer,peopleLayer,downloadController,travelledDrawn=[]
const offlinePack=ref(null),offlineView=ref(false),offlineBusy=ref(false),offlineNotice=ref('')
const noNetwork=ref(navigator.onLine===false)
const provider=ref('osm'), mapStyle=ref('terrain'), mapError=ref(''),switchingMap=ref(false)
const osmTone=ref(preferredOsmTone())
function updateOsmTone(){osmTone.value=preferredOsmTone()}
const osmAttribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
function hereAttribution(){
 const bounds=map.getBounds(),zoom=map.getZoom()
 const labels=(copyrights[props.roadsOnly?'map':mapStyle.value]||[]).filter(n=>zoom>=(n.minLevel??0)&&zoom<=(n.maxLevel??20)&&(!n.boxes?.length||n.boxes.some(b=>bounds.intersects([[b[0],b[1]],[b[2],b[3]]])))).map(n=>String(n.label||''))
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
 if(offlineLayer){map.removeLayer(offlineLayer);offlineLayer=null}
 map.setMaxBounds?.(null);map.setMinZoom?.(0)
 if(props.trackOnly)return
 if(offlineView.value&&offlinePack.value){
  const bounds=offlinePack.value.bounds
  const leafletBounds=L.latLngBounds([[bounds[1],bounds[0]],[bounds[3],bounds[2]]])
  map.setMaxZoom(19);map.setMaxBounds?.(leafletBounds.pad(.05))
  map.setMinZoom?.(Math.max(1,map.getBoundsZoom(leafletBounds)-1))
  offlineLayer=L.layerGroup().addTo(map)
  L.rectangle(leafletBounds,{color:'#a7b79d',weight:1,fillColor:'#f1eddd',fillOpacity:1,interactive:false}).addTo(offlineLayer)
  L.geoJSON(offlinePack.value.map,{
   filter:feature=>!props.roadsOnly||!!feature.properties?.highway,
   style:offlineFeatureStyle,
   pointToLayer(feature,latlng){
    const label=document.createElement('span');label.className='offline-place-label';label.textContent=feature.properties?.name||({drinking_water:'Woda pitna',shelter:'Wiata',toilets:'Toaleta',parking:'Parking'}[feature.properties?.amenity]||'')
    return L.marker(latlng,{interactive:false,keyboard:false,icon:L.divIcon({className:'offline-place-icon',html:label,iconSize:[100,20],iconAnchor:[50,10]})})
   },
   onEachFeature(feature,featureLayer){if(feature.properties?.name&&feature.geometry.type!=='Point'){const label=document.createElement('span');label.textContent=feature.properties.name;featureLayer.bindTooltip(label)}}
  }).addTo(offlineLayer)
  attribution=osmAttribution;map.attributionControl.addAttribution(attribution)
  return
 }
 const here=provider.value==='here'
 hereErrors=0
 map.setMaxZoom(here?20:19)
 tiles=L.tileLayer(here?`/api/maps/tiles/${props.roadsOnly?'map':mapStyle.value}/{z}/{x}/{y}${props.roadsOnly?'?roads_only=1':''}`:osmTileUrl,{attribution:here?'':osmAttribution,maxZoom:here?20:19,updateWhenIdle:true,keepBuffer:1})
 if(here)tiles.on('tileerror',()=>{if(disposed||++hereErrors<3)return;mapError.value='Nie udało się wczytać map HERE. Dostępna jest mapa OpenStreetMap.';provider.value='osm';setTiles()})
 else tiles.on('tileerror',()=>{if(!disposed&&++hereErrors>=3)mapError.value='Mapa OpenStreetMap jest chwilowo niedostępna. Spróbuj ponownie lub wybierz HERE.'})
 tiles.addTo(map);updateAttribution()
}
async function restoreOfflineMap(){
 const saved=await readOfflineMap()
 if(disposed)return
 offlinePack.value=saved
 if(saved&&noNetwork.value){offlineView.value=true;setTiles();map.fitBounds([[saved.bounds[1],saved.bounds[0]],[saved.bounds[3],saved.bounds[2]]],{padding:[18,18],animate:false})}
 else if(!saved&&offlineView.value){offlineView.value=false;setTiles()}
}
function networkChanged(){
 noNetwork.value=navigator.onLine===false
 if(noNetwork.value&&offlinePack.value){offlineView.value=true;setTiles()}
}
function toggleOfflineMap(){
 offlineView.value=!offlineView.value;setTiles()
 if(offlineView.value){const b=offlinePack.value.bounds;map.fitBounds([[b[1],b[0]],[b[3],b[2]]],{padding:[18,18],animate:false})}
}
async function saveVisibleMap(){
 if(offlineBusy.value)return
 offlineNotice.value=''
 const b=map.getBounds(),bounds=[b.getWest(),b.getSouth(),b.getEast(),b.getNorth()]
 try{
  validateMapArea(bounds)
  offlineBusy.value=true;downloadController=new AbortController()
  const timeout=setTimeout(()=>downloadController.abort(),50000)
  let saved
  try{saved=await downloadOfflineMap(bounds,{places:[...props.places,...props.endpointPlaces],signal:downloadController.signal})}finally{clearTimeout(timeout)}
  if(disposed)return
  offlinePack.value=saved;offlineNotice.value='Fragment zapisany w tym urządzeniu. Mapa offline ma uproszczony wygląd.'
 }catch(error){if(!disposed)offlineNotice.value=error.name==='AbortError'?'Pobieranie trwało zbyt długo. Spróbuj ponownie.':error.message}
 finally{offlineBusy.value=false}
}
async function deleteSavedMap(){try{await removeOfflineMap();if(!disposed){offlinePack.value=null;offlineView.value=false;setTiles();offlineNotice.value='Usunięto zapisany fragment.'}}catch{offlineNotice.value='Nie udało się usunąć fragmentu. Spróbuj ponownie.'}}
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
  copyrights=config.copyrights||{};provider.value='here';if(!props.roadsOnly)rememberMap('here');setTiles()
 }catch(error){if(!disposed){mapError.value=error.message+' Dostępna jest mapa OpenStreetMap.';provider.value='osm';setTiles()}}
 finally{if(!disposed)switchingMap.value=false}
}
function isEndpoint(p){return props.selected.length>1&&(p.id===props.selected[0]||p.id===props.selected.at(-1))}
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
 props.places.filter(p=>validMapPoint(p)&&!isEndpoint(p)&&(props.selected.includes(p.id)||p.details?.kind==='custom')).forEach(drawPlace)
}
function drawFlag(point,kind,place){
 const title=kind==='start'?'Start':'Meta'
 const html='<span class="route-flag route-flag-'+kind+'"><span>'+title+'</span></span>'
 const marker=L.marker([point.lat,point.lng],{title:title+(place?.name?': '+place.name:''),draggable:!!(props.draggablePoints&&place&&props.selected.includes(place.id)),zIndexOffset:1600,icon:L.divIcon({className:'',html,iconSize:[58,42],iconAnchor:[8,40]})}).addTo(layer)
 if(place&&place.details?.kind!=='custom'&&props.selected.includes(place.id))marker.on('click',()=>emit('select',place.id))
 else{
  const content=document.createElement('div'),heading=document.createElement('strong'),description=document.createElement('p')
  heading.textContent=title+(point.name?': '+point.name:'')
  description.textContent=kind==='start'?'Początek wycieczki. Od tego punktu wyznaczamy trasę.':'Koniec wyznaczonej trasy.'
  content.append(heading,description);marker.bindPopup(content,{maxWidth:260})
 }
 if(place)marker.on('dragend',()=>{const {lat,lng}=marker.getLatLng();emit('move-point',{id:place.id,lat:+lat.toFixed(6),lng:+lng.toFixed(6)})})
}
const mapElement=ref(null)
function drawRouteDirections(){
 if(!map||!arrowLayer)return
 arrowLayer.clearLayers()
 if(!props.routeDirections)return
 const size=map.getSize()
 const arrows=routeDirectionArrows(props.geometry?.coordinates,coordinate=>map.latLngToContainerPoint([coordinate[1],coordinate[0]]),{width:size.x,height:size.y})
 for(const point of arrows){
  L.marker(map.containerPointToLatLng([point.x,point.y]),{interactive:false,keyboard:false,zIndexOffset:500,icon:L.divIcon({className:'route-direction-icon',html:`<svg class="route-direction-arrow" style="transform:rotate(${point.heading}deg)" width="13" height="15" viewBox="0 0 13 15" aria-hidden="true"><path d="M6.5 1 L12 13 L6.5 10 L1 13 Z" fill="white" stroke="#1685d2" stroke-width="1.5" stroke-linejoin="round"/></svg>`,iconSize:[13,15],iconAnchor:[6.5,7.5]})}).addTo(arrowLayer)
 }
}
function drawTravelledTrack(){
 if(!map||!travelledLayer)return
 const points=props.travelledTrack
 let start=travelledDrawn.length
 if(points.length<start||start&&(points[0]!==travelledDrawn[0]||points[start-1]!==travelledDrawn[start-1])){travelledLayer.clearLayers();start=0}
 for(const point of points.slice(start))L.circleMarker([point.lat,point.lng],{radius:2.5,color:'#fff',weight:1,fillColor:'#176944',fillOpacity:1,interactive:false,pane:'markerPane'}).addTo(travelledLayer)
 travelledDrawn=points
}
function drawNearbyPeople(){
 if(!map||!peopleLayer)return
 peopleLayer.clearLayers()
 for(const person of props.nearbyPeople){
  if(!validMapPoint(person)||Date.parse(person.expires_at)<=Date.now()||!Number.isFinite(Date.parse(person.expires_at)))continue
  const label=document.createElement('span');label.textContent=String(person.name||'Uczestnik').slice(0,80)
  const popup=document.createElement('div'),name=document.createElement('strong'),info=document.createElement('p')
  name.textContent=label.textContent
  info.textContent=(Number.isFinite(person.distance_m)?'Od Ciebie: '+(person.distance_m<1000?Math.round(person.distance_m)+' m':(person.distance_m/1000).toFixed(1)+' km')+'. ':'')+'Aktualizacja: '+new Date(person.updated_at).toLocaleTimeString('pl-PL',{hour:'2-digit',minute:'2-digit'})
  popup.append(name,info)
  L.marker([person.lat,person.lng],{zIndexOffset:2000,icon:L.divIcon({className:'nearby-person-icon',html:'<span class="nearby-person-pin"><svg width="19" height="19" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="7" r="3" fill="currentColor"/><path d="M5 21v-3a7 7 0 0 1 14 0v3" fill="currentColor"/></svg></span>',iconSize:[32,32],iconAnchor:[16,16]})}).addTo(peopleLayer).bindTooltip(label).bindPopup(popup)
 }
}
function drawPosition(){
 if(!map||!userLayer)return
 const point=props.userLocation
 if(validMapPoint(point)){
  const latlng=[point.lat,point.lng]
  if(userMarker)userMarker.setLatLng(latlng)
  else if(props.directionalPosition)userMarker=L.marker(latlng,{interactive:false,keyboard:false,zIndexOffset:2200,icon:L.divIcon({className:'gps-direction-icon',html:'<svg class="gps-direction-pointer" width="32" height="34" viewBox="0 0 32 34" role="img" aria-label="Pozycja GPS"><path d="M16 2 L29 30 L16 24 L3 30 Z" fill="#1876d2" stroke="white" stroke-width="2.5" stroke-linejoin="round"/></svg>',iconSize:[32,34],iconAnchor:[16,17]})}).addTo(userLayer)
  else userMarker=L.circleMarker(latlng,{radius:8,color:'#fff',weight:3,fillColor:'#1876d2',fillOpacity:1}).addTo(userLayer).bindTooltip('Tu jesteś')
  if(props.directionalPosition){
   const pointer=userMarker.getElement()?.querySelector('.gps-direction-pointer')
   if(pointer){
    const known=Number.isFinite(point.heading)
    pointer.style.transform=`rotate(${known?point.heading:0}deg)`
    pointer.classList.toggle('direction-unknown',!known)
    pointer.setAttribute('aria-label',known?'Pozycja GPS i kierunek ruchu':'Pozycja GPS — kierunek zostanie ustalony podczas ruchu')
   }
  }
  if(!props.minimal&&Number.isFinite(point.accuracy)&&point.accuracy>0){
   if(accuracyCircle)accuracyCircle.setLatLng(latlng).setRadius(point.accuracy)
   else accuracyCircle=L.circle(latlng,{radius:point.accuracy,color:'#1876d2',weight:1,fillOpacity:.08}).addTo(userLayer)
   userMarker.bringToFront?.()
  }else if(accuracyCircle){userLayer.removeLayer(accuracyCircle);accuracyCircle=null}
 }else{userLayer.clearLayers();userMarker=null;accuracyCircle=null}
 const focus=props.focusLocation
 if(!props.distanceArea&&validMapPoint(focus)&&focus!==lastFocus){
  lastFocus=focus;map.setView([focus.lat,focus.lng],Number.isFinite(focus.zoom)?Math.max(8,Math.min(16,focus.zoom)):14,{animate:false})
 }
}
function draw() {
 if (!map) return
 const catalogPoints=props.places.filter(p=>p.details?.kind!=='custom')
 const viewportKey=JSON.stringify([catalogPoints.map(p=>props.draggablePoints&&props.selected.includes(p.id)?[p.id]:[p.id,p.lat,p.lng]).sort((a,b)=>a[0]-b[0]),props.searchLocation?.lat,props.searchLocation?.lng,props.distanceArea])
 const refit=viewportKey!==lastViewportKey||!!props.geometry&&props.geometry!==lastGeometry
 lastViewportKey=viewportKey;lastGeometry=props.geometry
 layer.clearLayers()
 const nextClusterKey=JSON.stringify([props.places.map(p=>[p.id,p.lat,p.lng,p.details?.kind,p.name]).sort((a,b)=>a[0]-b[0]),props.selected,props.draggablePoints])
 if(nextClusterKey!==clusterKey){clusterIndex=pointClusters(props.places,props.selected);clusterKey=nextClusterKey;drawMarkers()}
 const area=props.distanceArea
 let distanceCircle
 if(validMapPoint(area)&&Number.isFinite(area.radiusKm)&&area.radiusKm>0){
  distanceCircle=L.circle([area.lat,area.lng],{radius:area.radiusKm*1000,color:'#19744f',weight:2,fillOpacity:.06}).addTo(layer)
 }
 const points=props.geometry?.coordinates?.map(p=>[p[1],p[0]])||[]
 const routeLine=points.length>1?L.polyline(points,{color:'#1685d2',weight:5,dashArray:props.geometryApproximate?'8 8':undefined}).addTo(layer):null
 const stops=[...props.endpointPlaces,...props.places]
 const first=props.selected.length>1?stops.find(p=>p.id===props.selected[0]):null
 const last=props.selected.length>1?stops.find(p=>p.id===props.selected.at(-1)):null
 const firstPoint=first||(points.length>1?{lat:points[0][0],lng:points[0][1]}:null)
 const lastPoint=last||(points.length>1?{lat:points.at(-1)[0],lng:points.at(-1)[1]}:null)
 if(validMapPoint(firstPoint))drawFlag(firstPoint,'start',first)
 else if(validMapPoint(props.searchLocation))drawFlag(props.searchLocation,'start',null)
 if(validMapPoint(lastPoint))drawFlag(lastPoint,'end',last)
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
 window.addEventListener('perly:osm-tone-changed',updateOsmTone)
 window.addEventListener(offlineMapChanged,restoreOfflineMap)
 window.addEventListener('online',networkChanged);window.addEventListener('offline',networkChanged)
 map=L.map(mapElement.value,{scrollWheelZoom:false,doubleClickZoom:!props.allowCustomPoints}).setView([52.15,15.16],8)
 map.on('dblclick',event=>{
  if(!props.allowCustomPoints||event.originalEvent?.target?.closest?.('.leaflet-marker-icon,.leaflet-control,.leaflet-popup'))return
  const {lat,lng}=event.latlng||{}
  if(Number.isFinite(lat)&&Number.isFinite(lng)&&lat>=-90&&lat<=90&&lng>=-180&&lng<=180)emit('create-point',{lat:+lat.toFixed(6),lng:+lng.toFixed(6)})
 })
 setTiles();map.on('moveend zoomend',()=>{updateAttribution();drawMarkers();drawRouteDirections()})
 layer=L.layerGroup().addTo(map);markerLayer=L.layerGroup().addTo(map);userLayer=L.layerGroup().addTo(map);arrowLayer=L.layerGroup().addTo(map);travelledLayer=L.layerGroup().addTo(map);peopleLayer=L.layerGroup().addTo(map);draw();drawPosition();drawRouteDirections();drawTravelledTrack();drawNearbyPeople()
 if(typeof ResizeObserver!=='undefined'){
  resizeObserver=new ResizeObserver(()=>{if(!disposed){map.invalidateSize({pan:false});drawRouteDirections()}})
  resizeObserver.observe(mapElement.value)
 }
 await restoreOfflineMap()
 if(!disposed&&!offlineView.value&&!props.trackOnly&&(props.roadsOnly||preferredMap()==='here'))await selectProvider('here')
})
watch(mapStyle,setTiles)
watch(()=>props.roadsOnly,value=>{if(value&&provider.value!=='here'&&!offlineView.value)selectProvider('here');else setTiles()})
watch(()=>props.trackOnly,setTiles)
watch(()=>[props.selected,props.places,props.geometry,props.searchLocation,props.draggablePoints,props.distanceArea,props.endpointPlaces],draw,{deep:true})
watch(()=>[props.userLocation,props.focusLocation],drawPosition,{deep:true})
watch(()=>[props.geometry,props.routeDirections],drawRouteDirections,{deep:true})
watch(()=>props.travelledTrack,drawTravelledTrack,{deep:true})
watch(()=>props.nearbyPeople,drawNearbyPeople,{deep:true})
onBeforeUnmount(()=>{disposed=true;downloadController?.abort();window.removeEventListener('perly:osm-tone-changed',updateOsmTone);window.removeEventListener(offlineMapChanged,restoreOfflineMap);window.removeEventListener('online',networkChanged);window.removeEventListener('offline',networkChanged);resizeObserver?.disconnect();map?.remove();tiles?.off()})
defineExpose({saveVisibleMap,toggleOfflineMap,deleteSavedMap,offlinePack,offlineView,offlineBusy,offlineNotice,noNetwork})
</script>
<template>
 <div class="travel-map" :class="{'track-only':trackOnly,'osm-light':!offlineView&&provider==='osm'&&osmTone==='light','offline-view':offlineView,'minimal-map':minimal}">
  <div ref="mapElement" class="travel-map-canvas" aria-label="Mapa miejsc i tras w Polsce"></div>
  <div v-if="!minimal&&!trackOnly&&!offlineView" class="map-provider-switch" role="group" aria-label="Dostawca mapy"><button :aria-pressed="provider==='osm'" :disabled="switchingMap" @click="selectProvider('osm')">OpenStreetMap</button><button :aria-pressed="provider==='here'" :disabled="switchingMap" @click="selectProvider('here')">{{switchingMap?'HERE…':'HERE'}}</button></div>
  <div v-if="provider==='osm'&&!minimal&&!trackOnly&&!offlineView" class="osm-style-switch" role="group" aria-label="Wygląd mapy OpenStreetMap"><button :aria-pressed="osmTone==='light'" @click="rememberOsmTone('light')">Jasna</button><button :aria-pressed="osmTone==='standard'" @click="rememberOsmTone('standard')">Standardowa</button></div>
  <div v-if="provider==='here'&&!minimal&&!trackOnly&&!offlineView" class="map-style-switch" role="group" aria-label="Rodzaj mapy HERE"><button v-for="style in [{id:'map',label:'Mapa'},{id:'satellite',label:'Satelita'},{id:'terrain',label:'Teren'}]" :key="style.id" :aria-pressed="mapStyle===style.id" @click="mapStyle=style.id">{{style.label}}</button></div>
  <div v-if="!trackOnly&&!hideOfflineControls" class="offline-map-controls" @dblclick.stop @click.stop>
   <button class="offline-map-download" :disabled="offlineBusy||noNetwork" :aria-busy="offlineBusy" @click="saveVisibleMap"><Download :size="16"/>{{offlineBusy?'Pobieram…':'Pobierz fragment mapy'}}</button>
   <small v-if="!offlinePack">Widoczny obszar · do 25 km²</small>
   <div v-if="offlinePack" class="offline-map-saved"><button :aria-pressed="offlineView" @click="toggleOfflineMap"><WifiOff :size="15"/>{{offlineView?'Wróć do mapy online':'Pokaż mapę offline'}}</button><button :disabled="offlineBusy" aria-label="Usuń zapisany fragment mapy" @click="deleteSavedMap"><Trash2 :size="15"/></button></div>
   <small v-if="offlinePack&&!offlineView">Nowe pobranie zastąpi zapisany fragment.</small>
   <small v-if="offlineView">Zapisany fragment · {{new Date(offlinePack.savedAt).toLocaleDateString('pl')}}<br>Poza fragmentem mapa jest niedostępna.</small>
   <small v-if="offlineNotice" class="offline-map-notice" role="status">{{offlineNotice}}</small>
  </div>
  <p v-if="mapError&&!offlineView" class="map-provider-error" role="status">{{mapError}}</p>
 </div>
</template>
<style scoped>
.map-provider-switch{position:absolute;top:14px;right:14px;z-index:500;display:flex;gap:3px;padding:4px;background:#fff;border-radius:22px;box-shadow:0 2px 9px #173d2920}.map-provider-switch button{font:600 11px/1.4 system-ui;padding:8px 12px;border:0;border-radius:18px;background:transparent;color:#294b36;cursor:pointer}.map-provider-switch button[aria-pressed=true]{background:#18774f;color:white}.map-provider-switch button:disabled{opacity:.6;cursor:wait}.map-provider-switch button:focus-visible{outline:2px solid #19744f;outline-offset:2px}
.travel-map{position:relative;width:100%;height:100%;min-height:inherit}.map-style-switch{position:absolute;top:61px;right:14px;z-index:500;display:flex;gap:3px;padding:4px;background:#fff;border-radius:22px;box-shadow:0 2px 9px #173d2920}.map-style-switch button{font:600 11px/1.4 system-ui;padding:8px 12px;border:0;border-radius:18px;background:transparent;color:#294b36;cursor:pointer}.map-style-switch button[aria-pressed=true]{background:#18774f;color:white}.map-provider-error{position:absolute;bottom:36px;left:12px;right:12px;z-index:500;background:#fff8e9ed;padding:9px 12px;border-radius:7px;font:11px/1.5 system-ui;color:#775024;pointer-events:none}
</style>
<style>
.nearby-person-icon{background:transparent;border:0}.nearby-person-pin{display:grid;place-items:center;width:32px;height:32px;border:3px solid white;border-radius:50%;background:#805ab3;color:#fff;box-shadow:0 2px 9px #30244966}.nearby-person-pin svg{display:block}
</style>
<style scoped>
.offline-map-controls{position:absolute;z-index:550;left:12px;bottom:29px;max-width:min(250px,calc(100% - 24px));padding:6px;border-radius:12px;background:#ffffffed;box-shadow:0 2px 12px #173d2929;color:#24563b}.offline-map-controls button{display:flex;align-items:center;justify-content:center;gap:7px;min-height:40px;border:1px solid #d3dfc8;border-radius:8px;background:#fff;padding:8px 10px;font:600 11px/1.4 system-ui;color:#24563b}.offline-map-controls button:disabled{opacity:.55}.offline-map-controls button:focus-visible{outline:2px solid #19744f;outline-offset:2px}.offline-map-controls small{display:block;padding:4px 3px;font:10px/1.5 system-ui;color:#607753}.offline-map-saved{display:flex;gap:4px;margin-top:4px}.offline-map-saved button:first-child{flex:1}.offline-map-saved button[aria-pressed=true]{background:#e7f1df;border-color:#9bb48c}.offline-map-notice{max-width:230px}.minimal-map .offline-map-controls{top:76px;right:14px;left:auto;bottom:auto;max-width:220px}.offline-view .travel-map-canvas{background:#e5e8df}
</style>
<style>
.offline-place-icon{background:transparent;border:0}.offline-place-label{display:block;text-align:center;font:600 10px/1.4 system-ui;color:#425b3b;text-shadow:0 1px 2px #fff,1px 0 2px #fff,-1px 0 2px #fff;white-space:nowrap}.gps-direction-icon:before,.gps-direction-icon:after{content:'';position:absolute;pointer-events:none;z-index:-1}.gps-direction-icon:before{inset:-5px;border:1.5px solid #1876d2;border-radius:50%;background:#ffffff85}.gps-direction-icon:after{inset:-10px;background:linear-gradient(#1876d2,#1876d2) center/1.5px 100% no-repeat,linear-gradient(#1876d2,#1876d2) center/100% 1.5px no-repeat}
</style>
<style>
.travel-map.osm-light .leaflet-tile-pane{filter:saturate(.4) contrast(.88) brightness(1.08)}
</style>
<style scoped>
.osm-style-switch{position:absolute;top:61px;right:14px;z-index:500;display:flex;gap:3px;padding:4px;background:#fff;border-radius:22px;box-shadow:0 2px 9px #173d2920}.osm-style-switch button{font:600 11px/1.4 system-ui;padding:8px 12px;border:0;border-radius:18px;background:transparent;color:#294b36;cursor:pointer}.osm-style-switch button[aria-pressed=true]{background:#edf3e8;color:#176d4c}.osm-style-switch button:focus-visible{outline:2px solid #19744f;outline-offset:1px}@media(max-width:600px){.osm-style-switch{top:105px;right:12px}}
</style>
<style>
.gps-direction-icon,.route-direction-icon{background:transparent!important;border:0!important;pointer-events:none!important}.gps-direction-pointer{display:block;transform-origin:16px 17px;filter:drop-shadow(0 2px 3px #173d2966)}.gps-direction-pointer.direction-unknown{opacity:.65}.route-direction-arrow{display:block;transform-origin:center;filter:drop-shadow(0 1px 1px #173d2944)}
</style>
<style>
.map-cluster{display:grid;place-items:center;width:42px;height:42px;border-radius:50%;border:5px solid #c9e6b5;background:#19744f;color:#fff;font:700 13px/1 system-ui;box-shadow:0 2px 9px #173d2938}.map-cluster-list{max-height:240px;overflow:auto;display:grid;gap:5px;min-width:180px}.map-cluster-list button{text-align:left;white-space:normal;border:1px solid #dce7d3;border-radius:6px;padding:9px;color:#1e5436;background:#f5f9ef;font:12px/1.6 system-ui;cursor:pointer}.map-cluster-list button:focus-visible{outline:2px solid #19744f;outline-offset:1px}
</style>
<style scoped>
@media(max-width:600px){.map-provider-switch{top:58px;right:12px}.map-style-switch{top:105px;right:12px}}
</style>

<style scoped>.travel-map.track-only .travel-map-canvas{background:#f6f8f2}</style>

<style>.route-flag{position:relative;display:block;width:58px;height:42px;filter:drop-shadow(0 2px 2px #173d2940)}.route-flag:before{content:'';position:absolute;left:7px;top:2px;width:3px;height:38px;background:#365340;border-radius:2px}.route-flag>span{position:absolute;left:10px;top:3px;width:44px;height:25px;display:flex;align-items:center;justify-content:center;padding-right:4px;clip-path:polygon(0 0,100% 0,84% 50%,100% 100%,0 100%);color:#fff;font:700 10px/1 system-ui,sans-serif}.route-flag-start>span{background:#19744f}.route-flag-end>span{background:#ba5846}.route-flag p{margin:6px 0 0}</style>
