import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {demoPlaces} from '../src/data.js'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/miejsca',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
Object.defineProperty(globalThis,'navigator',{value:window.navigator,configurable:true})
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
let gpsCalls=0,deliver
const requests=[]
Object.defineProperty(navigator,'geolocation',{value:{getCurrentPosition(success){gpsCalls++;deliver=()=>success({coords:{latitude:52.3,longitude:15.3,accuracy:8}})}}})
localStorage.setItem('perly-route','[1,5]')
const geometry={type:'LineString',coordinates:[[15.3,52.3],[15.292786,52.334686]]}
globalThis.fetch=async(path,options={})=>{
 if(path==='/api/places')return {ok:true,json:async()=>demoPlaces}
 if(path==='/api/routing'){requests.push(JSON.parse(options.body));return {ok:true,json:async()=>({geometry,distance_m:3000,duration_s:1800})}}
 return {ok:true,json:async()=>[]}
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async el=>{assert.ok(el);el.click();await settle();await settle()}
const waitFor=async check=>{for(let i=0;i<100;i++){await settle();if(check())return;await new Promise(r=>setTimeout(r,10))}throw Error('Place navigation did not settle')}
await settle()
const card=document.querySelector('.explore-place'),name=card.querySelector('.place-title').textContent,place=demoPlaces.find(p=>p.name===name)
assert.equal(card.querySelector('.add-place-to-list').textContent,'Zaplanuj')
assert.equal(card.querySelector('.add-place-to-list').parentElement,card.querySelector('.navigate-place-button').parentElement,'Plan and navigate actions sit together')
await click(card.querySelector('.navigate-place-button'))
assert.ok(document.querySelector('.place-navigation-choice'))
assert.equal(gpsCalls,0,'Choosing an app never asks for GPS before the choice')
await click(document.querySelector('.place-navigation-modes button'))
const google=new URL(document.querySelector('.place-navigation-google').href)
assert.equal(google.origin,'https://www.google.com')
assert.equal(google.pathname,'/maps/dir/')
assert.equal(google.searchParams.get('destination'),place.lat+','+place.lng)
assert.equal(google.searchParams.get('travelmode'),'walking')
assert.equal(document.querySelector('.place-navigation-google').target,'_blank')
await click(document.querySelector('.place-navigation-app'))
assert.ok(document.querySelector('.trip-navigation'))
assert.equal(gpsCalls,1)
deliver();await waitFor(()=>requests.length>0&&JSON.parse(document.querySelector('.trip-navigation .test-explore-map').dataset.geometry||'null')?.coordinates.length===2)
assert.deepEqual(requests.at(-1).place_ids,[-9000000000002,place.id])
assert.equal(requests.at(-1).transport,'walk')
assert.deepEqual(requests.at(-1).custom_points,[{id:-9000000000002,name:'Punkt startowy',lat:52.3,lng:15.3}])
assert.equal(localStorage.getItem('perly-route'),'[1,5]','Single-place navigation never overwrites the planned trip')
await click(document.querySelector('.navigation-back'))
assert.equal(window.location.pathname,'/miejsca')
assert.equal(localStorage.getItem('perly-route'),'[1,5]')
assert.ok(document.querySelector('.explore-grid'))
await click(document.querySelector('[aria-label="Widok mapy"]'))
await click(document.querySelector('.test-explore-map button'))
await click([...document.querySelectorAll('.detail-actions button')].find(b=>b.textContent==='Nawiguj'))
assert.ok(document.querySelector('.place-navigation-choice'),'Map place details expose the same app choice')
assert.equal(gpsCalls,1)
app.unmount();dom.window.close()
console.log('PASS: adjacent plan/navigation actions, Google directions and mode, app GPS routing, plan preservation and return to Places')
