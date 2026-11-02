import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {parse,compileScript} from '@vue/compiler-sfc'
import {readFile,writeFile,mkdir} from 'node:fs/promises'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','MouseEvent','navigator','localStorage'])Object.defineProperty(globalThis,key,{value:dom.window[key],configurable:true})
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.cancelAnimationFrame=window.cancelAnimationFrame.bind(window);globalThis.getComputedStyle=window.getComputedStyle.bind(window)
Object.defineProperty(HTMLElement.prototype,'clientWidth',{get:()=>900});Object.defineProperty(HTMLElement.prototype,'clientHeight',{get:()=>600})
SVGElement.prototype.createSVGRect=()=>({})
let requests=0
globalThis.fetch=async()=>{requests++;return {ok:true,json:async()=>({provider:'here',copyrights:{}})}}
const {createApp,nextTick,ref,h}=await import('vue')
const descriptor=parse(await readFile('src/components/TravelMap.vue','utf8')).descriptor
let source=compileScript(descriptor,{id:'map-dom-test',inlineTemplate:true}).content
for(const name of ['apiResponse','mapPreferences','mapClusters'])source=source.replace(`from '../${name}.js'`,`from '../src/${name}.js'`)
await mkdir('artifacts',{recursive:true});await writeFile('artifacts/map-dom-test.mjs',source)
const Component=(await import('../artifacts/map-dom-test.mjs')).default
const selected=[]
const places=[{id:1,name:'Punkt trasy',lat:52.3347,lng:15.2922},{id:2,name:'Zamek <b>Joannitów</b>',lat:52.33471,lng:15.29221},{id:3,name:'Drugie miejsce',lat:52.33472,lng:15.29222}]
const userLocation=ref(null),visiblePlaces=ref(places),distanceArea=ref(null)
const app=createApp({render:()=>h(Component,{places:visiblePlaces.value,distanceArea:distanceArea.value,userLocation:userLocation.value,selected:[1],fitPlaces:true,onSelect:id=>selected.push(id)})});app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,30));await nextTick()}
await settle();assert.equal(requests,0)
assert.ok(document.querySelector('img.leaflet-tile').src.startsWith('https://tile.openstreetmap.org/'))
assert.equal(document.querySelector('.map-pin.chosen').textContent,'1')
assert.equal(document.querySelector('.map-cluster').textContent,'2')
document.querySelector('.map-cluster').parentElement.dispatchEvent(new MouseEvent('click',{bubbles:true}));await settle()
const list=document.querySelector('.map-cluster-list')
assert.ok(list,'Real Leaflet opens the clustered-place popup')
assert.equal(list.querySelectorAll('button').length,2)
assert.equal(list.querySelector('b'),null)
userLocation.value={lat:52.3346,lng:15.292,accuracy:10};visiblePlaces.value=[...places].reverse();await settle()
assert.equal(document.querySelector('.map-cluster-list'),list,'GPS fixes and distance reordering keep an open cluster list usable')
list.querySelector('button').click();await settle();assert.ok([2,3].includes(selected[0]))
distanceArea.value={lat:52.3347,lng:15.2922,radiusKm:5};await settle()
const radiusPath=[...document.querySelectorAll('.leaflet-overlay-pane path')].find(p=>p.getAttribute('stroke')==='#19744f')
assert.ok(radiusPath,'A selected distance draws the search area on the real map')
const smallArea=radiusPath.getAttribute('d')
distanceArea.value={...distanceArea.value,radiusKm:50};await settle()
assert.notEqual(document.querySelector('path[stroke="#19744f"]').getAttribute('d'),smallArea,'Changing radius refits the map even with identical places')
distanceArea.value=null;await settle()
assert.equal(document.querySelector('path[stroke="#19744f"]'),null,'Removing the limit clears its circle')
document.querySelectorAll('.map-provider-switch button')[1].click();await settle()
assert.equal(requests,1);assert.equal(document.querySelectorAll('.map-provider-switch button')[1].getAttribute('aria-pressed'),'true')
const tiles=[...document.querySelectorAll('img.leaflet-tile')].filter(tile=>tile.src.includes('/api/maps/tiles/'))
assert.ok(tiles.length>=3)
tiles[0].dispatchEvent(new Event('error'));await settle()
assert.equal(document.querySelectorAll('.map-provider-switch button')[1].getAttribute('aria-pressed'),'true')
tiles[1].dispatchEvent(new Event('error'));tiles[2].dispatchEvent(new Event('error'));await settle()
assert.equal(document.querySelectorAll('.map-provider-switch button')[0].getAttribute('aria-pressed'),'true')
assert.ok(document.querySelector('.map-pin.chosen'),'Provider changes preserve route markers')
app.unmount();dom.window.close()
console.log('PASS: real Leaflet DOM renders OSM tiles, clusters, safe popup selection and numbered stops, switches HERE and tolerates a single tile error')
