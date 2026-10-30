import {JSDOM} from 'jsdom'
import assert from 'node:assert/strict'
import {places as allPlaces} from '../src/data.js'
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
const places=allPlaces.slice(0,30).map((p,i)=>({...p,like_count:i,comment_count:0,popularity:i}))
localStorage.setItem('perly-saved',JSON.stringify([{id:100,name:'Piesza po jeziorach',description:'Opis spaceru',transport:'walk',place_ids:[1,5]},...[101,102,103,104].map(id=>({id,name:'Rowerowa '+id,description:'Plan na rower',transport:'bike',place_ids:[1,5]})),{id:105,name:'Autem',transport:'car',place_ids:[1]}]))
globalThis.fetch=async path=>{if(path==='/api/places')return {ok:true,json:async()=>places};throw Error('Unexpected '+path)}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
let app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async element=>{assert.ok(element);element.click();await settle()}
const start=()=>[...document.querySelectorAll('.main-navigation button')].find(b=>b.textContent.trim()==='Start')
await settle();await click(start())
assert.match(document.querySelector('#places h2').textContent,/Miejsca TOP 20/)
assert.equal(document.querySelectorAll('#places .place-card').length,20)
assert.equal(document.querySelector('#places .place-title').textContent,places.at(-1).name)
assert.deepEqual([...document.querySelectorAll('.top-place-position')].map(e=>Number(e.textContent)),Array.from({length:20},(_,i)=>i+1))
assert.match(document.querySelector('#home-walking h2').textContent,/Trasy piesze/)
assert.equal(document.querySelectorAll('#home-walking .home-route-card').length,1)
assert.equal(document.querySelectorAll('#home-cycling .home-route-card').length,3)
assert.equal(document.querySelector('#home-cycling .home-route-count').textContent,'4')
assert.equal(document.querySelector('#trails h2').textContent,'Wycieczki.')
assert.equal(document.querySelectorAll('#trails .trail-card').length,3)
await click(document.querySelector('#home-cycling .section-heading>.text-link'))
assert.equal(document.querySelector('.route-library h1').textContent,'Wycieczki rowerowe')
assert.equal(document.querySelectorAll('.route-library-item').length,4)
await click(start());await click(document.querySelector('#home-walking .home-route-card'))
assert.ok(document.querySelector('.planner-layout'))
assert.equal(document.querySelector('.main-navigation button:nth-child(4)').getAttribute('aria-current'),'page')
app.unmount();localStorage.setItem('perly-saved','[]');app=createApp(App);app.mount('#app');await settle();await click(start())
assert.equal(document.querySelectorAll('.home-route-empty').length,2)
assert.equal(document.querySelectorAll('.home-route-card').length,0)
app.unmount();dom.window.close()
console.log('PASS: TOP 20 popularity order and badges, walking/cycling previews and counts, list/planner links, excursions and empty states')
