import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/admin',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
localStorage.setItem('perly-token','admin-token');localStorage.setItem('perly-user',JSON.stringify({id:7,name:'Administrator',email:'owner@example.com'}))
let denied=false,regions=[{slug:'lubuskie',name:'Lubuskie',active:true,allowed_types:['castle','palace','lake','nature','heritage','leisure','stay','food','vineyard'],place_count:1}],records=[],id=1000000000,autoRequests=0,researchJob=null
const types=['castle','palace','lake','nature','heritage','leisure','stay','food','vineyard'].map(id=>({id,name:id}))
const options=[{slug:'lubuskie',name:'Lubuskie'},{slug:'kujawsko-pomorskie',name:'Kujawsko-pomorskie'}]
const oldPlace={id:1,name:'Stare miejsce',category:'nature',region:'lubuskie',lat:52,lng:15,location:'Łagów',image:'/images/lake.webp',subtitle:'Opis',description:'Opis'}
globalThis.fetch=async(path,request={})=>{
 let data
 if(path==='/api/auth/me')data={id:7,name:'Administrator',email:'owner@example.com',is_superadmin:!denied}
 else if(path==='/api/regions')data=regions.filter(r=>r.active)
 else if(path==='/api/places'&&request.method==='POST'){
  const body=JSON.parse(request.body);assert.equal(body.region,'kujawsko-pomorskie');assert.equal(body.place_type,'heritage')
  const record={...body,id:++id,category:'heritage',details:{kind:body.place_type}};records.push(record);regions[1].place_count=records.length;data=record
 }
 else if(path==='/api/places')data=[oldPlace,...(regions[1]?.active?records:[])]
 else if(path==='/api/routes'||path==='/api/routes/public'||path==='/api/favorites')data=[]
 else if(path==='/api/admin/regions'&&request.method==='POST'){
  const body=JSON.parse(request.body);assert.deepEqual(body.allowed_types,['castle','palace','lake','nature','heritage','leisure']);assert.equal(body.slug,'kujawsko-pomorskie')
  regions.push({slug:body.slug,name:'Kujawsko-pomorskie',active:false,allowed_types:body.allowed_types,place_count:0});data=regions
 }
 else if(path.startsWith('/api/admin/')){
  assert.match(request.headers.Authorization,/Bearer admin-token/)
  if(denied)return {ok:false,json:async()=>({detail:'Ta operacja wymaga konta superadministratora.'})}
  if(path.endsWith('/research')&&request.method==='POST'){autoRequests++;assert.equal(JSON.parse(request.body).max_places,5000);researchJob={id:'job-test',status:'queued',phase:'discovery',total:0,processed:0,added:0,updated:0};data=researchJob}
  else if(path.endsWith('/research'))data={configured:true,job:path.includes('kujawsko-pomorskie')?researchJob:null}
  else if(path.endsWith('/places'))data=path.includes('kujawsko-pomorskie')?records:[oldPlace]
  else if(request.method==='PATCH'){const body=JSON.parse(request.body);assert.equal(body.finish_research,true);regions[1].active=body.active;researchJob={...researchJob,status:'cancelled',cancel_requested:true};data=regions}
  else data={regions,options,types}
 }else throw Error('Unexpected '+path)
 return {ok:true,json:async()=>structuredClone(data)}
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
let app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async el=>{assert.ok(el);el.click();await settle();await settle()}
const submit=async form=>{form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await settle();await settle()}
await settle();await settle()
assert.ok(document.querySelector('.admin-regions'))
assert.equal(document.querySelectorAll('.admin-types input:checked').length,6)
assert.equal(document.querySelector('.admin-types').closest('details').open,false,'Category controls stay folded by default')
assert.equal(document.querySelector('#admin-new-region').value,'kujawsko-pomorskie')
await submit(document.querySelector('.admin-card form'))
assert.equal(autoRequests,1,'Primary region creation launches AI research')
assert.equal(document.querySelector('#admin-region').value,'kujawsko-pomorskie')
assert.equal(document.querySelectorAll('#admin-place-type option').length,6)
assert.equal(document.querySelector('.admin-manual').open,false,'Manual editing and JSON import stay folded by default')
await click(document.querySelector('.admin-manual summary'))
assert.equal(document.querySelector('.admin-manual').open,true)
for(const [selector,value] of [['#admin-place-name','Atrakcja <b>Toruń</b>'],['#admin-place-location','Toruń'],['#admin-place-description','Opis'],['#admin-place-lat','53.01'],['#admin-place-lng','18.60']]){
 const input=document.querySelector(selector);input.value=value;input.dispatchEvent(new Event('input',{bubbles:true}));await settle()
}
await submit(document.querySelector('#admin-place-editor'))
assert.equal(records.length,1);assert.ok(!document.querySelector('.admin-place-list b'),'Catalog titles are escaped')
const publish=document.querySelector('.admin-publish');assert.equal(publish.textContent,'Zakończ i opublikuj');assert.equal(publish.disabled,false)
await click(publish)
assert.equal(regions[1].active,true)
await click([...document.querySelectorAll('.admin-card button')].find(el=>el.textContent==='Otwórz katalog'))
assert.equal(window.location.pathname,'/miejsca');assert.equal(document.querySelector('#active-region').value,'kujawsko-pomorskie')
assert.equal(document.querySelector('.place-title').textContent,'Atrakcja <b>Toruń</b>')
assert.equal(document.querySelector('.facet-list input[value="stays"]'),null)
assert.equal(document.querySelector('.facet-list input[value="wineries"]'),null)
assert.equal(document.querySelector('.facet-list input[value="restaurants"]'),null)
app.unmount();denied=true;window.history.replaceState(null,'','/admin');app=createApp(App);app.mount('#app');await settle();await settle()
assert.equal(document.querySelector('.admin-card'),null,'Server rejection hides management forms despite cached identity')
assert.match(document.querySelector('.admin-error').textContent,/superadministratora/)
app.unmount();dom.window.close()
console.log('PASS: admin authorization, draft region creation, six categories, place entry and escaping, publication, region switch and blocked access')
