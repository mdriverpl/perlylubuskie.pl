import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {demoPlaces} from '../src/data.js'
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
localStorage.setItem('perly-user',JSON.stringify({id:1,name:'Tester'}));localStorage.setItem('perly-token','test-token');localStorage.setItem('perly-route','[1,5]')
let fail=true,created,posts=0
globalThis.fetch=async(path,options={})=>{
 if(path==='/api/places'&&options.method==='POST'){
  posts++;const data=JSON.parse(options.body)
  created={...data,id:1000000000,category:'heritage',details:{kind:data.place_type},image:data.image||'/images/heritage-placeholder.svg',rating:0,like_count:0,comment_count:0}
  return {ok:!fail,json:async()=>fail?{detail:'Nie można zapisać miejsca.'}:created}
 }
 if(path==='/api/places')return {ok:true,json:async()=>demoPlaces}
 if(path==='/api/favorites'||path==='/api/routes')return {ok:true,json:async()=>[]}
 if(path.includes('/community'))return {ok:true,json:async()=>({visit_count:0,visited:false,comment_count:0,like_count:0,liked:false,comments:[]})}
 throw Error('Unexpected '+path)
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async el=>{assert.ok(el);el.click();await settle()}
const nav=name=>[...document.querySelectorAll('.main-navigation button')].find(el=>el.textContent.trim()===name)
const input=async(selector,value)=>{const el=document.querySelector(selector);el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));await settle()}
await settle();assert.ok(document.querySelector('.planned-places-panel'))
await click(nav('Miejsca'))
await click(document.querySelector('.compact-clear-filters'))
assert.equal(document.querySelector('.planned-places-panel'),null)
assert.ok(document.querySelector('.catalog-content-layout'))
assert.equal(document.querySelectorAll('.explore-place').length,6)
assert.ok(document.querySelector('.facet-list'))
await click(document.querySelector('input[value="castles"]'))
assert.equal(document.querySelectorAll('.explore-place').length,1)
await click(document.querySelector('[aria-label="Widok listy"]'))
assert.equal(document.querySelectorAll('.explore-list .explore-place').length,1)
await click(document.querySelector('[aria-label="Widok mapy"]'))
assert.equal(document.querySelector('.test-explore-map').dataset.ids,'1')
assert.equal(document.querySelector('.test-map-doubleclick'),null,'Catalog does not create route points')
await click(document.querySelector('.compact-clear-filters'))
await click(document.querySelector('.create-place-button'))
await input('#new-place-name','Pałac <b>Nowy</b>');await input('#new-place-location','Zabór');await input('#new-place-description','Opis nowego miejsca');await input('#new-place-lat','51.95');await input('#new-place-lng','15.7')
const type=document.querySelector('#new-place-type');type.value='palace';type.dispatchEvent(new Event('change',{bubbles:true}));await settle()
const submit=()=>document.querySelector('.add-place-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))
submit();await settle();assert.match(document.querySelector('.add-place-form [role=alert]').textContent,/Nie można/)
assert.equal(document.querySelector('#new-place-name').value,'Pałac <b>Nowy</b>')
fail=false;submit();submit();await settle()
assert.equal(posts,2,'Double submission is blocked')
assert.ok(document.querySelector('.place-community'),'Created place supports comments and likes')
assert.equal(document.querySelector('.modal h2').textContent,'Pałac <b>Nowy</b>')
assert.equal(document.querySelector('.modal h2 b'),null)
await click(document.querySelector('[aria-label="Zamknij okno"]'))
await click(document.querySelector('[aria-label="Widok kafelków"]'))
assert.equal(document.querySelectorAll('.explore-place').length,7)
assert.equal(localStorage.getItem('perly-route'),'[1,5]','Adding a place does not add a waypoint to the route')
await click(nav('Planer'))
assert.ok(document.querySelector('.planned-places-panel'))
assert.equal(document.querySelector('.create-place-button'),null)
await click(nav('Miejsca'))
const firstName=document.querySelector('.place-title').textContent
const firstPlace=demoPlaces.find(p=>p.name===firstName)
await click(document.querySelector('.add-place-to-list'))
assert.ok(document.querySelector('.planned-places-panel'))
assert.equal(document.querySelector('[aria-label="Widok mapy"]').getAttribute('aria-pressed'),'true')
assert.equal(document.querySelector('.test-explore-map').dataset.focusLat,String(firstPlace.lat))
assert.equal(document.querySelector('.test-explore-map').dataset.focusLng,String(firstPlace.lng))
await input('#explore-query','Łagów')
assert.ok(Math.abs(Number(document.querySelector('.test-explore-map').dataset.focusLat)-52.3429)<.00001,'Town search replaces the initial place focus with the town center')
app.unmount();dom.window.close()
console.log('PASS: separate Planer/catalog, filters and three views, no route points in catalog, add-place validation/retry, escaping and community support')
