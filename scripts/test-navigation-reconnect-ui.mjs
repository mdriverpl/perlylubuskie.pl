import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {demoPlaces} from '../src/data.js'

const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/miejsca',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
Object.defineProperty(globalThis,'navigator',{value:window.navigator,configurable:true})
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
Object.defineProperty(navigator,'geolocation',{value:{watchPosition(success){success({coords:{latitude:52.3,longitude:15.3,accuracy:8}});return 1},clearWatch(){}}})
let available=false,catalogCalls=0,routingCalls=0,releaseCatalog
const geometry={type:'LineString',coordinates:[[15.3,52.3],[15.292786,52.334686]]}
globalThis.fetch=async(path)=>{
 if(path==='/api/places'){
  catalogCalls++
  if(!available)throw new TypeError('Failed to fetch')
  if(releaseCatalog===null)await new Promise(resolve=>releaseCatalog=resolve)
  return {ok:true,json:async()=>demoPlaces}
 }
 if(path==='/api/routing'){routingCalls++;return {ok:true,json:async()=>({geometry,distance_m:3000,duration_s:1800})}}
 return {ok:true,json:async()=>[]}
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
let app=createApp(App)
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const waitFor=async check=>{for(let i=0;i<150;i++){await settle();if(check())return;await new Promise(r=>setTimeout(r,10))}throw Error('Reconnection did not settle')}
const click=async element=>{assert.ok(element);element.click();await settle();await settle()}
app.mount('#app');await settle()
await click(document.querySelector('.navigate-place-button'))
await click(document.querySelector('.place-navigation-app'))
assert.equal(catalogCalls,2,'Starting navigation retries a failed initial connection')
assert.match(document.querySelector('.navigation-status').textContent,/wymaga połączenia/)
assert.equal(routingCalls,0)
await click(document.querySelector('.navigation-status button'))
assert.equal(catalogCalls,3,'Retry really requests the server while offline')
available=true;releaseCatalog=null
await click(document.querySelector('.navigation-status button'))
assert.equal(catalogCalls,4)
assert.match(document.querySelector('.navigation-status').textContent,/Wyznaczam/)
window.dispatchEvent(new Event('online'))
document.dispatchEvent(new Event('visibilitychange'))
await settle()
assert.equal(catalogCalls,4,'Concurrent reconnect triggers share the request')
releaseCatalog()
await waitFor(()=>document.querySelector('.navigation-metrics'))
assert.equal(routingCalls,1,'Recovered connection automatically calculates the route once')
assert.equal(document.querySelector('.navigation-status'),null)
assert.match(document.querySelector('.navigation-metrics').textContent,/3 km/)
app.unmount()

// Returning to the phone app, or regaining mobile data, recovers without a reload.
for(const target of ['online','visibilitychange']){
 available=false;releaseCatalog=undefined
 app=createApp(App);app.mount('#app');await settle()
 const before=catalogCalls
 available=true
 ;(target==='online'?window:document).dispatchEvent(new Event(target))
 await waitFor(()=>document.querySelector('.connection-status.online'))
 assert.equal(catalogCalls,before+1)
 app.unmount()
 const after=catalogCalls
 window.dispatchEvent(new Event('online'));document.dispatchEvent(new Event('visibilitychange'));await settle()
 assert.equal(catalogCalls,after,'Unmount removes reconnect listeners')
}
dom.window.close()
console.log('PASS: offline navigation retry, deduplicated reconnect, route recovery, mobile resume, online events and listener cleanup')
