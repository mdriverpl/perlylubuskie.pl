import { JSDOM } from 'jsdom'
import assert from 'node:assert/strict'
import { places } from '../src/data.js'
const dom=new JSDOM('<!doctype html><div id="app"></div>',{url:'http://localhost',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
let visited=false, comments=[], failPost=false
const response=(data,status=200)=>({ok:status<400,status,json:async()=>data})
globalThis.fetch=async(path,options={})=>{
 if(path==='/api/places')return response(places)
 if(path==='/api/auth/login')return response({access_token:'test-token',user:{id:1,name:'Odkrywca',email:'test@example.com'}})
 if(path==='/api/favorites'||path==='/api/routes')return response([])
 if(path.startsWith('/api/places/1/community'))return response({visit_count:visited?1:0,visited,comment_count:comments.length,comments:[...comments]})
 if(path==='/api/places/1/visit'){visited=options.method==='PUT';return response(null,204)}
 if(path==='/api/places/1/comments'&&options.method==='POST'){
  if(failPost)return response({detail:'Spróbuj później.'},429)
  const comment={id:1,body:JSON.parse(options.body).body,author:'Odkrywca',created_at:new Date().toISOString(),can_delete:true};comments.unshift(comment);return response(comment,201)
 }
 if(path==='/api/places/1/comments/1'&&options.method==='DELETE'){comments=[];return response(null,204)}
 throw Error('Unexpected request '+path)
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const button=text=>[...document.querySelectorAll('button')].find(b=>b.textContent.includes(text))
const click=async el=>{assert.ok(el);el.click();await settle()}
await settle();await click(document.querySelector('.place-title'))
const link=document.querySelector('.google-maps-link')
assert.equal(new URL(link.href).searchParams.get('query'),'52.3347,15.2922')
assert.equal(link.target,'_blank');assert.ok(link.rel.includes('noopener'))
assert.equal(document.querySelector('.visit-total strong').textContent,'0')
assert.ok(document.querySelector('.community-login'))
assert.equal(document.querySelector('.comment-form'),null)
await click(button('Byłem tu'))
assert.ok(document.querySelector('.auth-body'))
const email=document.querySelector('input[type="email"]'),password=document.querySelector('input[type="password"]')
email.value='test@example.com';email.dispatchEvent(new Event('input',{bubbles:true}));password.value='password123';password.dispatchEvent(new Event('input',{bubbles:true}))
document.querySelector('.auth-body form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await settle();await settle()
assert.ok(document.querySelector('.place-community'))
assert.ok(document.querySelector('.comment-form'))
await click(button('Byłem tu'))
assert.equal(document.querySelector('.visit-total strong').textContent,'1')
assert.equal(document.querySelector('.visit-button').getAttribute('aria-pressed'),'true')
await click(button('Byłem tu'))
assert.equal(document.querySelector('.visit-total strong').textContent,'0')
const textarea=document.querySelector('textarea'),body='<img src=x onerror=alert(1)> Piękne miejsce!'
textarea.value=body;textarea.dispatchEvent(new Event('input',{bubbles:true}));await settle()
failPost=true;document.querySelector('.comment-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await settle()
assert.equal(textarea.value,body)
assert.match(document.querySelector('.community-error').textContent,/Spróbuj później/)
failPost=false;document.querySelector('.comment-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await settle()
assert.equal(document.querySelector('.comment-body').textContent,body)
assert.equal(document.querySelector('.comment-body img'),null)
assert.equal(document.querySelector('textarea').value,'')
assert.equal(document.querySelector('.comments-heading h3 span').textContent,'1')
await click(button('Usuń swój komentarz'))
assert.equal(document.querySelectorAll('.place-comment').length,0)
app.unmount();dom.window.close()
console.log('PASS: Google Maps coordinates, login returns to place, visit toggle/count, comment add/delete, failed draft preservation and escaped content')
