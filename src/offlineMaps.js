import {readApiJson} from './apiResponse.js'

const cacheName='perly-offline-map-v1',entry='/offline-map/selected-area'
export const offlineMapChanged='perly:offline-map-changed'
export function mapArea(bounds){
 const [west,south,east,north]=bounds
 if(!bounds.every(Number.isFinite)||west>=east||south>=north||west< -180||east>180||south< -85||north>85)throw Error('Nieprawidłowy obszar mapy.')
 const width=(east-west)*111.32*Math.cos((south+north)*Math.PI/360),height=(north-south)*111.32
 return {width,height,km2:width*height}
}
export function validateMapArea(bounds){
 const size=mapArea(bounds)
 if(size.km2>25||Math.max(size.width,size.height)>10)throw Error('Przybliż mapę. Pobierz fragment do 25 km², o szerokości i wysokości do 10 km.')
 return size
}
export function validOfflineMap(value){return value?.version===1&&Array.isArray(value.bounds)&&value.bounds.length===4&&value.map?.type==='FeatureCollection'&&Array.isArray(value.map.features)&&value.map.features.length>0}
export async function readOfflineMap(){
 if(!globalThis.caches)return null
 try{const saved=await(await caches.open(cacheName)).match(entry);if(!saved)return null;const value=await saved.json();return validOfflineMap(value)?value:null}catch{return null}
}
export async function downloadOfflineMap(bounds,{places=[],signal}={}){
 validateMapArea(bounds)
 if(!globalThis.caches)throw Error('Zapisywanie mapy wymaga HTTPS i przeglądarki obsługującej pracę offline.')
 const response=await fetch('/api/maps/offline?'+new URLSearchParams(Object.fromEntries(['west','south','east','north'].map((key,i)=>[key,bounds[i]]))),{signal:signal||AbortSignal.timeout(50000)})
 const value=await readApiJson(response,'Nie udało się pobrać fragmentu mapy. Spróbuj ponownie.')
 if(!validOfflineMap(value))throw Error('Otrzymano nieprawidłowy fragment mapy.')
 const [west,south,east,north]=bounds
 // Only the places inside the chosen fragment are copied to this device.
 const localPlaces=places.filter(p=>p.lat>=south&&p.lat<=north&&p.lng>=west&&p.lng<=east).map(p=>({...p,liked:false}))
 const saved={...value,places:localPlaces,savedAt:Date.now()}
 const body=JSON.stringify(saved)
 if(new TextEncoder().encode(body).length>12_000_000)throw Error('Fragment mapy jest zbyt duży. Wybierz mniejszy obszar.')
 try{await(await caches.open(cacheName)).put(entry,new Response(body,{headers:{'Content-Type':'application/json'}}))}
 catch{throw Error('Brakuje miejsca na zapis mapy w telefonie. Zwolnij pamięć i spróbuj ponownie.')}
 window.dispatchEvent(new Event(offlineMapChanged))
 // The browser may deny persistent storage; a successful download still works.
 try{await navigator.storage?.persist?.()}catch{}
 return saved
}
export async function removeOfflineMap(){
 if(globalThis.caches)await(await caches.open(cacheName)).delete(entry)
 window.dispatchEvent(new Event(offlineMapChanged))
}
export function offlineFeatureStyle(feature){
 const p=feature.properties||{},polygon=['Polygon','MultiPolygon'].includes(feature.geometry?.type)
 if(polygon){
  const water=p.natural==='water'||p.landuse==='reservoir'||p.landuse==='basin'
  const forest=p.natural==='wood'||p.landuse==='forest'
  const green=forest||['grass','meadow','recreation_ground','village_green'].includes(p.landuse)||['scrub','wetland','grassland'].includes(p.natural)||p.leisure==='park'
  return {color:water?'#80b7ca':p.building?'#b4a79a':green?'#a6c79c':'#d6cfb8',fillColor:water?'#a7d0df':p.building?'#d5c8ba':forest?'#bed6ac':green?'#d7e5bd':'#ede7d3',weight:p.building?.6:.5,fillOpacity:1}
 }
 if(p.waterway)return {color:'#8bbfd4',weight:p.waterway==='river'?3:1.5}
 if(p.railway)return {color:'#8d8990',weight:2,dashArray:'5 4'}
 const path=['path','footway','cycleway','track','steps','bridleway'].includes(p.highway)
 return {color:path?'#aa8b66':['motorway','trunk','primary'].includes(p.highway)?'#d7a86f':'#fff',weight:path?1.8:4,dashArray:path?'4 4':undefined,opacity:1}
}
