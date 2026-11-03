// Component tests in jsdom; map tiles and visual layout require a real browser.
import { JSDOM } from 'jsdom'
import { parse, compileScript } from '@vue/compiler-sfc'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import assert from 'node:assert/strict'
const dom = new JSDOM('<!doctype html><html><body><div id="app"></div></body></html>', { url: 'http://localhost/planer', pretendToBeVisual: true })
for (const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage','MutationObserver']) globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{}
Element.prototype.scrollIntoView=()=>{}
globalThis.fetch=async()=>{throw new Error('Offline test')}
const { createApp, nextTick }=await import('vue')
const { descriptor }=parse(await readFile('src/App.vue','utf8'))
const compiled=compileScript(descriptor,{id:'test-app',inlineTemplate:true})
const source=compiled.content.replace("from './apiResponse.js'","from '../src/apiResponse.js'").replace('places as initialPlaces','demoPlaces as initialPlaces').replace("from './data'","from '../src/data.js'").replace("from './useGeolocation.js'","from '../src/useGeolocation.js'").replace("from './useRouting.js'","from '../src/useRouting.js'").replace("from './useTripMetrics.js'","from '../src/useTripMetrics.js'").replace("from './rememberedAddress.js'","from '../src/rememberedAddress.js'").replace("from './navigation.js'","from '../src/navigation.js'").replace("from './customPoints.js'","from '../src/customPoints.js'").replace("from './explore.js'","from '../src/explore.js'").replace("from './routeNames.js'","from '../src/routeNames.js'").replace("from './components/PlaceCommunity.vue'","from './community-test.mjs'").replace("from './components/ExploreHome.vue'","from './explore-test.mjs'").replace("import TravelMap from './components/TravelMap.vue'","const TravelMap = { template: '<div>Map stub</div>' }")
await mkdir('artifacts',{recursive:true})
const brandMark=parse(await readFile('src/components/BrandMark.vue','utf8')).descriptor
await writeFile('artifacts/brand-mark-test.mjs',compileScript(brandMark,{id:'test-brand',inlineTemplate:true}).content)
const poland=parse(await readFile('src/components/PolandRegions.vue','utf8')).descriptor
await writeFile('artifacts/poland-regions-test.mjs',compileScript(poland,{id:'test-poland',inlineTemplate:true}).content.replace("from '../regionOverview.js'","from '../src/regionOverview.js'"))
const research=parse(await readFile('src/components/RegionResearch.vue','utf8')).descriptor
await writeFile('artifacts/region-research-test.mjs',compileScript(research,{id:'test-research',inlineTemplate:true}).content.replace("from '../apiResponse.js'","from '../src/apiResponse.js'"))
const adminRegions=parse(await readFile('src/components/AdminRegions.vue','utf8')).descriptor
await writeFile('artifacts/admin-regions-test.mjs',compileScript(adminRegions,{id:'test-admin-regions',inlineTemplate:true}).content.replace("from './RegionResearch.vue'","from './region-research-test.mjs'").replace("from '../apiResponse.js'","from '../src/apiResponse.js'"))
const homeAddress=parse(await readFile('src/components/HomeAddressSearch.vue','utf8')).descriptor
await writeFile('artifacts/home-address-test.mjs',compileScript(homeAddress,{id:'test-home-address',inlineTemplate:true}).content.replaceAll("from '../useGeolocation.js'","from '../src/useGeolocation.js'").replaceAll("from '../useLocationSearch.js'","from '../src/useLocationSearch.js'").replaceAll("from '../rememberedAddress.js'","from '../src/rememberedAddress.js'"))
const pwa=parse(await readFile('src/components/PwaControls.vue','utf8')).descriptor
await writeFile('artifacts/pwa-test.mjs',compileScript(pwa,{id:'test-pwa',inlineTemplate:true}).content)
const addPlace=parse(await readFile('src/components/AddPlaceForm.vue','utf8')).descriptor
await writeFile('artifacts/add-place-test.mjs',compileScript(addPlace,{id:'test-add-place',inlineTemplate:true}).content)
const community=parse(await readFile('src/components/PlaceCommunity.vue','utf8')).descriptor
await writeFile('artifacts/community-test.mjs',compileScript(community,{id:'test-community',inlineTemplate:true}).content.replace("from '../apiResponse.js'","from '../src/apiResponse.js'"))
const navigationComponent=parse(await readFile('src/components/TripNavigation.vue','utf8')).descriptor
const explore=parse(await readFile('src/components/ExploreHome.vue','utf8')).descriptor
const mapStubTemplate=`<div class="test-explore-map" :data-focus-lat="focusLocation?.lat" :data-focus-lng="focusLocation?.lng" :data-geometry="JSON.stringify(geometry)" :data-approximate="geometryApproximate" :data-ids="places.map(p=>p.id).join(',')" :data-user-lat="userLocation?.lat" :data-search-lat="searchLocation?.lat"><button v-for="place in places" :key="place.id" @click="$emit('select',place.id)">Map: {{place.name}}</button><button v-if="draggablePoints" class="test-drag-point" @click="$emit('move-point',{id:places[0].id,lat:52.12,lng:15.31})">Przesuń punkt</button><button v-if="allowCustomPoints" class="test-map-doubleclick" @click="$emit('create-point',{lat:52.1,lng:15.3})">Double click map</button></div>`
const mapStub=`const TravelMap = {props:{places:Array,focusLocation:Object,draggablePoints:Boolean,geometry:Object,geometryApproximate:Boolean,userLocation:Object,searchLocation:Object,allowCustomPoints:Boolean},emits:['select','create-point','move-point'],template:${JSON.stringify(mapStubTemplate)}}`
const ai=parse(await readFile('src/components/AiPlanner.vue','utf8')).descriptor
await writeFile('artifacts/ai-test.mjs',compileScript(ai,{id:'test-ai',inlineTemplate:true}).content.replace("from '../apiResponse.js'","from '../src/apiResponse.js'").replace("import TravelMap from './TravelMap.vue'",mapStub).replace("from '../routeShare.js'","from '../src/routeShare.js'"))
await writeFile('artifacts/trip-navigation-test.mjs',compileScript(navigationComponent,{id:'test-navigation-screen',inlineTemplate:true}).content.replace("import TravelMap from './TravelMap.vue'",mapStub))
const exploreSource=compileScript(explore,{id:'test-explore',inlineTemplate:true}).content.replace("from '../explore.js'","from '../src/explore.js'").replace("from '../useGeolocation.js'","from '../src/useGeolocation.js'").replace("from '../useLocationSearch.js'","from '../src/useLocationSearch.js'").replace("from '../rememberedAddress.js'","from '../src/rememberedAddress.js'").replace("import TravelMap from './TravelMap.vue'",mapStub)
await writeFile('artifacts/explore-test.mjs',exploreSource)
await writeFile('artifacts/ui-test.mjs',source.replace("from './components/BrandMark.vue'","from './brand-mark-test.mjs'").replace("from './components/TripNavigation.vue'","from './trip-navigation-test.mjs'").replace("from './components/AdminRegions.vue'","from './admin-regions-test.mjs'").replace("import('./components/PolandRegions.vue')","import('./poland-regions-test.mjs')").replace("from './components/HomeAddressSearch.vue'","from './home-address-test.mjs'").replace("from './components/AiPlanner.vue'","from './ai-test.mjs'").replace("from './components/PwaControls.vue'","from './pwa-test.mjs'").replace("from './components/AddPlaceForm.vue'","from './add-place-test.mjs'").replace("const TravelMap = { template: '<div>Map stub</div>' }",mapStub).replace("import { createRouteCover } from './routeCover.js'", "const createRouteCover=async()=>{if(globalThis.failRouteCover)throw Error('Nie udało się pobrać mapy do zdjęcia.');return 'data:image/webp;base64,UklGRg=='}"))
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const button=(text)=>[...document.querySelectorAll('button')].find(b=>b.textContent.includes(text))
const click=async(el)=>{assert.ok(el,'Element exists');el.click();await settle()}
await settle()
assert.deepEqual([...document.querySelectorAll('.main-navigation button')].map(b=>(b.dataset.navLabel||b.textContent.trim())),['Start','Miejsca','Planer','Wycieczki'])
assert.equal(document.querySelectorAll('.main-navigation button svg').length,4)
await click(button('Start'))
assert.equal(document.querySelectorAll('.place-card').length,6)
await click(document.querySelector('[aria-label="Dodaj do ulubionych: Łagów"]'))
assert.deepEqual(JSON.parse(localStorage.getItem('perly-favorites')),[1])
await click(document.querySelector('[aria-label="Ulubione miejsca"]'))
assert.equal(document.querySelectorAll('.place-card').length,1)
await click(button('Start'))
const search=document.querySelector('.hero-search input');search.value='Zaplanuj dzień w Łagowie';search.dispatchEvent(new Event('input',{bubbles:true}));await settle()
assert.equal(document.querySelector('.ai-planner'),null,'Typing alone does not submit an AI request')
assert.equal(document.querySelectorAll('.place-card').length,6)
await click(button('Zaplanuj wycieczkę'))
assert.equal(document.querySelectorAll('.route-stop').length,3)
await click(document.querySelector('[aria-label="Przesuń Łagów niżej"]'))
assert.equal(document.querySelector('.route-stop strong').textContent,'Jezioro Trześniowskie')
await click(button('Zapisz trasę'))
await click(document.querySelector('.modal .full-width'))
assert.equal(JSON.parse(localStorage.getItem('perly-saved')).length,1)
await click(button('Resetuj'))
assert.equal(document.querySelectorAll('.route-stop').length,0)
assert.equal(button('Pobierz punkty').disabled,true)
await click(button('Zapisane plany'))
await click(button('Moja lubuska przygoda'))
assert.equal(document.querySelectorAll('.route-stop').length,3)
let exportedBlob
URL.createObjectURL=blob=>{exportedBlob=blob;return 'blob:test'}
URL.revokeObjectURL=()=>{}
dom.window.HTMLAnchorElement.prototype.click=()=>{}
await click(button('Pobierz punkty'))
const gpx=new dom.window.DOMParser().parseFromString(await exportedBlob.text(),'text/xml')
assert.equal(gpx.querySelector('parsererror'),null)
assert.equal(gpx.querySelectorAll('rtept').length,3)
assert.equal(gpx.querySelector('rtept name').textContent,'Jezioro Trześniowskie')
await click(button('Start'))
await click(document.querySelector('.place-title'))
assert.ok(document.querySelector('[role="dialog"]'))
document.querySelector('.modal').dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));await settle()
assert.equal(document.querySelector('[role="dialog"]'),null)
app.unmount()
dom.window.close()
console.log('PASS: catalog, favorites, search/empty state, route ordering, local save/restore, GPX export/order, disabled export, modal keyboard close')

