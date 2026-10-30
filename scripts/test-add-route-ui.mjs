import {JSDOM} from 'jsdom'
import assert from 'node:assert/strict'
import {demoPlaces as places} from '../src/data.js'
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
localStorage.setItem('perly-user',JSON.stringify({id:1,name:'Tester'}));localStorage.setItem('perly-token','test-token');localStorage.setItem('perly-route','[1,5]')
let fail=true,posts=[]
globalThis.fetch=async(path,options={})=>{
 if(path==='/api/places')return {ok:true,json:async()=>places}
 if(path==='/api/favorites'||path==='/api/routes'&&!options.method)return {ok:true,json:async()=>[]}
 if(path==='/api/routes'&&options.method==='POST'){const body=JSON.parse(options.body);posts.push(body);return {ok:!fail,json:async()=>fail?{detail:'Nie można teraz zapisać trasy.'}:{id:77,...body}}}
 if(path==='/api/routing')return {ok:true,json:async()=>({geometry:{type:'LineString',coordinates:[[15.2922,52.3347],[15.2973,52.3511]]},distance_m:2000,duration_s:1800})}
 throw Error('Unexpected '+path)
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async selector=>{document.querySelector(selector).click();await settle()}
const input=async(selector,value)=>{const el=document.querySelector(selector);el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));await settle()}
await settle();await click('.planned-places-panel>.button')
assert.equal(document.querySelector('.modal h2').textContent,'Dodaj trasę')
assert.equal(document.querySelectorAll('.new-route-type input').length,2)
assert.equal(document.querySelector('.new-route-form button[type=submit]').disabled,false)
assert.equal(document.querySelector('#new-route-name').value,'Łagów')
assert.equal(document.querySelector('#new-route-description').required,false)
assert.equal(document.querySelector('.route-visibility input').checked,true)
const description='<b>Spacer przez las</b>'
await input('#new-route-name','Mój spacer');await input('#new-route-description',description)
await click('.new-route-type input[value=walk]')
const submit=()=>document.querySelector('.new-route-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))
submit();await settle()
assert.match(document.querySelector('.new-route-form [role=alert]').textContent,/Nie można/)
assert.equal(document.querySelector('#new-route-description').value,description)
assert.equal(document.querySelector('#new-route-name').value,'Mój spacer')
fail=false;await input('#new-route-description','');submit();submit();await settle()
assert.equal(posts.length,2)
assert.equal(posts[1].transport,'walk');assert.equal(posts[1].description,'');assert.equal(posts[1].is_public,false);assert.deepEqual(posts[1].place_ids,[1,5])
assert.match(posts[1].cover_image,/^data:image\/webp;base64,/)
assert.equal(document.querySelector('.route-library h1').textContent,'Wycieczki piesze')
assert.match(document.querySelector('.route-library-info small').textContent,/Piesza/)
assert.equal(document.querySelector('.route-library-description').textContent,'Ta trasa nie ma jeszcze opisu.')
assert.equal(document.querySelector('.route-library-description b'),null)
assert.match(document.querySelector('.route-library-open img').getAttribute('src'),/^data:image\/webp;base64,/)
assert.equal(localStorage.getItem('perly-saved'),null)
await click('.route-library-open')
assert.ok(document.querySelector('.planner-layout'))
assert.equal(document.querySelector('.main-navigation button:nth-child(4)').getAttribute('aria-current'),'page')
app.unmount();dom.window.close()
console.log('PASS: route name/description/type form, server save, failure preserves draft, duplicate-submit guard and saved-routes destination')
