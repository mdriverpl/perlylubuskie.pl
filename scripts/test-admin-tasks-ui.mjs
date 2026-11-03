import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/admin'})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event'])globalThis[key]=dom.window[key]
const tasks=[
 {id:'photos',name:'Zdjęcia — Lubuskie',agent:'Wikimedia Commons',model:null,paid:false,status:'running',processed:1,total:4,added:1,missing:0,region:'lubuskie',can_start:false,can_stop:true},
 {id:'contacts',name:'Kontakty',agent:'Weryfikacja źródeł',model:'gpt-6-luna',paid:true,status:'stopped',processed:144,total:796,limit:10,can_start:true,can_stop:false},
 {id:'region',name:'Opisy — Dolnośląskie',agent:'Badanie atrakcji',model:'gpt-6-luna',paid:true,status:'idle',processed:0,total:0,limit:25,region:'dolnoslaskie',can_start:true,can_stop:false},
]
const calls=[]
globalThis.fetch=async(path,options={})=>{
 assert.equal(options.headers.Authorization,'Bearer admin-token')
 calls.push({path,method:options.method||'GET'})
 if(options.method==='POST'){
  const [,id,action]=path.match(/tasks\/(\w+)\/(start|stop)/)
  const task=tasks.find(t=>t.id===id),body=JSON.parse(options.body)
  assert.equal(body.max_places,25)
  if(id==='region')assert.equal(body.region,'dolnoslaskie')
  task.status=action==='start'?'running':'stopped';task.can_start=action!=='start';task.can_stop=action==='start'
 }
 return {ok:true,json:async()=>structuredClone({tasks,planner:{model:'gpt-6.1-terra',status:'Na żądanie użytkownika'}})}
}
const {createApp,nextTick}=await import('vue')
const Component=(await import('../artifacts/admin-tasks-test.mjs')).default
const app=createApp(Component,{token:'admin-token',region:{slug:'dolnoslaskie'}});app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async(selector,index)=>{const button=document.querySelectorAll(selector)[index];assert.ok(button&&!button.disabled);button.click();await settle();await settle()}
await settle();await settle()
assert.equal(document.querySelectorAll('.admin-task-row').length,3)
assert.equal(calls.filter(c=>c.method==='POST').length,0,'Loading the panel never starts paid tasks')
assert.match(document.querySelector('[data-task="photos"]').textContent,/Bez tokenów AI/)
assert.match(document.querySelector('[data-task="contacts"]').textContent,/gpt-6-luna/)
assert.match(document.querySelector('[data-task="contacts"]').textContent,/do 10 obiektów/)
assert.match(document.querySelector('.planner-agent').textContent,/gpt-6.1-terra/)
await click('[data-task="contacts"] button',0)
assert.match(document.querySelector('[data-task="contacts"] .task-status').textContent,/W trakcie/)
await click('[data-task="contacts"] button',1)
assert.match(document.querySelector('[data-task="contacts"] .task-status').textContent,/Zatrzymane/)
assert.match(document.querySelector('[data-task="contacts"]').textContent,/144 \/ 796/,'Stopping preserves the completed count')
await click('[data-task="photos"] button',1)
assert.equal(tasks[0].status,'stopped')
await click('[data-task="photos"] button',0)
await click('[data-task="region"] button',0)
assert.equal(tasks[2].status,'running')
assert.equal(calls.filter(c=>c.method==='POST').length,5)
app.unmount();dom.window.close()
console.log('PASS: task/model/status list, no paid autostart, bounded Start, independent Stop, retained progress and planner model')
