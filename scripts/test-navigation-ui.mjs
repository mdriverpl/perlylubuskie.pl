import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {viewFromUrl,viewPaths} from '../src/navigation.js'
assert.equal(viewFromUrl('https://example.com/'),'discover')
assert.equal(viewFromUrl('https://example.com/?view=places'),'places')
assert.equal(viewFromUrl('https://example.com/nieznana'),'discover')
for(const [view,path] of Object.entries(viewPaths))assert.equal(viewFromUrl('https://example.com'+path+'/'),view)
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
globalThis.fetch=async()=>({ok:true,json:async()=>[]})
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
let app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const active=()=>document.querySelector('.main-navigation [aria-current="page"]')?.textContent.trim()
const navigate=async text=>{[...document.querySelectorAll('.main-navigation button')].find(el=>el.textContent.trim()===text).click();await settle()}
const history=async direction=>{const done=new Promise(resolve=>window.addEventListener('popstate',resolve,{once:true}));window.history[direction]();await done;await settle()}
await settle()
assert.equal(active(),'Start');assert.equal(window.location.pathname,'/start')
assert.ok(document.querySelector('.hero-search'))
for(const [label,path] of [['Miejsca','/miejsca'],['Planer','/planer'],['Wycieczki piesze','/wycieczki-piesze'],['Wycieczki rowerowe','/wycieczki-rowerowe']]){
 await navigate(label);assert.equal(active(),label);assert.equal(window.location.pathname,path)
}
const length=window.history.length
await navigate('Wycieczki rowerowe');assert.equal(window.history.length,length,'No duplicate history entry for active view')
await history('back');assert.equal(active(),'Wycieczki piesze')
await history('back');assert.equal(active(),'Planer')
await history('forward');assert.equal(active(),'Wycieczki piesze')
assert.equal(window.history.length,length,'History navigation does not push new entries')
app.unmount();app=createApp(App);app.mount('#app');await settle()
assert.equal(active(),'Wycieczki piesze','Reload restores the current URL view')
await navigate('Start');assert.equal(window.location.pathname,'/start')
app.unmount();dom.window.close()
console.log('PASS: Start default, readable URLs, direct links, legacy URLs, reload, back/forward and duplicate history protection')
