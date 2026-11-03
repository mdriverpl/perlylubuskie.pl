import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/miejsca',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
const source='https://palace.example/kontakt'
const place={id:1,name:'Testowy pałac',location:'Łagów',category:'heritage',region:'lubuskie',subtitle:'Pałac',description:'Opis obiektu.',image:'/images/lagow.webp',lat:52.33,lng:15.29,rating:0,details:{kind:'palace',coordinate_source:'https://www.wikidata.org/wiki/Q1',coordinate_license:'Wikidata CC0',sources:[{title:'Źródło opisu',url:'https://palace.example/historia'}],photo:{author:'Autor zdjęcia',source_url:'https://commons.wikimedia.org/wiki/File:Test.jpg',license_url:'https://creativecommons.org/licenses/by-sa/4.0/',license:'CC BY-SA 4.0'},contact:{checked_at:'2026-11-03T10:00:00Z',accommodation:{value:true,source_url:source},restaurant:{value:null,source_url:''},phone:{value:'+48 123 456 789',source_url:source},email:{value:'recepcja@palace.example',source_url:source},website:{value:'https://palace.example/',source_url:source}}}}
globalThis.fetch=async path=>({ok:true,json:async()=>path==='/api/places'?[place]:[]})
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
await settle();await settle()
document.querySelector('.place-title').click();await settle()
const disclosure=document.querySelector('details.heritage-provenance')
assert.ok(disclosure)
assert.equal(disclosure.open,false,'Technical sources are collapsed initially')
assert.equal(disclosure.querySelector('summary').textContent,'Źródła danych')
assert.ok(disclosure.textContent.includes('Autor zdjęcia'))
assert.ok(disclosure.textContent.includes('CC BY-SA 4.0'))
disclosure.querySelector('summary').click();await settle()
assert.equal(disclosure.open,true)
const contact=document.querySelector('.place-contact')
assert.ok(contact.textContent.includes('NoclegDostępny'))
assert.ok(contact.textContent.includes('RestauracjaBrak potwierdzonych informacji'),'Unknown service must not display as unavailable')
assert.equal(contact.querySelector('a[href^="tel:"]').getAttribute('href'),'tel:+48123456789')
assert.equal(contact.querySelector('a[href^="mailto:"]').getAttribute('href'),'mailto:recepcja@palace.example')
assert.equal(contact.querySelector('a[target="_blank"]').href,'https://palace.example/')
assert.ok(disclosure.querySelector('a[href="'+source+'"]'),'Contact evidence stays available in sources')
assert.ok(!disclosure.contains(contact),'Practical contact stays outside collapsed provenance')
app.unmount();dom.window.close()
console.log('PASS: collapsed sources, source toggle, photo attribution, visible contact links and unknown services')
