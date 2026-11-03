import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/admin'})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event'])globalThis[key]=dom.window[key]
const {createApp,nextTick}=await import('vue')
const Research=(await import('../artifacts/region-research-test.mjs')).default
const originalTimeout=globalThis.setTimeout,originalClear=globalThis.clearTimeout
let scheduled,job=null,events=0,requests=[]
globalThis.setTimeout=(fn,delay,...args)=>delay===3000?(scheduled=fn,'poll'):originalTimeout(fn,delay,...args)
globalThis.clearTimeout=id=>id==='poll'?(scheduled=null):originalClear(id)
globalThis.fetch=async(path,request={})=>{
 requests.push({path,request});assert.equal(request.headers.Authorization,'Bearer secret-test')
 if(request.method==='POST'){
  if(path.endsWith('/cancel'))job={...job,cancel_requested:true}
  else if(path.endsWith('/resume'))job={...job,status:'queued',cancel_requested:false}
  else{assert.equal(JSON.parse(request.body).max_places,25);job={id:'job-1',status:'queued',phase:'discovery',discovered:0,total:0,processed:0,added:0,updated:0,duplicates:0,review:0,photos:0,missing_photos:0,issues:[]}}
  return {ok:true,json:async()=>structuredClone(job)}
 }
 return {ok:true,json:async()=>({configured:true,job:structuredClone(job)})}
}
const app=createApp(Research,{token:'secret-test',region:{slug:'kujawsko-pomorskie',active:false},reloadKey:0,onChanged:()=>events++});app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>originalTimeout(r,0));await nextTick()}
const button=text=>[...document.querySelectorAll('button')].find(b=>b.textContent===text)
async function click(text){assert.ok(button(text),text);button(text).click();await settle();await settle()}
await settle();await click('Uruchom AI')
assert.match(document.body.textContent,/Oczekuje na rozpoczęcie/)
assert.ok(scheduled)
assert.equal(document.querySelector('.research-report').open,false,'Detailed report stays folded during import')
assert.equal(document.querySelector('progress').hasAttribute('value'),false,'Discovery shows indeterminate progress')
job={...job,status:'running',phase:'research',total:4,processed:2,added:2,batch_size:8}
job.discovery_done=false;job.report={discovery_groups:6,discovery_cursor:1,message:'AI sprawdza pierwszą porcję obiektów.'}
await scheduled();await settle()
assert.match(document.body.textContent,/AI sprawdza pierwszą porcję/)
assert.match(document.body.textContent,/Wyszukane kategorie: 1 \/ 6/)
assert.match(document.body.textContent,/Procent dotyczy dotychczas znalezionych/)
assert.doesNotMatch(document.querySelector('.research-progress-label').textContent,/%/,'Do not claim a final percentage while categories are still being discovered')
assert.equal(document.querySelector('progress').hasAttribute('value'),false)
job={...job,discovery_done:true};await scheduled();await settle()
assert.match(document.querySelector('.research-progress-label').textContent,/50%/)
job={...job,processed:4,discovery_done:false};await scheduled();await settle()
assert.doesNotMatch(document.querySelector('.research-progress-label').textContent,/100%/,'Finishing the first category must not look like completing the region')
assert.match(document.querySelector('.research-report').textContent,/porcjami do 8 obiektów/)
assert.equal(events,1,'Saved partial results refresh the region before completion')
await scheduled();await settle();assert.equal(events,1,'Unchanged polls do not reload the catalog')
await click('Zatrzymaj')
assert.match(document.body.textContent,/Zatrzymanie nastąpi po bieżącym zapytaniu/)
assert.equal(button('Zatrzymaj').disabled,true)
job={...job,status:'cancelled'};await scheduled();await settle()
await click('Wznów');assert.ok(requests.some(r=>r.path.endsWith('/resume')))
job={...job,status:'completed',discovery_done:true,phase:'completed',total:3,processed:3,added:2,review:1,photos:1,missing_photos:1,issues:[{name:'Obiekt <script>',message:'Brak potwierdzonego zdjęcia'}]}
await scheduled();await settle()
assert.match(document.body.textContent,/Zbieranie zakończone/)
assert.match(document.body.textContent,/Zapisane bez zdjęcia: 1/)
assert.equal(document.querySelector('script'),null)
assert.equal(events,3)
assert.equal(document.querySelector('progress').value,3)
assert.match(document.querySelector('.research-progress-label').textContent,/100%/)
assert.equal(document.querySelector('.research-settings').open,false,'Limits and restart stay in optional settings')
app.unmount();assert.equal(scheduled,null)
globalThis.setTimeout=originalTimeout;globalThis.clearTimeout=originalClear;dom.window.close()
console.log('PASS: region research starts with limit, polls, cancels, resumes, reports missing photos, escapes sources and disposes polling')
