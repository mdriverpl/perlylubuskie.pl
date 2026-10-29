import { JSDOM } from 'jsdom'
import assert from 'node:assert/strict'
import { places } from '../src/data.js'
import { filterPlaces } from '../src/explore.js'
assert.equal(filterPlaces(places,'  Województwo Lubuskie ','',[]).length,6)
assert.deepEqual(filterPlaces(places,'Lubuskie','',['castles']).map(p=>p.id),[1])
assert.deepEqual(filterPlaces(places,'Lubuskie','',['castles','restaurants']).map(p=>p.id),[1,4])
assert.deepEqual(filterPlaces(places,'Lubuskie','',['history','castles']).map(p=>p.id),[1,2,3])
assert.equal(filterPlaces(places,'Mazowieckie','',[]).length,0)
const dom=new JSDOM('<!doctype html><div id="app"></div>',{url:'http://localhost',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
Object.defineProperty(globalThis,'navigator',{value:dom.window.navigator,configurable:true})
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
let geoCalls=0,deny=false
Object.defineProperty(navigator,'geolocation',{configurable:true,value:{getCurrentPosition(success,failure){geoCalls++;deny?failure({code:1}):success({coords:{latitude:52.3,longitude:15.4,accuracy:25}})}}})
globalThis.fetch=async path=>{if(path==='/api/places')return {ok:true,json:async()=>places};if(path.includes('/community'))return {ok:true,json:async()=>({visit_count:0,visited:false,comment_count:0,comments:[]})};throw Error('Unexpected '+path)}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const button=text=>[...document.querySelectorAll('button')].find(b=>b.textContent.includes(text))
const click=async element=>{assert.ok(element);element.click();await settle()}
const input=async(selector,value)=>{const field=document.querySelector(selector);field.value=value;field.dispatchEvent(new Event('input',{bubbles:true}));await settle()}
await settle()
assert.ok(document.querySelector('.explore-home'))
assert.equal(document.querySelectorAll('.explore-place').length,6)
assert.deepEqual([...document.querySelectorAll('[role="tab"]')].map(t=>t.textContent.trim().replace(/\d/g,'')),['Miejsca','Mapa'])
await click(document.querySelector('input[value="castles"]'))
assert.equal(document.querySelectorAll('.explore-place').length,1)
await click(document.querySelector('input[value="restaurants"]'))
assert.equal(document.querySelectorAll('.explore-place').length,2)
await click(document.getElementById('explore-tab-map'))
assert.equal(document.querySelector('.test-explore-map').dataset.ids,'1,4')
assert.equal(geoCalls,0)
await click(button('Pokaż, gdzie jestem'))
assert.equal(geoCalls,1)
assert.equal(document.querySelector('.test-explore-map').dataset.userLat,'52.3')
assert.match(document.querySelector('.explore-map-legend').textContent,/25 m/)
await click(document.querySelector('[aria-label="Usuń filtr: Zamki"]'))
assert.equal(document.querySelector('.test-explore-map').dataset.ids,'4')
deny=true;await click(button('Odśwież moją lokalizację'))
assert.match(document.querySelector('.location-error').textContent,/Brak zgody/)
assert.equal(document.querySelector('.test-explore-map').dataset.ids,'4')
await click(document.getElementById('explore-tab-places'))
assert.equal(document.querySelectorAll('.explore-place').length,1)
await click(button('Wyczyść filtry'))
await input('#explore-region','Mazowieckie')
assert.ok(document.querySelector('.explore-empty'))
assert.equal(document.querySelectorAll('.explore-place').length,0)
await click(button('Pokaż miejsca w Lubuskiem'))
await input('#explore-query','Trześniowskie')
assert.equal(document.querySelectorAll('.explore-place').length,1)
document.getElementById('explore-tab-places').dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true}));await settle()
assert.equal(document.activeElement.id,'explore-tab-map')
assert.equal(document.querySelector('.test-explore-map').dataset.ids,'5')
await click(button('Map: Jezioro Trześniowskie'))
assert.match(document.querySelector('.modal h2').textContent,/Jezioro Trześniowskie/)
app.unmount();dom.window.close()
console.log('PASS: two tabs, region/checkbox/query filters, map parity, explicit geolocation and denial, keyboard tabs and marker opens place')
