import {JSDOM} from 'jsdom'
import {parse,compileScript} from '@vue/compiler-sfc'
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import assert from 'node:assert/strict'
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','navigator','localStorage'])Object.defineProperty(globalThis,key,{value:dom.window[key],configurable:true})
let tileError,removed=0,lastTile,notices=[],mapOptions,events={},custom=[],views=[],zoom=8,layers=[],fetches=0
const bounds={intersects:()=>true,pad(){return this},getWest:()=>14,getEast:()=>24.2,getSouth:()=>49,getNorth:()=>55}
const map={setView(center,z){zoom=z;views.push({center,zoom:z});return this},setMaxZoom(){return this},fitBounds(){},getBounds:()=>bounds,getZoom:()=>zoom,on(event,handler){events[event]=handler},remove(){removed++},removeLayer(){},attributionControl:{addAttribution(a){notices.push(a)},removeAttribution(){}}}
globalThis.__leaflet={
 map:(element,options)=>{mapOptions=options;return map},
 layerGroup(){const layer={markers:[],clearLayers(){this.markers=[]},addTo(){return this}};layers.push(layer);return layer},
 tileLayer(url,options){lastTile={url,options};return {off(){},on(event,fn){if(event==='tileerror')tileError=fn;return this},addTo(){return this}}},
 divIcon:options=>options,
 marker(center,options){return {center,options,events:{},addTo(layer){layer.markers.push(this);return this},bindTooltip(label){this.tooltip=label;return this},on(event,handler){this.events[event]=handler;return this},getLatLng:()=>({lat:52.12345678,lng:15.34567891}),bindPopup(popup){this.popup=popup;return this},openPopup(){this.open=true;return this}}},
}
globalThis.fetch=async()=>{fetches++;return {ok:true,json:async()=>({provider:'here',copyrights:{terrain:[{label:'<Supplier>',boxes:[],minLevel:0,maxLevel:20}]}})}}
const {createApp,nextTick}=await import('vue')
const descriptor=parse(await readFile('src/components/TravelMap.vue','utf8')).descriptor
await mkdir('artifacts',{recursive:true})
let source=compileScript(descriptor,{id:'here-map-test',inlineTemplate:true}).content.replace("import * as L from 'leaflet/dist/leaflet-src.esm.js'",'const L=globalThis.__leaflet')
for(const name of ['apiResponse','mapPreferences','mapClusters'])source=source.replace(`from '../${name}.js'`,`from '../src/${name}.js'`)
await writeFile('artifacts/here-map-test.mjs',source)
const Component=(await import('../artifacts/here-map-test.mjs')).default
const app=createApp(Component,{places:[],allowCustomPoints:true,onCreatePoint:p=>custom.push(p)});app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
await settle()
assert.equal(mapOptions.doubleClickZoom,false)
assert.equal(lastTile.url,'https://tile.openstreetmap.org/{z}/{x}/{y}.png')
assert.equal(fetches,0,'Default OSM needs no HERE configuration request')
assert.equal(document.querySelectorAll('.map-provider-switch button')[0].getAttribute('aria-pressed'),'true')
events.dblclick({latlng:{lat:52.12345678,lng:15.34567891}})
assert.deepEqual(custom,[{lat:52.123457,lng:15.345679}])
events.dblclick({latlng:{lat:52.1,lng:15.3},originalEvent:{target:{closest:()=>({})}}})
assert.equal(custom.length,1)
document.querySelectorAll('.map-provider-switch button')[1].click();await settle()
assert.equal(fetches,1)
assert.equal(lastTile.url,'/api/maps/tiles/terrain/{z}/{x}/{y}')
assert.equal(document.querySelectorAll('.map-style-switch button')[2].getAttribute('aria-pressed'),'true')
assert.equal(document.querySelectorAll('.map-style-switch button').length,3)
assert.ok(notices.some(n=>n.includes('&lt;Supplier&gt;')))
document.querySelectorAll('.map-style-switch button')[1].click();await settle()
assert.equal(lastTile.url,'/api/maps/tiles/satellite/{z}/{x}/{y}')
document.querySelectorAll('.map-style-switch button')[2].click();await settle()
tileError();await settle()
assert.match(lastTile.url,/api\/maps\/tiles/,'One failed tile never disables HERE')
tileError();tileError();await settle()
assert.match(lastTile.url,/openstreetmap/)
assert.match(document.querySelector('[role=status]').textContent,/HERE.*OpenStreetMap/)
assert.equal(document.querySelector('.map-style-switch'),null)
app.unmount();assert.equal(removed,1)
globalThis.fetch=async()=>({ok:false,json:async()=>({detail:'Klucz HERE nie ma dostępu do map.'})})
const invalidApp=createApp(Component,{places:[],fitPlaces:true,focusLocation:{lat:52.1,lng:15.3}});invalidApp.mount('#app');await settle()
assert.deepEqual(views.at(-1),{center:[52.1,15.3],zoom:14})
assert.equal(mapOptions.doubleClickZoom,true)
assert.match(lastTile.url,/openstreetmap/)
assert.match(document.querySelector('[role=status]').textContent,/Klucz HERE.*OpenStreetMap/)
invalidApp.unmount()
localStorage.removeItem('perly:map-provider')
const places=Array.from({length:8},(_,i)=>({id:i+1,name:i===1?'<b>Bezpieczna nazwa</b>':'Miejsce '+i,lat:53.01+i*.000001,lng:18.6}))
const selected=[],moved=[]
const clusterApp=createApp(Component,{places,selected:[1],draggablePoints:true,onSelect:id=>selected.push(id),onMovePoint:p=>moved.push(p)});clusterApp.mount('#app');await settle()
const markers=layers.at(-1).markers
assert.equal(markers.length,2,'Seven nearby points cluster while route point remains separate')
const routePoint=markers.find(m=>m.options.draggable)
assert.match(routePoint.options.icon.html,/chosen/)
routePoint.events.click();assert.deepEqual(selected,[1])
routePoint.events.dragend();assert.deepEqual(moved,[{id:1,lat:52.123457,lng:15.345679}])
const cluster=markers.find(m=>m.options.title)
cluster.events.click();assert.equal(cluster.open,true)
assert.equal(cluster.popup.querySelectorAll('button').length,7)
assert.equal(cluster.popup.querySelector('b'),null)
cluster.popup.querySelector('button').click();assert.equal(selected.length,2)
assert.notEqual(selected[1],1)
clusterApp.unmount();assert.equal(removed,3);dom.window.close()
console.log('PASS: instant default OSM, optional remembered HERE, transient tile tolerance, fallback, escaped clustering, popup selection, draggable numbered stops and cleanup')
