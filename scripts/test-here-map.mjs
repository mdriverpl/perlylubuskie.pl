import {JSDOM} from 'jsdom'
import {parse,compileScript} from '@vue/compiler-sfc'
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import assert from 'node:assert/strict'
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','navigator'])Object.defineProperty(globalThis,key,{value:dom.window[key],configurable:true})
let tileError,removed=0,lastTile,notices=[],mapOptions,events={},custom=[],views=[]
const map={setView(center,zoom){views.push({center,zoom});return this},fitBounds(){},getBounds(){return {intersects:()=>true}},getZoom:()=>8,on(event,handler){events[event]=handler},remove(){removed++},removeLayer(){},attributionControl:{addAttribution(a){notices.push(a)},removeAttribution(){}}}
const layer={clearLayers(){},addTo(){return this}}
globalThis.__leaflet={map:(element,options)=>{mapOptions=options;return map},layerGroup:()=>layer,tileLayer(url,options){lastTile={url,options};return {off(){},once(event,fn){tileError=fn},addTo(){return this}}}}
globalThis.fetch=async()=>({ok:true,json:async()=>({provider:'here',copyrights:{terrain:[{label:'<Supplier>',boxes:[],minLevel:0,maxLevel:20}]}})})
const {createApp,nextTick}=await import('vue')
const descriptor=parse(await readFile('src/components/TravelMap.vue','utf8')).descriptor
await mkdir('artifacts',{recursive:true})
await writeFile('artifacts/here-map-test.mjs',compileScript(descriptor,{id:'here-map-test',inlineTemplate:true}).content.replace("import * as L from 'leaflet/dist/leaflet-src.esm.js'",'const L=globalThis.__leaflet'))
const Component=(await import('../artifacts/here-map-test.mjs')).default
const app=createApp(Component,{places:[],allowCustomPoints:true,onCreatePoint:p=>custom.push(p)});app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
await settle()
assert.equal(mapOptions.doubleClickZoom,false)
events.dblclick({latlng:{lat:52.12345678,lng:15.34567891}})
assert.deepEqual(custom,[{lat:52.123457,lng:15.345679}])
events.dblclick({latlng:{lat:52.1,lng:15.3},originalEvent:{target:{closest:()=>({})}}})
assert.equal(custom.length,1)
assert.equal(lastTile.url,'/api/maps/tiles/terrain/{z}/{x}/{y}')
assert.equal(document.querySelectorAll('.map-style-switch button')[2].getAttribute('aria-pressed'),'true')
assert.equal(document.querySelectorAll('.map-style-switch button').length,3)
assert.ok(notices.some(n=>n.includes('&lt;Supplier&gt;')))
document.querySelectorAll('.map-style-switch button')[1].click();await settle()
assert.equal(lastTile.url,'/api/maps/tiles/satellite/{z}/{x}/{y}')
document.querySelectorAll('.map-style-switch button')[2].click();await settle()
assert.equal(lastTile.url,'/api/maps/tiles/terrain/{z}/{x}/{y}')
tileError();await settle()
assert.match(lastTile.url,/openstreetmap/)
assert.match(document.querySelector('[role=status]').textContent,/HERE.*OpenStreetMap/)
assert.equal(document.querySelector('.map-style-switch'),null)
app.unmount();assert.equal(removed,1)
globalThis.fetch=async()=>({ok:false,json:async()=>({detail:'Klucz HERE nie ma dostępu do map.'})})
const invalidApp=createApp(Component,{places:[],fitPlaces:true,focusLocation:{lat:52.1,lng:15.3}});invalidApp.mount('#app');await settle()
assert.deepEqual(views.at(-1),{center:[52.1,15.3],zoom:14},'Planner opens near the added place with its surroundings visible')
assert.equal(mapOptions.doubleClickZoom,true)
events.dblclick({latlng:{lat:52.1,lng:15.3}});assert.equal(custom.length,1)
assert.match(lastTile.url,/openstreetmap/)
assert.match(document.querySelector('[role=status]').textContent,/Klucz HERE.*OpenStreetMap/)
assert.equal(document.querySelector('.map-style-switch'),null)
invalidApp.unmount();dom.window.close()
console.log('PASS: HERE default map, satellite/terrain controls, escaped supplier attribution, tile failure fallback and cleanup')
