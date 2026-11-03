import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/start',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','KeyboardEvent','localStorage'])globalThis[key]=dom.window[key]
Object.defineProperty(globalThis,'navigator',{value:window.navigator,configurable:true})
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
let gpsCalls=0,deliverGps,searchCalls=0,reverseCalls=0
Object.defineProperty(navigator,'geolocation',{value:{getCurrentPosition(success){gpsCalls++;deliverGps=()=>success({coords:{latitude:52,longitude:15,accuracy:10}})}}})
const places=[{id:101,name:'Przy GPS',lat:52,lng:15},{id:102,name:'Przy adresie',lat:52,lng:16}].map(p=>({...p,category:'nature',location:'Lubuskie',subtitle:'Przyroda',image:'/images/lake.webp',description:'Opis'}))
const address={id:'address',name:'Zielona Góra, Testowa 2',lat:52,lng:16}
globalThis.fetch=async path=>{
 if(path==='/api/places')return {ok:true,json:async()=>places}
 if(path.startsWith('/api/maps/search?')){searchCalls++;return {ok:true,json:async()=>({items:[address]})}}
 if(path.startsWith('/api/maps/reverse?')){reverseCalls++;return {ok:true,json:async()=>({items:[{id:'gps',name:'Adres z GPS 1, Lubuskie',lat:52,lng:15}]})}}
 return {ok:true,json:async()=>[]}
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
let app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async el=>{assert.ok(el);el.click();await settle()}
const nav=async name=>click([...document.querySelectorAll('.main-navigation button')].find(el=>(el.dataset.navLabel||el.textContent.trim())===name))
const names=()=>[...document.querySelectorAll('.explore-place .place-title')].map(el=>el.textContent)
const type=async(selector,text)=>{const input=document.querySelector(selector);input.value=text;input.dispatchEvent(new Event('input',{bubbles:true}));await settle()}
const reload=async()=>{app.unmount();app=createApp(App);app.mount('#app');await settle()}
await settle()
await click(document.querySelector('#hero-tab-address'))
assert.ok(document.querySelector('.hero-ai-panel .home-address-search'),'Address search sits below AI')
assert.equal(gpsCalls,0)
await type('#home-address','Zielona Góra, Testowa 2')
document.querySelector('.home-address-search form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await settle();await settle()
assert.equal(window.location.pathname,'/miejsca')
assert.deepEqual(names(),['Przy adresie','Przy GPS'])
assert.equal(document.querySelector('#explore-query').value,'Zielona Góra, Testowa 2')
assert.equal(searchCalls,1)
await nav('Planer')
assert.equal(document.querySelector('#explore-query').value,'Zielona Góra, Testowa 2')
assert.equal(document.querySelector('.test-explore-map').dataset.searchLat,'52')
assert.equal(document.querySelector('[aria-label="Filtr odległości"]').disabled,false)
await nav('Start');assert.equal(document.querySelector('#home-address').value,'Zielona Góra, Testowa 2')
await reload()
assert.equal(document.querySelector('#home-address').value,'Zielona Góra, Testowa 2')
assert.equal(gpsCalls,0,'Restoring an address never requests GPS')
await click(document.querySelector('[aria-label="Wyszukaj miejsca według GPS"]'))
assert.equal(gpsCalls,1);deliverGps();await settle();await settle()
assert.equal(reverseCalls,1)
assert.equal(window.location.pathname,'/miejsca','GPS automatically opens nearby results')
assert.deepEqual(names(),['Przy GPS','Przy adresie'])
assert.equal(document.querySelector('#explore-query').value,'Adres z GPS 1, Lubuskie')
await reload()
assert.deepEqual(names(),['Przy GPS','Przy adresie'],'Coordinates and address survive reload without GPS')
assert.equal(document.querySelector('.gps-toggle'),null)
assert.equal(gpsCalls,1);assert.equal(searchCalls,1);assert.equal(reverseCalls,1)
await nav('Planer');assert.equal(document.querySelector('#explore-query').value,'Adres z GPS 1, Lubuskie')
await click(document.querySelector('.compact-clear-filters'))
assert.equal(localStorage.getItem('perly:search-address'),null,'Clearing filters forgets the saved address')
await nav('Start');assert.equal(document.querySelector('#home-address').value,'')
app.unmount();dom.window.close()
console.log('PASS: home address search below AI, GPS auto-search, shared address/coordinates, reload without new permission or lookup, explicit reset')
