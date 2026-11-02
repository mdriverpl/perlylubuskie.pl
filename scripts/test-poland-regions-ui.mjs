import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/start',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
const allowed_types=['castle','palace','lake','nature','heritage','leisure']
const regions=[{slug:'lubuskie',name:'Lubuskie',place_count:351,active:true,allowed_types},{slug:'dolnoslaskie',name:'Dolnośląskie',place_count:506,active:true,allowed_types},{slug:'kujawsko-pomorskie',name:'Kujawsko-pomorskie',place_count:255,active:true,allowed_types}]
const places=regions.map((r,i)=>({id:i+1,region:r.slug,name:r.name+' — test',description:'Opis',subtitle:'Atrakcja',location:r.name,category:'heritage',details:{kind:'castle'},image:'/images/heritage-placeholder.svg',lat:53,lng:18,rating:0}))
const routes=[{id:10,name:'Publiczny spacer',is_public:true,transport:'walk',place_ids:[1,1,2]},{id:11,name:'Publiczna rowerowa',is_public:true,transport:'bike',place_ids:[3]}]
localStorage.setItem('perly-saved',JSON.stringify([{id:99,name:'Prywatna',transport:'walk',place_ids:[1]}]))
let geocoderRequests=0
globalThis.fetch=async path=>{
 if(path.startsWith('/api/maps/search'))geocoderRequests++
 const data=path==='/api/regions'?regions:path==='/api/places'?places:path==='/api/routes/public'?routes:[]
 return {ok:true,json:async()=>structuredClone(data)}
}
const {createApp,nextTick}=await import('vue')
await import('../artifacts/poland-regions-test.mjs')
const App=(await import('../artifacts/ui-test.mjs')).default
let app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
await settle();await settle();await settle()
assert.equal(document.querySelector('#poland-regions'),null,'Map starts in the second hero tab')
document.querySelector('#hero-tab-map').click();await settle();await settle();await settle()
const map=document.querySelector('#poland-regions');assert.ok(map)
assert.ok(document.querySelector('.hero-ai-panel').contains(map),'Map lives inside the hero panel')
assert.equal(document.querySelectorAll('#poland-regions').length,1,'No duplicate map below the hero')
assert.ok(map.compareDocumentPosition(document.querySelector('#places'))&Node.DOCUMENT_POSITION_FOLLOWING,'Map appears before TOP 20')
assert.equal(map.querySelectorAll('.poland-province>path').length,16)
assert.equal(map.querySelectorAll('.poland-region-rows button').length,16)
assert.equal(map.querySelector('.poland-total strong').textContent.replace(/\s/g,''),'1112')
const province=slug=>map.querySelector(`[data-region="${slug}"]`)
assert.match(province('lubuskie').getAttribute('aria-label'),/351 miejsc, 1 trasa piesza, 0 tras rowerowych/)
assert.match(province('kujawsko-pomorskie').getAttribute('aria-label'),/255 miejsc, 0 tras pieszych, 1 trasa rowerowa/)
assert.equal(province('podlaskie').getAttribute('aria-disabled'),'true')
province('podlaskie').dispatchEvent(new Event('click',{bubbles:true}));await settle();assert.equal(window.location.pathname,'/start')
const list=map.querySelector('.poland-region-list');assert.equal(list.open,false);list.querySelector('summary').click();await settle();assert.equal(list.open,true)
province('kujawsko-pomorskie').dispatchEvent(new window.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));await settle();await settle()
assert.equal(window.location.pathname,'/miejsca');assert.equal(JSON.parse(localStorage.getItem('perly:region')),'kujawsko-pomorskie')
assert.equal(document.querySelector('.place-title').textContent,'Kujawsko-pomorskie — test')
assert.equal(document.querySelector('#poland-regions'),null)
assert.equal(document.querySelector('#active-region'),null,'Places has no province dropdown')
await typeProvince('cała Polska');assert.equal(document.querySelectorAll('.explore-place').length,3)
await typeProvince('Dolnośląskie');assert.equal(document.querySelectorAll('.explore-place').length,1)
assert.equal(document.querySelector('.place-title').textContent,'Dolnośląskie — test')
assert.equal(JSON.parse(localStorage.getItem('perly:region')),'dolnoslaskie')
app.unmount();app=createApp(App);app.mount('#app');await settle();await settle()
assert.equal(JSON.parse(localStorage.getItem('perly:region')),'dolnoslaskie','Province selection survives reload')
assert.equal(document.querySelector('.place-title').textContent,'Dolnośląskie — test')
async function typeProvince(text,automatic=false){
 const field=document.querySelector('#explore-query');field.value=text;field.dispatchEvent(new Event('input',{bubbles:true}));await settle()
 if(automatic)await new Promise(r=>setTimeout(r,650))
 else field.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}))
 await settle();await settle()
}
await typeProvince('województwo kujawsko pomorskie')
assert.equal(JSON.parse(localStorage.getItem('perly:region')),'kujawsko-pomorskie')
assert.equal(document.querySelector('#explore-query').value,'')
assert.equal(document.querySelector('.place-title').textContent,'Kujawsko-pomorskie — test')
await typeProvince('LUBUSKIE',true)
assert.equal(JSON.parse(localStorage.getItem('perly:region')),'lubuskie','Province is also recognized automatically after typing')
await typeProvince('podlaskie')
assert.equal(JSON.parse(localStorage.getItem('perly:region')),'lubuskie','Unavailable provinces do not select a different catalog silently')
assert.match(document.querySelector('.location-search-error').textContent,/nie ma jeszcze opublikowanego katalogu/)
assert.equal(geocoderRequests,0,'Province selection must not invoke the address geocoder')
app.unmount();dom.window.close()
console.log('PASS: map before TOP 20, 16 outlines, published place/public route counts, no private route leakage, readable list and keyboard catalog navigation')
