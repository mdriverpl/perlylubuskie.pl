import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/miejsca',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window)
globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
let blobs=0,revoked=0
URL.createObjectURL=()=>`blob:test-${++blobs}`;URL.revokeObjectURL=()=>revoked++
const user={id:7,name:'<b>Ada</b>'}
localStorage.setItem('perly-user',JSON.stringify(user));localStorage.setItem('perly-token','photo-token')
let uploads=0,creates=0,failUpload=true,failCreate=true,place
const response=data=>({ok:true,json:async()=>data})
globalThis.fetch=async(path,options={})=>{
 if(path==='/api/place-photos'){
  uploads++;assert.equal(options.headers.Authorization,'Bearer photo-token')
  assert.equal(options.headers['Content-Type'],'image/jpeg');assert.ok(options.body instanceof window.File)
  if(uploads===2&&failUpload){failUpload=false;return {ok:false,json:async()=>({detail:'Błąd przesyłania zdjęcia.'})}}
  return response({id:uploads===1?'photo-1':'photo-2'})
 }
 if(path==='/api/places'&&options.method==='POST'){
  creates++;const data=JSON.parse(options.body)
  assert.deepEqual(data.photo_ids,['photo-1','photo-2']);assert.equal(data.photos,undefined);assert.equal(data.photo_rights_confirmed,true)
  if(failCreate){failCreate=false;return {ok:false,json:async()=>({detail:'Nie udało się zapisać miejsca.'})}}
  place={...data,id:1000000001,category:'heritage',rating:0,image:'/api/place-photos/photo-1.webp',like_count:12,comment_count:3,details:{kind:'palace',submitted_by:7,user_photos:data.photo_ids.map(id=>({id,url:`/api/place-photos/${id}.webp`,author:user.name}))}}
  return response(place)
 }
 if(path==='/api/places/1000000001/photos'){
  const data=JSON.parse(options.body);assert.equal(data.photo_rights_confirmed,true)
  const added={id:'photo-3',url:'/api/place-photos/photo-3.webp',author:user.name}
  return response({id:place.id,image:place.image,details:{...place.details,user_photos:[...place.details.user_photos,added]}})
 }
 if(path==='/api/places')return response([])
 if(path.endsWith('/community'))return response({comments:[],like_count:12,comment_count:3,visit_count:0})
 return response([])
}
const {createApp,nextTick}=await import('vue')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app');await settle();await settle()
document.querySelector('.create-place-button').click();await settle()
const change=async(selector,value)=>{const e=document.querySelector(selector);e.value=value;e.dispatchEvent(new Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}));await settle()}
await change('#new-place-name','Nowy pałac');await change('#new-place-location','Zabór');await change('#new-place-description','Opis');await change('#new-place-lat','51.95');await change('#new-place-lng','15.7');await change('#new-place-type','palace')
const select=async(files)=>{const input=document.querySelector('.place-photo-files');Object.defineProperty(input,'files',{configurable:true,value:files});input.dispatchEvent(new Event('change',{bubbles:true}));await settle()}
const jpg=name=>new window.File(['pixels'],name,{type:'image/jpeg'})
await select([new window.File(['svg'],'test.svg',{type:'image/svg+xml'})]);assert.match(document.querySelector('.photo-picker [role=alert]').textContent,/JPG/)
const huge=jpg('huge.jpg');Object.defineProperty(huge,'size',{value:10*1024*1024+1})
await select([huge]);assert.match(document.querySelector('.photo-picker [role=alert]').textContent,/10 MB/)
await select(Array.from({length:6},(_,i)=>jpg(`${i}.jpg`)));assert.equal(document.querySelectorAll('.photo-preview').length,0)
await select([jpg('first.jpg'),jpg('second.jpg')]);assert.equal(document.querySelectorAll('.photo-preview').length,2)
assert.ok(document.querySelector('.add-place-form button[type=submit]').disabled)
const confirm=async()=>{const box=document.querySelector('.photo-rights input');box.checked=true;box.dispatchEvent(new Event('change',{bubbles:true}));await settle()}
await confirm()
const submit=async()=>{document.querySelector('.add-place-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await settle();await settle()}
await submit();assert.equal(creates,0);assert.match(document.querySelector('.add-place-form>[role=alert]').textContent,/przesyłania/);assert.equal(document.querySelectorAll('.photo-preview').length,2)
await submit();assert.equal(uploads,3,'Retry reuses the first staged photo');assert.equal(creates,1)
await submit();assert.equal(uploads,3,'A failed place save must not upload duplicate photos');assert.equal(creates,2)
assert.equal(document.querySelector('.detail-image').getAttribute('src'),place.image)
assert.equal(document.querySelectorAll('.place-photo-thumbs button').length,2)
assert.equal(document.querySelector('.place-photo-author b'),null,'Author name is escaped')
document.querySelectorAll('.place-photo-thumbs button')[1].click();await settle()
assert.match(document.querySelector('.detail-image').getAttribute('src'),/photo-2/)
document.querySelector('.place-photo-editor>button').click();await settle()
await select([jpg('remove.jpg')]);document.querySelector('.photo-preview button').click();await settle();assert.equal(document.querySelectorAll('.photo-preview').length,0)
await select([jpg('third.jpg')]);await confirm()
document.querySelector('.place-photo-editor form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await settle();await settle()
assert.equal(document.querySelectorAll('.place-photo-thumbs button').length,3)
assert.equal(document.querySelector('.place-photo-editor form'),null)
assert.ok(revoked>0,'Temporary preview URLs are released')
app.unmount()
const Photos=(await import('../artifacts/place-photos-test.mjs')).default
const viewer=createApp(Photos,{place,user:{id:8},token:'other',online:true});viewer.mount('#app');await settle()
assert.equal(document.querySelector('.place-photo-editor'),null,'Only the place creator gets the upload controls')
viewer.unmount();dom.window.close()
console.log('PASS: photo file validation, consent, previews/removal, cached upload retry, atomic creation, gallery, escaped author and creator-only additions')
