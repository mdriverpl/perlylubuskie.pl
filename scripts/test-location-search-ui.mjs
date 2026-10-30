import {JSDOM} from 'jsdom'
import assert from 'node:assert/strict'
import {demoPlaces as places} from '../src/data.js'
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','KeyboardEvent','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
let calls=0,fail=false
globalThis.fetch=async path=>{
 if(path==='/api/places')return {ok:true,json:async()=>places}
 if(path.startsWith('/api/maps/search?')){calls++;assert.match(decodeURIComponent(path),/Łaz/);return {ok:!fail,json:async()=>fail?{detail:'Brak dostępu do wyszukiwania HERE.'}:{items:[{id:'laz',name:'Łaz, gmina Zabór, Polska',lat:51.94944,lng:15.68673}]}}}
 throw Error('Unexpected '+path)
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
await settle()
const input=document.querySelector('#explore-query');input.value='Łaz';input.dispatchEvent(new Event('input',{bubbles:true}));await settle()
assert.equal(calls,0)
assert.equal(document.querySelector('.find-map-location'),null);input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await settle()
assert.equal(calls,1)
assert.match(document.querySelector('.searched-location').textContent,/Łaz, gmina Zabór/)
assert.equal(document.querySelector('.test-explore-map').getAttribute('data-search-lat'),'51.94944')
assert.equal(document.querySelector('.map-no-results'),null)
const radius=document.querySelector('[aria-label="Filtr odległości"]')
assert.equal(radius.disabled,false)
radius.value='100';radius.dispatchEvent(new Event('change',{bubbles:true}));await settle()
assert.ok(document.querySelector('.test-explore-map').dataset.ids.length>0,'Location radius finds nearby places even when town name is absent from catalog')
input.value='Łaz 2';input.dispatchEvent(new Event('input',{bubbles:true}));await settle()
assert.equal(document.querySelector('.searched-location'),null)
assert.equal(radius.value,'')
assert.equal(radius.disabled,true)
fail=true;input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await settle()
assert.match(document.querySelector('.location-search-error').textContent,/Brak dostępu/)
app.unmount();dom.window.close()
console.log('PASS: Łaz search outside the catalog, explicit submit, HERE coordinates, query reset and server errors')
