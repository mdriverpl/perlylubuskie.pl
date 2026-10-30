import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import { JSDOM } from 'jsdom'
import { places } from '../src/data.js'
import { filterPlaces } from '../src/explore.js'
const records=JSON.parse(await fs.readFile('data/heritage/source-records.json','utf8'))
const seed=JSON.parse(await fs.readFile('backend/seed.json','utf8'))
assert.deepEqual(seed,places)
assert.equal(records.length,175)
assert.equal(places.length,351)
assert.equal(new Set(places.map(p=>p.id)).size,places.length)
assert.equal(filterPlaces(places,'lubuskie','',['castles']).length,24)
assert.equal(filterPlaces(places,'lubuskie','',['palaces']).length,151)
for(const p of places.filter(p=>p.details?.wikidata)){
 assert.ok(p.lat>51.3&&p.lat<53.1&&p.lng>14.4&&p.lng<16.5,p.name)
 assert.ok(p.description.length>30&&p.description.length<=2000,p.name)
 assert.ok(p.details.sources.every(s=>new URL(s.url).protocol==='https:'))
 if(p.details.photo){assert.ok(p.details.photo.author);assert.match(p.details.photo.license,/CC|Public domain|PDM/);assert.equal(new URL(p.details.photo.source_url).hostname,'commons.wikimedia.org')}
 if(p.image.startsWith('/'))await fs.access('public'+p.image)
}
const dom=new JSDOM('<!doctype html><div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
globalThis.fetch=async path=>({ok:true,json:async()=>path==='/api/places'?places:{visit_count:0,visited:false,comment_count:0,comments:[]}})
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
await settle()
document.querySelector('.compact-clear-filters').click();await settle()
document.querySelector('[aria-label="Widok kafelków"]').click();await settle()
assert.equal(document.querySelectorAll('.explore-place').length,351)
const palace=document.querySelector('input[value="palaces"]');palace.click();await settle()
assert.equal(document.querySelectorAll('.explore-place').length,151)
const photographed=places.find(p=>p.details?.kind==='palace'&&p.details.photo)
;[...document.querySelectorAll('.explore-place .place-title')].find(el=>el.textContent===photographed.name).click();await settle()
assert.match(document.querySelector('.heritage-provenance').textContent,/Współrzędne:/)
assert.ok(document.querySelector('.heritage-provenance a[href*="wikidata.org"]'))
assert.ok(document.querySelector('.heritage-provenance a[href*="commons.wikimedia.org"]'))
const image=document.querySelector('.detail-image');image.dispatchEvent(new Event('error'));assert.match(image.src,/heritage-placeholder.svg$/)
assert.ok(document.querySelector('a[href="/heritage-credits.html"]'))
app.unmount();dom.window.close()
console.log('PASS: 175 sourced objects, stable IDs, seed parity, coordinates, photo attribution, palace filter, preview and image fallback')
