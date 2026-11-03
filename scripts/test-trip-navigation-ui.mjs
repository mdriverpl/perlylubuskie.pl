import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {demoPlaces} from '../src/data.js'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/wycieczki',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','KeyboardEvent','localStorage'])globalThis[key]=dom.window[key]
Object.defineProperty(globalThis,'navigator',{value:window.navigator,configurable:true})
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
let gpsCalls=0,deliver
Object.defineProperty(navigator,'geolocation',{value:{getCurrentPosition(success){gpsCalls++;deliver=()=>success({coords:{latitude:52.3347,longitude:15.2922,accuracy:8}})}}})
localStorage.setItem('perly-saved',JSON.stringify([{id:101,name:'Spacer testowy',transport:'walk',place_ids:[1,5]}]))
const geometry={type:'LineString',coordinates:[[15.2922,52.3347],[15.2973,52.3511]]}
globalThis.fetch=async path=>({ok:true,json:async()=>path==='/api/places'?demoPlaces:path==='/api/routing'?{geometry,distance_m:2500,duration_s:1800}:[]})
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const waitFor=async check=>{for(let i=0;i<100;i++){await settle();if(check())return;await new Promise(r=>setTimeout(r,10))}throw Error('Navigation did not settle')}
await settle();assert.equal(gpsCalls,0,'Opening the library never asks for GPS')
document.querySelector('.trip-navigation-start').click();await settle();await settle()
let nav=document.querySelector('.trip-navigation');assert.ok(nav)
assert.equal(gpsCalls,1,'Starting navigation explicitly requests the current position')
deliver();await waitFor(()=>JSON.parse(document.querySelector('.trip-navigation .test-explore-map').dataset.geometry||'null')?.coordinates.length===2)
assert.equal(nav.querySelector('.test-explore-map').dataset.userLat,'52.3347')
assert.equal(document.body.style.overflow,'hidden')
nav.querySelector('[aria-controls="navigation-options"]').click();await settle()
const checkbox=nav.querySelector('.navigation-options input');checkbox.click();await settle()
assert.equal(localStorage.getItem('perly:navigation-track-only'),'true')
nav.querySelector('.navigation-refresh').click();await settle();assert.equal(gpsCalls,2)
deliver();await settle()
nav.querySelector('.navigation-back').click();await settle()
assert.equal(document.querySelector('.trip-navigation'),null)
assert.equal(window.location.pathname,'/wycieczki','Back returns to the trip library')
assert.equal(document.body.style.overflow,'')
document.querySelector('.trip-navigation-start').click();await settle();await settle()
nav=document.querySelector('.trip-navigation');assert.equal(gpsCalls,2,'An active GPS fix can be reused')
nav.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));await settle()
assert.equal(document.querySelector('.trip-navigation'),null)
assert.equal(window.location.pathname,'/wycieczki')
app.unmount();dom.window.close()
console.log('PASS: fullscreen navigation, real route data, explicit GPS and refresh, track-only preference, back and Escape')
