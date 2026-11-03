import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/'+(process.argv[2]||'miejsca'),pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','KeyboardEvent','localStorage'])globalThis[key]=dom.window[key]
Object.defineProperty(globalThis,'navigator',{value:window.navigator,configurable:true})
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
let locateCalls=0,deliverGps,reverseCalls=0,searchCalls=0,holdReverse=false,releaseReverse
Object.defineProperty(navigator,'geolocation',{value:{getCurrentPosition(success){locateCalls++;deliverGps=()=>success({coords:{latitude:52,longitude:15,accuracy:10}})}}})
const places=[{id:101,name:'Przy GPS',lat:52,lng:15},{id:102,name:'Przy adresie',lat:52,lng:16}].map(p=>({...p,category:'nature',location:'Lubuskie',subtitle:'Przyroda',image:'/images/lake.webp',description:'Opis'}))
globalThis.fetch=async path=>{
 if(path==='/api/places')return {ok:true,json:async()=>places}
 if(path.startsWith('/api/maps/reverse?')){
  reverseCalls++;assert.match(path,/lat=52&lng=15/)
  if(holdReverse)await new Promise(resolve=>releaseReverse=resolve)
  return {ok:true,json:async()=>({items:[{id:'gps',name:'Adres z GPS 1, Lubuskie',lat:52,lng:15}]})}
 }
 if(path.startsWith('/api/maps/search?')){searchCalls++;return {ok:true,json:async()=>({items:[{id:'address',name:'Wpisany adres 2, Lubuskie',lat:52,lng:16}]})}}
 return {ok:true,json:async()=>[]}
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async el=>{assert.ok(el);el.click();await settle()}
const names=()=>[...document.querySelectorAll('.place-title')].map(el=>el.textContent)
const input=()=>document.querySelector('#explore-query')
const type=async text=>{input().value=text;input().dispatchEvent(new Event('input',{bubbles:true}));await settle()}
const gpsButton=()=>document.querySelector('[aria-label="Wpisz adres z GPS"]')
await settle()
assert.equal(document.querySelector('[aria-label="Sortuj miejsca"]').value,'distance')
await click(document.querySelector('[aria-label="Widok kafelków"]'))
const pendingRadius=document.querySelector('.distance-filter select')
assert.equal(pendingRadius.disabled,false)
pendingRadius.value='5';pendingRadius.dispatchEvent(new Event('change',{bubbles:true}));await settle()
assert.equal(locateCalls,0,'Distance selection never requests GPS')
assert.equal(document.querySelector('.distance-origin-help'),null)
await click(gpsButton());assert.equal(locateCalls,1);assert.equal(gpsButton().disabled,true)
deliverGps();await settle();await settle()
assert.equal(reverseCalls,1);assert.equal(input().value,'Adres z GPS 1, Lubuskie')
assert.equal(document.querySelector('[aria-label="Sortuj miejsca"]').value,'distance')
assert.equal(pendingRadius.value,'5')
assert.deepEqual(names(),['Przy GPS'])
await click(document.querySelector('[aria-label="Widok mapy"]'))
assert.equal(document.querySelector('.test-explore-map').dataset.ids.split(',').filter(id=>Number(id)>0).join(','),'101','Map uses the same radius-filtered points')
pendingRadius.value='100';pendingRadius.dispatchEvent(new Event('change',{bubbles:true}));await settle()
assert.deepEqual(document.querySelector('.test-explore-map').dataset.ids.split(',').filter(id=>Number(id)>0),['101','102'],'Changing the limit updates map points')
await click(document.querySelector('.explore-view-switch button:nth-child(2)'))

pendingRadius.value='';pendingRadius.dispatchEvent(new Event('change',{bubbles:true}));await settle()
assert.deepEqual(names(),['Przy GPS','Przy adresie'])
await new Promise(r=>setTimeout(r,650));await settle();assert.equal(searchCalls,0,'GPS address does not trigger a second search')
await type('Wpisany adres 2')
assert.equal(searchCalls,0)
await new Promise(r=>setTimeout(r,650));await settle()
assert.equal(searchCalls,1);assert.deepEqual(names(),['Przy adresie','Przy GPS'],'Typed address overrides active GPS')
assert.equal(document.querySelector('.searched-location'),null)
const radius=document.querySelector('[aria-label="Filtr odległości"]');radius.value='5';radius.dispatchEvent(new Event('change',{bubbles:true}));await settle()
assert.deepEqual(names(),['Przy adresie'],'Radius uses the typed address')
radius.value='';radius.dispatchEvent(new Event('change',{bubbles:true}));await settle()
await click(gpsButton());await settle();assert.equal(input().value,'Adres z GPS 1, Lubuskie')
assert.equal(locateCalls,1,'Existing GPS fix can fill the address again')
assert.deepEqual(names(),['Przy GPS','Przy adresie'])
holdReverse=true;await click(gpsButton());await type('Nowy adres')
releaseReverse();await settle();await settle()
assert.equal(input().value,'Nowy adres','Late reverse lookup never overwrites edited input')
app.unmount();dom.window.close()
console.log('PASS: GPS icon, address fill, automatic search, address overrides GPS, radius origin, reuse and cancelled reverse lookup')
