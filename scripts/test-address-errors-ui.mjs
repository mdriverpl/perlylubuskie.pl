import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/start',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','KeyboardEvent','localStorage'])globalThis[key]=dom.window[key]
Object.defineProperty(globalThis,'navigator',{value:window.navigator,configurable:true})
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
Object.defineProperty(navigator,'geolocation',{value:{getCurrentPosition(success){success({coords:{latitude:52,longitude:15,accuracy:10}})}}})
let body='',status=500,failNetwork=false
globalThis.fetch=async path=>{
 if(path==='/api/places'||path==='/api/routes/public')return {ok:true,json:async()=>[]}
 if(failNetwork)throw new TypeError('Failed to fetch')
 return new Response(body,{status,headers:{'Content-Type':'application/json'}})
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const nav=async label=>{[...document.querySelectorAll('.main-navigation button')].find(el=>(el.dataset.navLabel||el.textContent.trim())===label).click();await settle()}
for(const label of ['Start','Miejsca','Planer']){
 await nav(label)
 const home=label==='Start'
 const input=document.querySelector(home?'#home-address':'#explore-query')
 input.value='Łagów';input.dispatchEvent(new Event('input',{bubbles:true}));await settle()
 const search=async()=>{
  if(home)document.querySelector('.home-address-search form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))
  else input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))
  await settle()
 }
 const error=()=>document.querySelector(home?'.home-address-error':'.location-search-error')
 for(const invalid of ['', '<html>Bad Gateway</html>', '{"items":', 'null', '{}', '{"items":[null]}']){
  body=invalid;status=invalid.startsWith('<')?502:200
  await search();assert.match(error().textContent,/Wyszukiwanie adresów jest chwilowo niedostępne/)
  assert.doesNotMatch(error().textContent,/JSON|Unexpected|SyntaxError/)
 }
 failNetwork=true;await search();assert.match(error().textContent,/Nie udało się połączyć/);failNetwork=false
 body='';status=500
 document.querySelector(home?'[aria-label="Wyszukaj miejsca według GPS"]':'[aria-label="Wpisz adres z GPS"]').click();await settle();await settle()
 assert.match(error().textContent,/Wyszukiwanie adresów jest chwilowo niedostępne/)
 body=JSON.stringify({items:[{id:'address',name:'Łagów, Polska',lat:52.33,lng:15.29}]});status=200
 await search();await settle()
 assert.equal(document.querySelector(home?'.home-address-error':'.location-search-error'),null,'Retry succeeds after invalid responses')
}
app.unmount();dom.window.close()
console.log('PASS: empty/truncated/HTML/null/malformed responses and network errors, GPS reverse failure and successful retry in Start, Places and Planner')
