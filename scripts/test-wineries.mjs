import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import {JSDOM} from 'jsdom'
import {places} from '../src/data.js'
import {filterPlaces} from '../src/explore.js'
const catalog=JSON.parse(await fs.readFile('src/catalog/wineries.json','utf8'))
const seed=JSON.parse(await fs.readFile('backend/seed.json','utf8'))
assert.deepEqual(seed,places)
assert.equal(catalog.length,30)
assert.equal(filterPlaces(places,'lubuskie','',['wineries']).length,30)
assert.ok(filterPlaces(places,'lubuskie','Łaz',['wineries']).some(p=>p.name==='Winnica Ingrid'))
assert.ok(filterPlaces(places,'lubuskie','Zabór',['wineries']).some(p=>p.name==='Winnica Międzypole'))
assert.equal(new Set(places.map(p=>p.id)).size,places.length)
for(const p of catalog){
 assert.ok(p.id>=900001&&p.id<=900030)
 assert.equal(p.category,'vineyard')
 assert.ok(p.lat>51.7&&p.lat<52.2&&p.lng>15.3&&p.lng<15.9,p.name)
 assert.ok(p.description.length>=50&&p.description.length<=2000)
 assert.ok(p.details.sources.length>=2)
 assert.ok(p.details.sources.every(s=>new URL(s.url).protocol==='https:'))
 await fs.access('public'+p.image)
 if(p.details.coordinate_accuracy==='street'||p.details.coordinate_accuracy==='complex-reference')assert.ok(p.details.location_note)
}
assert.equal(catalog.find(p=>p.name==='Winnica Jany').details.coordinate_accuracy,'address-building')
assert.equal(catalog.find(p=>p.id===900030).details.coordinate_accuracy,'complex-reference')
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
globalThis.fetch=async path=>({ok:true,json:async()=>path==='/api/places'?places:{like_count:0,liked:false,visit_count:0,visited:false,comment_count:0,comments:[]}})
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
await settle();document.querySelector('.compact-clear-filters').click();await settle();document.querySelector('input[value="wineries"]').click();await settle()
assert.equal(document.querySelector('.test-explore-map').dataset.ids.split(',').length,30)
document.querySelector('[aria-label="Widok kafelków"]').click();await settle()
assert.equal(document.querySelectorAll('.explore-place').length,30)
assert.ok([...document.querySelectorAll('.place-tag')].every(p=>p.textContent==='Winnice'))
const titles=[...document.querySelectorAll('.place-title')]
titles.find(p=>p.textContent==='Winnica Słone').click();await settle()
assert.match(document.querySelector('.heritage-provenance').textContent,/Lokalizacja orientacyjna/)
assert.match(new URL(document.querySelector('.google-maps-link').href).searchParams.get('query'),/Słoneczna 69/)
assert.ok(document.querySelector('.heritage-provenance a[href="https://winnicaslone.pl/"]'))
app.unmount();dom.window.close()
console.log('PASS: 30 sourced wine-related points, stable IDs, winery filter/map/cards, source details and approximate-location directions')
