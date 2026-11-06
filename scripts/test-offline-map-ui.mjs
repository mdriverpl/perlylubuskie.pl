import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {parse,compileScript} from '@vue/compiler-sfc'
import {readFile,writeFile} from 'node:fs/promises'

const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','MouseEvent','navigator','localStorage'])Object.defineProperty(globalThis,key,{value:dom.window[key],configurable:true})
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.cancelAnimationFrame=window.cancelAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
Object.defineProperty(HTMLElement.prototype,'clientWidth',{get:()=>390})
Object.defineProperty(HTMLElement.prototype,'clientHeight',{get:()=>650})
SVGElement.prototype.createSVGRect=()=>({})
const stored=new Map()
let quota=false,online=true,requests=0
Object.defineProperty(navigator,'onLine',{get:()=>online})
const cache={async match(key){return stored.get(key)?.clone()},async put(key,value){if(quota)throw Error('QuotaExceeded');stored.set(key,value)},async delete(key){return stored.delete(key)}}
globalThis.caches={open:async()=>cache}
const bounds=[15.28,52.33,15.30,52.35]
const fixture={version:1,bounds,attribution:'© OpenStreetMap contributors · ODbL',map:{type:'FeatureCollection',features:[
 {type:'Feature',properties:{highway:'path',name:'Ścieżka'},geometry:{type:'LineString',coordinates:[[15.285,52.335],[15.295,52.345]]}},
 {type:'Feature',properties:{place:'village',name:'<b>Łagów</b>'},geometry:{type:'Point',coordinates:[15.29,52.34]}}
]}}
globalThis.fetch=async url=>{requests++;assert.ok(String(url).startsWith('/api/maps/offline?'));return {ok:true,json:async()=>fixture}}
const {downloadOfflineMap,readOfflineMap,validateMapArea}=await import('../src/offlineMaps.js')
assert.throws(()=>validateMapArea([14,50,16,54]),/Przybliż/)
await assert.rejects(downloadOfflineMap([14,50,16,54]),/Przybliż/)
assert.equal(requests,0)
await downloadOfflineMap(bounds,{places:[{id:1,lat:52.34,lng:15.29},{id:2,lat:53,lng:16}]})
assert.equal(requests,1)
assert.deepEqual((await readOfflineMap()).places.map(p=>p.id),[1])
quota=true
await assert.rejects(downloadOfflineMap(bounds),/Brakuje miejsca/)
assert.equal((await readOfflineMap()).places.length,1,'Failed replacement retains the saved map')
quota=false;online=false

const {createApp,nextTick,ref,h}=await import('vue')
const descriptor=parse(await readFile('src/components/TravelMap.vue','utf8')).descriptor
let source=compileScript(descriptor,{id:'offline-map-dom',inlineTemplate:true}).content
for(const name of ['apiResponse','mapPreferences','mapClusters','navigationDirections','offlineMaps'])source=source.replace(`from '../${name}.js'`,`from '../src/${name}.js'`)
await writeFile('artifacts/offline-map-test.mjs',source)
const MapComponent=(await import('../artifacts/offline-map-test.mjs')).default
const track=ref([{lat:52.335,lng:15.285}]),position=ref({lat:52.34,lng:15.29,accuracy:8,heading:90})
let app=createApp({render:()=>h(MapComponent,{places:[],minimal:true,directionalPosition:true,userLocation:position.value,travelledTrack:track.value,geometry:{type:'LineString',coordinates:[[15.285,52.335],[15.295,52.345]]}})})
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,30));await nextTick()}
const before=requests
app.mount('#app');await settle()
assert.ok(document.querySelector('.offline-view'))
assert.equal(document.querySelector('img.leaflet-tile'),null,'Offline map does not request raster tiles')
assert.equal(document.querySelector('.offline-place-label').textContent,'<b>Łagów</b>')
assert.equal(document.querySelector('.offline-place-label b'),null,'Saved map labels cannot inject HTML')
assert.ok(document.querySelector('path[stroke="#aa8b66"]'),'Offline paths are rendered from saved data')
assert.ok(document.querySelector('path[fill="#176944"]'),'Travelled positions are small green dots')
assert.ok(document.querySelector('.gps-direction-icon'),'GPS crosshair/direction remains visible offline')
assert.equal(document.querySelector('.offline-map-download').disabled,true)
track.value=[...track.value,{lat:52.336,lng:15.286}];await settle()
assert.equal(document.querySelectorAll('path[fill="#176944"]').length,2)
assert.equal(requests,before,'Map and GPS remain usable with no network requests')
app.unmount()
app=createApp(MapComponent,{places:[],minimal:true});app.mount('#app');await settle()
assert.ok(document.querySelector('.offline-view'),'Reload restores the saved fragment offline')
online=true;window.dispatchEvent(new Event('online'));await settle()
assert.ok(document.querySelector('.offline-view'),'Regaining network does not unexpectedly replace the offline view')
document.querySelector('[aria-label="Usuń zapisany fragment mapy"]').click();await settle()
assert.equal(await readOfflineMap(),null)
assert.equal(document.querySelector('.offline-view'),null)
app.unmount();dom.window.close()
console.log('PASS: bounded map download, storage errors, offline reload/rendering, safe labels, live GPS/dots, no tile prefetch, deletion and network transitions')
