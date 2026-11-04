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
app.unmount()
place.image='/images/lake-maps/test.webp';place.category='nature';place.details.kind='lake'
place.details.map_preview={image:place.image,source_url:'https://www.openstreetmap.org/way/123',geometry_available:true}
const mapApp=createApp(App);mapApp.mount('#app');await settle();await settle()
assert.match(document.querySelector('.map-preview-badge').textContent,/OpenStreetMap/)
document.querySelector('.place-title').click();await settle()
assert.match(document.querySelector('.map-preview-note').textContent,/Podgląd mapy/)
assert.ok(document.querySelector('.provenance-content a[href="https://www.openstreetmap.org/way/123"]'))
assert.ok(!document.querySelector('.provenance-content').textContent.includes('Autor zdjęcia'),'A map crop must not inherit an unrelated photograph credit')
mapApp.unmount()
const Contact=(await import('../artifacts/place-contact-test.mjs')).default
const lakeApp=createApp(Contact,{lakeInfo:{
 swimming:{status:'unknown',explanation:'Brak aktualnych danych.'},
 motorboats:{status:'no',explanation:'Zakaz silników spalinowych.',source_url:'https://official.example/regulamin'},
 beach:{status:'yes',explanation:'<b>Wyznaczona plaża</b>',source_url:'javascript:alert(1)'}
}});lakeApp.mount('#app');await settle()
const lake=document.querySelector('.lake-info')
assert.ok(lake.textContent.includes('KąpielBrak potwierdzonych informacji'))
assert.ok(lake.textContent.includes('MotorówkiNie'))
assert.equal(lake.querySelectorAll('a').length,1,'Only HTTPS evidence links are shown')
assert.equal(lake.querySelector('b'),null,'Lake explanations are escaped')
lakeApp.unmount();dom.window.close()
console.log('PASS: collapsed sources, source toggle, photo attribution, visible contact links and unknown services')
