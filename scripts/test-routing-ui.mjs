import { JSDOM } from 'jsdom'
import assert from 'node:assert/strict'
import { demoPlaces as places } from '../src/data.js'
const dom=new JSDOM('<!doctype html><div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
let fail=false, requests=[]
globalThis.fetch=async(path,options={})=>{
 if(path==='/api/places')return {ok:true,json:async()=>places}
 if(path==='/api/routing'){
  const payload=JSON.parse(options.body);requests.push(payload)
  return {ok:!fail,json:async()=>fail?{detail:'Brak połączenia z silnikiem'}:{geometry:{type:'LineString',coordinates:[[15.2922,52.3347,100],[15.295,52.338,110],[15.2973,52.3511,102]]},distance_m:payload.transport==='bike'?6000:4000,duration_s:payload.transport==='bike'?1800:3600}}
 }
 throw Error('Unexpected path '+path)
}
localStorage.setItem('perly-saved',JSON.stringify([{id:101,name:'Rowerowa testowa',transport:'bike',place_ids:[1,5,3]},{id:102,name:'Piesza testowa',transport:'walk',place_ids:[1,5,3]}]))
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const button=text=>[...document.querySelectorAll('button')].find(b=>b.textContent.includes(text))
const waitRoute=async()=>{for(let i=0;i<60;i++){await new Promise(r=>setTimeout(r,10));await nextTick();if(!document.querySelector('.routing-status')?.textContent.includes('Wyznaczam'))return}throw Error('Routing did not settle')}
await settle();button('Wycieczki rowerowe').click();await settle()
assert.ok(document.querySelector('.route-library'))
assert.equal(document.querySelector('.planner-layout'),null)
document.querySelector('.route-library-open').click();await nextTick()
assert.ok(button('Pobierz punkty').disabled)
await waitRoute()
assert.equal(requests.at(-1).transport,'bike')
assert.equal(button('Wycieczki rowerowe').getAttribute('aria-current'),'page')
assert.match(document.querySelector('.route-stats').textContent,/6 km/)
assert.match(document.querySelector('.route-stats').textContent,/30 min/)
assert.equal(document.querySelector('.map-panel .test-explore-map').dataset.approximate,'false')
assert.equal(JSON.parse(document.querySelector('.map-panel .test-explore-map').dataset.geometry).coordinates.length,3)
assert.ok(button('Pobierz trasę'))
document.querySelector('.test-drag-point').click();await nextTick();await waitRoute()
assert.deepEqual(requests.at(-1).point_positions,[{id:1,lat:52.12,lng:15.31}])
button('Wycieczki piesze').click();await settle()
assert.ok(document.querySelector('.route-library'))
document.querySelector('.route-library-open').click();await nextTick();await waitRoute()
assert.equal(requests.at(-1).transport,'walk')
assert.equal(button('Wycieczki piesze').getAttribute('aria-current'),'page')
assert.equal(button('Wycieczki rowerowe').getAttribute('aria-current'),null)
assert.match(document.querySelector('.route-stats').textContent,/4 km/)
let exported
URL.createObjectURL=blob=>{exported=blob;return 'blob:test'};URL.revokeObjectURL=()=>{}
dom.window.HTMLAnchorElement.prototype.click=()=>{}
button('Pobierz trasę').click();await settle()
const xml=new dom.window.DOMParser().parseFromString(await exported.text(),'text/xml')
assert.equal(xml.querySelectorAll('trkpt').length,3)
assert.equal(xml.querySelectorAll('rtept').length,0)
fail=true
document.querySelector('[aria-label="Przesuń Łagów niżej"]').click();await nextTick();await waitRoute()
assert.match(document.querySelector('.routing-error').textContent,/Brak połączenia/)
const fallback=document.querySelector('.map-panel .test-explore-map')
assert.equal(fallback.dataset.approximate,'false')
assert.equal(JSON.parse(fallback.dataset.geometry),null,'Routing errors must not show a straight-line substitute')
assert.match(document.querySelector('.route-stats').textContent,/— km/)
assert.ok(button('Pobierz punkty'))
assert.ok(!button('Pobierz trasę'))
assert.equal(requests.at(-1).place_ids[0],5)
fail=false;button('Spróbuj ponownie').click();await nextTick();await waitRoute();assert.ok(button('Pobierz trasę'))
button('Autem').click();await settle();assert.ok(button('Pobierz punkty'))
app.unmount();dom.window.close()
console.log('PASS: cycling/walking routing, distance/time, loading, GPX track, error clears stale route, retry and car fallback')
