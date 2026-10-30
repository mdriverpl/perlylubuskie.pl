import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {sortNearby,distanceKm} from '../src/explore.js'
assert.equal(distanceKm({lat:0,lng:0},{lat:0,lng:0}),0)
assert.ok(Math.abs(distanceKm({lat:0,lng:0},{lat:0,lng:1})-111.195)<.01)
assert.ok(distanceKm({lat:0,lng:179.9},{lat:0,lng:-179.9})<23)
assert.equal(distanceKm(null,{lat:0,lng:0}),Infinity)
assert.equal(distanceKm({lat:91,lng:0},{lat:0,lng:0}),Infinity)
const points=[{id:1001,name:'A1',lat:52,lng:15},{id:1003,name:'B1',lat:52,lng:16},{id:1002,name:'A2',lat:52.001,lng:15.001},{id:1004,name:'B2',lat:52.001,lng:16.001}]
const original=points.map(p=>p.id)
assert.deepEqual(sortNearby(points).map(p=>p.id),[1001,1002,1003,1004])
assert.deepEqual(points.map(p=>p.id),original)
assert.deepEqual(sortNearby([...points].reverse()).map(p=>p.id),[1001,1002,1003,1004])
assert.deepEqual(sortNearby(points,{lat:52,lng:16}).map(p=>p.id),[1003,1004,1002,1001])
assert.deepEqual(sortNearby([]),[])
assert.equal(sortNearby([...points,{id:9,lat:null,lng:null}]).at(-1).id,9)
assert.deepEqual(sortNearby([{id:1,lat:0,lng:179.9},{id:2,lat:0,lng:0},{id:3,lat:0,lng:-179.9}],{lat:0,lng:179.8}).map(p=>p.id),[1,3,2])
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
Object.defineProperty(globalThis,'navigator',{value:dom.window.navigator,configurable:true})
let geoCalls=0
Object.defineProperty(navigator,'geolocation',{value:{getCurrentPosition(success){geoCalls++;success({coords:{latitude:52,longitude:16,accuracy:10}})}}})
localStorage.setItem('perly-route','[]')
globalThis.fetch=async path=>{assert.equal(path,'/api/places');return {ok:true,json:async()=>points.map(p=>({...p,category:'nature',subtitle:'Miejsce',location:'Lubuskie',image:'/images/lake.webp',description:'Opis',popularity:p.id===1003?100:0}))}}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async selector=>{document.querySelector(selector).click();await settle()}
const names=()=>[...document.querySelectorAll('.explore-place .place-title')].map(el=>el.textContent)
await settle();await click('[aria-label="Widok kafelków"]')
assert.equal(document.querySelector('[aria-label="Sortuj miejsca"]').value,'nearby')
assert.deepEqual(names(),['A1','A2','B1','B2'])
await click('[aria-label="Widok listy"]');assert.deepEqual(names(),['A1','A2','B1','B2'])
const sort=document.querySelector('[aria-label="Sortuj miejsca"]');sort.value='recommended';sort.dispatchEvent(new Event('change',{bubbles:true}));await settle()
assert.equal(names()[0],'B1')
await click('[aria-label="Widok kafelków"]');assert.equal(names()[0],'B1')
sort.value='nearby';sort.dispatchEvent(new Event('change',{bubbles:true}));await settle();assert.deepEqual(names(),['A1','A2','B1','B2'])
const radius=document.querySelector('[aria-label="Filtr odległości"]')
assert.equal(radius.disabled,true)
assert.equal(sort.querySelector('[value="distance"]').disabled,true)
assert.equal(geoCalls,0)
await click('[aria-label="Widok mapy"]')
await click('[aria-label="Pokaż, gdzie jestem"]')
assert.equal(geoCalls,1)
assert.equal(radius.disabled,true,'GPS does not enable distance filtering')
assert.equal(sort.querySelector('[value="distance"]').disabled,true)
assert.equal(document.querySelector('.test-explore-map').dataset.ids.split(',').length,4)
await click('[aria-label="Widok listy"]')
assert.deepEqual(names(),['A1','A2','B1','B2'],'GPS does not reorder or hide places')
assert.equal(document.querySelector('.place-distance'),null)
app.unmount();dom.window.close()
console.log('PASS: nearby grouping, distance sorting/radius, no automatic geolocation, facet counts, map/list/grid parity and reset')
