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
const models=[{id:'gpt-6-luna',label:'gpt-6-luna — oszczędny'},{id:'gpt-6.1-terra',label:'gpt-6.1-terra'},{id:'gpt-6.1-sol',label:'gpt-6.1-sol'},{id:'gpt-6-astra',label:'gpt-6-astra — najdroższy'}]
let plannerModel='gpt-6.1-terra',failModel=false,failCreate=false
const archived=new Set()
window.confirm=()=>true
globalThis.fetch=async(path,options={})=>{
 assert.equal(options.headers.Authorization,'Bearer admin-token')
 calls.push({path,method:options.method||'GET'})
 if(options.method==='PUT'){
  if(failModel)return {ok:false,status:409,json:async()=>({detail:'Najpierw zatrzymaj zadanie.'})}
  const id=path.match(/tasks\/(\w+)\/model/)[1],selected=JSON.parse(options.body).model
  assert.ok(models.some(model=>model.id===selected))
  if(id==='planner')plannerModel=selected
  else tasks.find(task=>task.id===id).model=selected
 }
 if(options.method==='DELETE'){
  const id=path.split('/').at(-1);archived.add(id)
  const task=tasks.find(t=>t.id===id);task.status='stopped';task.can_start=true;task.can_stop=false
 }
 if(path==='/api/admin/prompt-tasks'&&options.method==='POST'){
  if(failCreate)return {ok:false,status:422,json:async()=>({detail:'Wskaż dane do uzupełnienia.'})}
  const body=JSON.parse(options.body)
  if(body.prompt.startsWith('Dodaj województwo')){
   assert.equal(body.region,null)
   tasks.push({id:'prompt2',custom:true,task_type:'region_import',name:body.prompt,prompt:body.prompt,model:body.model,paid:true,status:'idle',region:'lubelskie',total:0,processed:0,updated:0,limit:25,fields:'atrakcje, opisy i dostępne zdjęcia',scope:'Atrakcje · Lubelskie',can_start:true,can_stop:false})
   return {ok:true,json:async()=>structuredClone(tasks.at(-1))}
  }
  assert.equal(body.prompt,'Uzupełnij wszystkie numery telefonów dla zamków')
  assert.equal(body.model,'gpt-6-luna');assert.equal(body.region,null)
  tasks.push({id:'prompt1',custom:true,name:body.prompt,prompt:body.prompt,model:body.model,paid:true,status:'idle',region:null,total:2,processed:0,updated:0,limit:10,fields:'numery telefonów',scope:'Zamki · Cała Polska',can_start:true,can_stop:false})
  return {ok:true,json:async()=>structuredClone(tasks.at(-1))}
 }
 if(path==='/api/admin/tasks/restore')archived.clear()
 else if(options.method==='POST'){
  const [,id,action]=path.match(/tasks\/(\w+)\/(start|stop)/)
  const task=tasks.find(t=>t.id===id),body=JSON.parse(options.body)
  assert.equal(body.max_places,25)
  if(id==='region')assert.equal(body.region,'dolnoslaskie')
  task.status=action==='start'?'running':'stopped';task.can_start=action!=='start';task.can_stop=action==='start'
 }
 return {ok:true,json:async()=>structuredClone({tasks:tasks.filter(task=>!archived.has(task.id)).map(task=>({...task,can_change_model:task.paid&&task.status!=='running'})),archived_count:archived.size,model_options:models,planner:{model:plannerModel,status:'Na żądanie użytkownika',can_change_model:true}})}
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
assert.equal(document.querySelector('#task-model-planner').value,'gpt-6.1-terra')
assert.equal(document.querySelector('[data-task="photos"] select'),null,'Photos use no AI model')
const choose=async(id,value)=>{const select=document.querySelector('#task-model-'+id);assert.ok(!select.disabled);select.value=value;select.dispatchEvent(new Event('change',{bubbles:true}));await settle();await settle()}
await choose('contacts','gpt-6.1-sol')
assert.equal(document.querySelector('#task-model-contacts').value,'gpt-6.1-sol')
assert.equal(calls.filter(c=>c.method==='POST').length,0,'Changing a model never starts paid work')
await choose('planner','gpt-6-luna')
assert.equal(plannerModel,'gpt-6-luna')
failModel=true
await choose('contacts','gpt-6-astra')
assert.match(document.querySelector('[role="alert"]').textContent,/Najpierw zatrzymaj/)
assert.equal(document.querySelector('#task-model-contacts').value,'gpt-6.1-sol','Failed saves restore the persisted choice')
failModel=false
await click('[data-task="contacts"] button',0)
assert.match(document.querySelector('[data-task="contacts"] .task-status').textContent,/W trakcie/)
assert.ok(document.querySelector('#task-model-contacts').disabled,'Running tasks cannot change models')
await click('[data-task="contacts"] button',1)
assert.match(document.querySelector('[data-task="contacts"] .task-status').textContent,/Zatrzymane/)
assert.match(document.querySelector('[data-task="contacts"]').textContent,/144 \/ 796/,'Stopping preserves the completed count')
await click('[data-task="photos"] button',1)
assert.equal(tasks[0].status,'stopped')
await click('[data-task="photos"] button',0)
await click('[data-task="region"] button',0)
assert.equal(tasks[2].status,'running')
assert.equal(calls.filter(c=>c.method==='POST').length,5)
window.confirm=()=>false
await click('[data-task="region"] .delete-task',0)
assert.equal(calls.filter(c=>c.method==='DELETE').length,0,'Cancelling removal keeps the task')
window.confirm=()=>true
await click('[data-task="region"] .delete-task',0)
assert.equal(document.querySelector('[data-task="region"]'),null)
assert.equal(tasks[2].status,'stopped','Removing stops running work')
await click('.restore-tasks',0)
assert.ok(document.querySelector('[data-task="region"]'))
assert.equal(tasks[2].status,'stopped','Restoring does not start work')
const prompt=document.querySelector('#new-task-prompt')
prompt.value='Uzupełnij wszystkie numery telefonów dla zamków';prompt.dispatchEvent(new Event('input',{bubbles:true}));await settle()
const submitPrompt=async()=>{document.querySelector('.prompt-task-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await settle();await settle()}
failCreate=true;await submitPrompt()
assert.match(document.querySelector('[role="alert"]').textContent,/Wskaż dane/)
assert.ok(prompt.value,'Failed creation preserves the instruction')
failCreate=false
const startsBefore=calls.filter(call=>call.path.endsWith('/start')).length
await submitPrompt()
assert.equal(prompt.value,'')
assert.match(document.querySelector('[data-task="prompt1"]').textContent,/Zamki · Cała Polska/)
assert.equal(calls.filter(call=>call.path.endsWith('/start')).length,startsBefore,'Saving the instruction does not start paid work')
await click('[data-task="prompt1"] button',0)
assert.equal(calls.at(-2).path,'/api/admin/prompt-tasks/prompt1/start')
assert.ok(document.querySelector('#task-model-prompt1').disabled)
await click('[data-task="prompt1"] button',1)
await choose('prompt1','gpt-6.1-sol')
assert.equal(tasks.at(-1).model,'gpt-6.1-sol')
await click('[data-task="prompt1"] .delete-task',0)
assert.equal(document.querySelector('[data-task="prompt1"]'),null)
await click('.prompt-examples button',0)
assert.match(document.querySelector('#new-task-prompt').value,/Dodaj województwo lubelskie/)
await submitPrompt()
assert.match(document.querySelector('[role="status"]').textContent,/Kliknij Start/)
assert.ok(!document.querySelector('[role="status"]').textContent.includes('Obiektów do sprawdzenia: 0'))
assert.match(document.querySelector('[data-task="prompt2"]').textContent,/Lubelskie/)
app.unmount();dom.window.close()
console.log('PASS: task/model/status list, no paid autostart, bounded Start, independent Stop, retained progress and planner model')
