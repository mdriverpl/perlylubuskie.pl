import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {demoPlaces} from '../src/data.js'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/wycieczki',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
localStorage.setItem('perly-saved',JSON.stringify([{id:101,name:'Spacer',transport:'walk',place_ids:[1,5]},{id:102,name:'Rower',transport:'bike',place_ids:[5,1]}]))
const requests=[]
let fail=false
globalThis.fetch=async(path,options={})=>{
 if(path==='/api/places')return {ok:true,json:async()=>demoPlaces}
 if(path==='/api/routing'){
  const data=JSON.parse(options.body);requests.push(data)
  return {ok:!fail,json:async()=>fail?{detail:'Routing unavailable'}:{distance_m:data.transport==='walk'?5000:10000,duration_s:data.transport==='walk'?3600:1800}}
 }
 return {ok:true,json:async()=>[]}
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
let app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const waitFor=async check=>{for(let i=0;i<100;i++){await settle();if(check())return;await new Promise(r=>setTimeout(r,10))}throw Error('Metrics did not settle')}
const ready=()=>document.querySelectorAll('.trip-card-metrics:not(.trip-metrics-pending)').length
await waitFor(()=>ready()===2)
assert.equal(requests.length,2)
assert.match(document.querySelector('.route-library-item').textContent,/5 km/)
assert.match(document.querySelector('.route-library-item').textContent,/1 h/)
assert.match(document.querySelectorAll('.route-library-item')[1].textContent,/10 km/)
assert.match(document.querySelectorAll('.route-library-item')[1].textContent,/30 min/)
document.querySelector('[aria-label="Wycieczki jako kafelki"]').click();await settle()
assert.ok(document.querySelector('.trip-library-tiles'))
assert.equal(ready(),2)
assert.equal(document.querySelectorAll('.trip-navigation-start').length,2)
app.unmount();app=createApp(App);app.mount('#app');await waitFor(()=>ready()===2)
assert.ok(document.querySelector('.trip-library-tiles'),'The selected library view survives reload')
await new Promise(r=>setTimeout(r,150));assert.equal(requests.length,2,'Reload uses saved road metrics')
app.unmount()
const saved=JSON.parse(localStorage.getItem('perly-saved'));saved[0].point_positions=[{id:1,lat:52.3,lng:15.3}]
localStorage.setItem('perly-saved',JSON.stringify(saved));fail=true
app=createApp(App);app.mount('#app');await waitFor(()=>!!document.querySelector('.trip-metrics-retry'))
assert.equal(ready(),1,'A changed route must not show stale metrics')
assert.deepEqual(requests.at(-1).point_positions,[{id:1,lat:52.3,lng:15.3}])
fail=false;document.querySelector('.trip-metrics-retry').click();await waitFor(()=>ready()===2)
assert.equal(requests.length,4,'Retry only calculates the route missing from cache')
assert.equal(document.querySelector('.route-library-heading>.button'),null,'The redundant choose-places button is removed')
app.unmount();dom.window.close()
console.log('PASS: trip road distance/time, list/tiles preference, cache reuse, changed-point invalidation, error and retry')
