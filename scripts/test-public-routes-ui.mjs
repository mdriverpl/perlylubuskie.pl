import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {demoPlaces} from '../src/data.js'
import {shortRouteName} from '../src/routeNames.js'
assert.equal(shortRouteName([demoPlaces[0],demoPlaces[4],demoPlaces[2]]),'Łagów')
assert.equal(shortRouteName([demoPlaces[4],demoPlaces[0]]),'Jezioro Trześniowskie')
assert.equal(shortRouteName([{name:'a'.repeat(200)}]).length,120)
assert.equal(shortRouteName([]),'Moja trasa')
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
localStorage.setItem('perly-user',JSON.stringify({id:1,name:'Tester'}));localStorage.setItem('perly-token','test-token')
const own={id:101,name:'Moja prywatna',transport:'bike',place_ids:[1],description:'',is_public:false}
const publicRoute={id:202,name:'Publiczna innego autora',transport:'bike',place_ids:[5],description:'',is_public:true}
let updates=0
globalThis.fetch=async(path,options={})=>{
 let data
 if(path==='/api/places')data=demoPlaces
 else if(path==='/api/favorites')data=[]
 else if(path==='/api/routes')data=[own]
 else if(path==='/api/routes/public')data=[publicRoute]
 else if(path==='/api/routes/101'&&options.method==='PUT'){updates++;Object.assign(own,JSON.parse(options.body));data=own}
 else throw Error('Unexpected '+path)
 return {ok:true,json:async()=>structuredClone(data)}
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async el=>{assert.ok(el);el.click();await settle()}
const nav=[...document.querySelectorAll('.main-navigation button')].find(el=>el.textContent.trim()==='Wycieczki rowerowe')
await settle();await click(nav)
assert.equal(document.querySelectorAll('.route-library-item').length,2)
const other=[...document.querySelectorAll('.route-library-item')].find(el=>el.textContent.includes(publicRoute.name))
assert.equal(other.querySelector('.route-library-delete'),null)
await click(other.querySelector('.route-library-open'))
assert.equal(document.querySelector('.test-drag-point'),null,'Other users cannot edit public route markers')
await click(nav)
await click(document.querySelector('.my-trips-filter input'))
assert.equal(document.querySelectorAll('.route-library-item').length,1)
await click(document.querySelector('.route-library-open'))
await click(document.querySelector('.route-panel > button:last-child'))
const choices=document.querySelectorAll('.modal .route-visibility input')
assert.equal(choices[0].checked,true)
await click(choices[1]);assert.equal(choices[0].checked,false)
await click([...document.querySelectorAll('.modal button')].find(el=>el.textContent==='Zapisz trasę'))
assert.equal(updates,1)
assert.equal(own.is_public,true)
assert.equal(document.querySelectorAll('.route-library-item').length,1,'My routes filter does not duplicate an owned public route')
await click(document.querySelector('.my-trips-filter input'))
assert.equal(document.querySelectorAll('.route-library-item').length,2)
app.unmount();dom.window.close()
console.log('PASS: private/public list, my-routes filtering, public ownership protection, visibility edit updates existing route, default private and short generated names')
