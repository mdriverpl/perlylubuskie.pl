import {JSDOM} from 'jsdom'
import assert from 'node:assert/strict'
import {demoPlaces} from '../src/data.js'
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
localStorage.setItem('perly-user',JSON.stringify({id:1,name:'Odkrywca'}));localStorage.setItem('perly-token','test-token')
const places=demoPlaces.map(p=>({...p,like_count:p.id===1?2:0,comment_count:p.id===2?4:0,popularity:p.id===1?2:p.id===2?4:0,liked:false}))
let comments=[],fail=false
const response=(data,status=200)=>({ok:status<400,status,json:async()=>structuredClone(data)})
globalThis.fetch=async(path,options={})=>{
 if(path==='/api/places')return response(places)
 if(path==='/api/favorites'||path==='/api/routes')return response([])
 const p=places[0]
 if(path==='/api/places/1/like'){
  if(fail)return response({detail:'Nie udało się zapisać polubienia.'},503)
  const liked=options.method==='PUT';if(liked!==p.liked)p.like_count+=liked?1:-1;p.liked=liked;p.popularity=p.like_count+p.comment_count;return response(p)
 }
 if(path.startsWith('/api/places/1/community'))return response({...p,visit_count:0,visited:false,comments})
 if(path==='/api/places/1/comments'&&options.method==='POST'){
  const c={id:comments.length+1,body:JSON.parse(options.body).body,author:'Odkrywca',created_at:new Date().toISOString(),can_delete:true};comments.unshift(c);p.comment_count=comments.length;p.popularity=p.like_count+p.comment_count;return response(c,201)
 }
 throw Error('Unexpected '+path)
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async selector=>{document.querySelector(selector).click();await settle()}
await settle();await click('[aria-label="Widok kafelków"]')
const sorting=document.querySelector('[aria-label="Sortuj miejsca"]');sorting.value='recommended';sorting.dispatchEvent(new Event('change',{bubbles:true}));await settle()
assert.equal(document.querySelector('.explore-place .place-title').textContent,'Park Mużakowski')
assert.ok(document.querySelector('[aria-label="Dodaj do ulubionych: Łagów"]').title.includes('prywatne'))
await click('[aria-label="Polub: Łagów"]')
assert.equal(document.querySelector('[aria-label="Cofnij polubienie: Łagów"]').textContent.trim(),'3')
await click('[aria-label="Komentarze: Łagów"]')
assert.equal(document.querySelector('.place-like-button').getAttribute('aria-pressed'),'true')
await click('.comments-toggle')
for(let i=0;i<2;i++){
 const field=document.querySelector('.comment-form textarea');field.value='Moja opinia '+i;field.dispatchEvent(new Event('input',{bubbles:true}));await settle()
 document.querySelector('.comment-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await settle();await settle()
}
await click('[aria-label="Zamknij okno"]')
assert.equal(document.querySelector('.explore-place .place-title').textContent,'Łagów')
assert.equal(document.querySelector('[aria-label="Komentarze: Łagów"]').textContent.trim(),'2')
await click('[aria-label="Cofnij polubienie: Łagów"]')
assert.equal(document.querySelector('[aria-label="Polub: Łagów"]').textContent.trim(),'2')
fail=true;await click('[aria-label="Polub: Łagów"]')
assert.equal(document.querySelector('[aria-label="Polub: Łagów"]').textContent.trim(),'2')
assert.match(document.querySelector('.toast-message').textContent,/Nie udało/)
app.unmount();dom.window.close()
console.log('PASS: public likes, private favorites labels, undo/error handling, comment counters and live popularity order')
