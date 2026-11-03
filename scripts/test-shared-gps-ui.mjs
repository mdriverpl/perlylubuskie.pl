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
const nav=async name=>click([...document.querySelectorAll('.main-navigation button')].find(el=>(el.dataset.navLabel||el.textContent.trim())===name))
const locateButton=()=>document.querySelector('.map-locate-button')
const fix=(lat=52.33)=>success({coords:{latitude:lat,longitude:15.29,accuracy:12}})
await settle();assert.equal(calls,0);assert.equal(document.querySelector('.gps-toggle'),null)
await nav('Miejsca')
assert.equal(document.querySelector('[aria-label="Sortuj miejsca"]').value,'distance')
assert.equal(document.querySelector('.distance-origin-note'),null)
assert.equal(calls,0,'Opening places does not request GPS automatically')
await nav('Planer')
await click(locateButton());assert.equal(calls,1)
fix();await settle();assert.equal(document.querySelector('.gps-toggle'),null)
assert.equal(document.querySelector('.gps-status'),null,'GPS does not show a coordinates banner')
for(const name of ['Miejsca','Planer','Wycieczki']){
 await nav(name);assert.equal(document.querySelector('.gps-toggle'),null);assert.equal(calls,1)
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
fix(52.34);await settle();assert.equal(document.querySelector('.gps-status'),null);assert.equal(document.querySelector('.gps-toggle'),null)
await nav('Planer')
await click(locateButton());assert.equal(calls,2);assert.deepEqual(cleared,[1])
const stale=success
failure({code:1});await settle();assert.match(document.querySelector('.gps-status').textContent,/Brak zgody/)
assert.deepEqual(cleared,[1,2])
await click([...document.querySelectorAll('.gps-status button')].find(el=>el.textContent==='Zamknij'))
stale({coords:{latitude:53,longitude:15,accuracy:10}});await settle()
assert.equal(document.querySelector('.gps-status'),null,'Closing a failed GPS request ignores late fixes')
await click(locateButton());fix();await settle()
assert.equal(document.querySelector('.test-explore-map').dataset.userLat,'52.33')
app.unmount();assert.deepEqual(cleared,[1,2,3])
dom.window.close()
console.log('PASS: shared GPS status, coordinates, live fixes, all four views, denied permission, cancellation, late callbacks and unmount cleanup')
