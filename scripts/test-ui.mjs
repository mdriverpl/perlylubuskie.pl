// Component tests in jsdom; map tiles and visual layout require a real browser.
import { JSDOM } from 'jsdom'
import { parse, compileScript } from '@vue/compiler-sfc'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import assert from 'node:assert/strict'
const dom = new JSDOM('<!doctype html><html><body><div id="app"></div></body></html>', { url: 'http://localhost', pretendToBeVisual: true })
for (const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage','MutationObserver']) globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{}
Element.prototype.scrollIntoView=()=>{}
globalThis.fetch=async()=>{throw new Error('Offline test')}
const { createApp, nextTick }=await import('vue')
const { descriptor }=parse(await readFile('src/App.vue','utf8'))
const compiled=compileScript(descriptor,{id:'test-app',inlineTemplate:true})
const source=compiled.content.replace("from './data'","from '../src/data.js'").replace("import TravelMap from './components/TravelMap.vue'","const TravelMap = { template: '<div>Map stub</div>' }")
await mkdir('artifacts',{recursive:true})
await writeFile('artifacts/ui-test.mjs',source)
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const button=(text)=>[...document.querySelectorAll('button')].find(b=>b.textContent.includes(text))
const click=async(el)=>{assert.ok(el,'Element exists');el.click();await settle()}
await settle()
assert.equal(document.querySelectorAll('.place-card').length,4)
await click(document.querySelector('[aria-label="Dodaj do ulubionych: Łagów"]'))
assert.deepEqual(JSON.parse(localStorage.getItem('perly-favorites')),[1])
await click(document.querySelector('[aria-label="Ulubione miejsca"]'))
assert.equal(document.querySelectorAll('.place-card').length,1)
await click(button('Odkrywaj'))
const search=document.querySelector('.hero-search input');search.value='nieistniejące miejsce';search.dispatchEvent(new Event('input',{bubbles:true}));await settle()
assert.ok(document.querySelector('.empty-state'))
await click(button('Wyczyść filtry'))
assert.equal(document.querySelectorAll('.place-card').length,4)
await click(button('Mapa i trasy'))
assert.equal(document.querySelectorAll('.route-stop').length,3)
await click(document.querySelector('[aria-label="Przesuń Łagów niżej"]'))
assert.equal(document.querySelector('.route-stop strong').textContent,'Jezioro Trześniowskie')
await click(button('Zapisz plan wycieczki'))
await click(document.querySelector('.modal .full-width'))
assert.equal(JSON.parse(localStorage.getItem('perly-saved')).length,1)
await click(button('Resetuj'))
assert.equal(document.querySelectorAll('.route-stop').length,0)
assert.equal(button('Pobierz plan').disabled,true)
await click(button('Zapisane plany'))
await click(button('Moja lubuska przygoda'))
assert.equal(document.querySelectorAll('.route-stop').length,3)
let exportedBlob
URL.createObjectURL=blob=>{exportedBlob=blob;return 'blob:test'}
URL.revokeObjectURL=()=>{}
dom.window.HTMLAnchorElement.prototype.click=()=>{}
await click(button('Pobierz plan'))
const gpx=new dom.window.DOMParser().parseFromString(await exportedBlob.text(),'text/xml')
assert.equal(gpx.querySelector('parsererror'),null)
assert.equal(gpx.querySelectorAll('rtept').length,3)
assert.equal(gpx.querySelector('rtept name').textContent,'Jezioro Trześniowskie')
await click(button('Odkrywaj'))
await click(document.querySelector('.place-title'))
assert.ok(document.querySelector('[role="dialog"]'))
document.querySelector('.modal').dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));await settle()
assert.equal(document.querySelector('[role="dialog"]'),null)
app.unmount()
dom.window.close()
console.log('PASS: catalog, favorites, search/empty state, route ordering, local save/restore, GPX export/order, disabled export, modal keyboard close')
