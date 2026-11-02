import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
Object.defineProperty(globalThis,'navigator',{value:window.navigator,configurable:true})
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
let success,failure,calls=0,cleared=[]
Object.defineProperty(navigator,'geolocation',{value:{watchPosition(ok,fail,options){calls++;success=ok;failure=fail;assert.equal(options.enableHighAccuracy,true);return calls},clearWatch(id){cleared.push(id)}}})
const places=[{id:101,name:'Dalej',lat:53,lng:15.29},{id:102,name:'Blisko',lat:52.33,lng:15.29}].map(p=>({...p,category:'nature',location:'Lubuskie',image:'/images/lake.webp',description:'Opis',subtitle:'Przyroda'}))
globalThis.fetch=async path=>({ok:true,json:async()=>path==='/api/places'?places:[]})
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async el=>{assert.ok(el);el.click();await settle()}
const nav=async name=>click([...document.querySelectorAll('.main-navigation button')].find(el=>el.textContent.trim()===name))
const toggle=()=>document.querySelector('.gps-toggle')
const fix=(lat=52.33)=>success({coords:{latitude:lat,longitude:15.29,accuracy:12}})
await settle();assert.equal(calls,0);assert.match(toggle().textContent,/GPS OFF/)
await nav('Miejsca')
assert.equal(document.querySelector('[aria-label="Sortuj miejsca"]').value,'distance')
assert.equal(document.querySelector('.distance-origin-note'),null)
assert.equal(calls,0,'Opening places does not request GPS automatically')
await nav('Planer')
await click(toggle());assert.match(toggle().textContent,/GPS?/)
fix();await settle();assert.match(toggle().textContent,/GPS ON/)
assert.equal(document.querySelector('.gps-status'),null,'GPS does not show a coordinates banner')
for(const name of ['Miejsca','Planer','Wycieczki piesze','Wycieczki rowerowe']){
 await nav(name);assert.match(toggle().textContent,/GPS ON/);assert.equal(calls,1)
 if(name==='Miejsca'){
  assert.equal(document.querySelector('[aria-label="Sortuj miejsca"]').value,'distance')
  assert.deepEqual([...document.querySelectorAll('.place-title')].map(el=>el.textContent),['Blisko','Dalej'])
  assert.ok(document.querySelector('.place-distance'))
  const radius=document.querySelector('[aria-label="Filtr odległości"]')
  assert.equal(radius.disabled,false,'GPS enables the distance radius')
  radius.value='5';radius.dispatchEvent(new Event('change',{bubbles:true}));await settle()
  assert.deepEqual([...document.querySelectorAll('.place-title')].map(el=>el.textContent),['Blisko'])
  radius.value='';radius.dispatchEvent(new Event('change',{bubbles:true}));await settle()
  assert.equal(document.querySelectorAll('.explore-place').length,2)
  await click(document.querySelector('[aria-label="Widok mapy"]'))
 }
 if(name==='Miejsca'||name==='Planer')assert.equal(document.querySelector('.test-explore-map').dataset.userLat,'52.33')
}
fix(52.34);await settle();assert.equal(document.querySelector('.gps-status'),null);assert.match(toggle().textContent,/GPS ON/)
await click(toggle());assert.deepEqual(cleared,[1]);assert.match(toggle().textContent,/GPS OFF/)
fix(53);await settle();assert.equal(document.querySelector('.gps-status'),null,'Late reading cannot reactivate GPS')
await click(toggle());failure({code:1});await settle();assert.match(document.querySelector('.gps-status').textContent,/Brak zgody/)
assert.match(toggle().textContent,/GPS OFF/);assert.deepEqual(cleared,[1,2])
await click(toggle());const late=success;await click(toggle());late({coords:{latitude:52,longitude:15}});await settle();assert.equal(document.querySelector('.gps-status'),null)
await click(toggle());fix();await settle();app.unmount();assert.deepEqual(cleared,[1,2,3,4])
dom.window.close()
console.log('PASS: shared GPS status, coordinates, live fixes, all four views, denied permission, cancellation, late callbacks and unmount cleanup')
