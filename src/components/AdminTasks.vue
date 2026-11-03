<script setup>
import {ref,watch,onBeforeUnmount} from 'vue'
import {readApiJson} from '../apiResponse.js'
const props=defineProps({token:String,region:Object})
const emit=defineEmits(['changed'])
const tasks=ref([]),planner=ref(null),models=ref([]),archivedCount=ref(0),error=ref(''),message=ref(''),busy=ref('')
const newPrompt=ref(''),newModel=ref('gpt-6-luna')
function taskPath(task){return task.custom?`/api/admin/prompt-tasks/${task.id}`:`/api/admin/tasks/${task.id}`}
const labels={idle:'Gotowe do uruchomienia',queued:'W kolejce',running:'W trakcie',stopping:'Zatrzymywanie…',stopped:'Zatrzymane',cancelled:'Zatrzymane',paused:'Limit porcji — zatrzymane',blocked:'Wstrzymane',failed:'Błąd',completed:'Zakończone',published:'Opublikowane'}
let timer,controller,version=0,disposed=false
async function load(){
 clearTimeout(timer);controller?.abort();controller=new AbortController();const current=++version
 try{
  const response=await fetch('/api/admin/tasks?region='+encodeURIComponent(props.region?.slug||'lubuskie'),{headers:{Authorization:'Bearer '+props.token},signal:controller.signal})
  const data=await readApiJson(response,'Nie udało się odczytać zadań.')
  if(current!==version||disposed)return
  const previous=tasks.value
  tasks.value=Array.isArray(data.tasks)?data.tasks:[];planner.value=data.planner;models.value=data.model_options||[];archivedCount.value=data.archived_count||0;error.value=''
  if(previous.some(old=>tasks.value.some(next=>next.id===old.id&&((next.updated||0)>(old.updated||0)||(next.added||0)>(old.added||0)||['running','queued','stopping'].includes(old.status)&&!['running','queued','stopping'].includes(next.status)))))emit('changed')
 }catch(e){if(current===version&&!disposed&&e.name!=='AbortError')error.value=e.message}
 finally{if(current===version&&!disposed)timer=setTimeout(load,tasks.value.some(t=>['running','queued','stopping'].includes(t.status))?5000:15000)}
}
async function act(task,action){
 if(busy.value)return
 busy.value=task.id;message.value='';error.value=''
 try{
  const response=await fetch(`${taskPath(task)}/${action}`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+props.token},body:JSON.stringify({region:task.region||'lubuskie',max_places:25}),signal:AbortSignal.timeout(20000)})
  await readApiJson(response,'Nie udało się zmienić stanu zadania.')
  message.value=action==='stop'?'Zatrzymano zadanie. Zapisane wyniki pozostają w bazie.':'Uruchomiono zadanie.'
  await load();emit('changed')
 }catch(e){error.value=e.message}
 finally{busy.value=''}
}
async function changeModel(kind,event){
 const select=event.target,selected=select.value
 if(busy.value)return
 busy.value=kind;message.value='';error.value=''
 try{
  const task=tasks.value.find(task=>task.id===kind)
  const response=await fetch(`${task?taskPath(task):'/api/admin/tasks/'+kind}/model`,{method:'PUT',headers:{'Content-Type':'application/json',Authorization:'Bearer '+props.token},body:JSON.stringify({model:selected}),signal:AbortSignal.timeout(20000)})
  await readApiJson(response,'Nie udało się zapisać modelu.')
  await load()
  message.value=`Zapisano model ${selected}. Będzie używany przy kolejnych zapytaniach. Zmiana nie uruchamia zadania.`
 }catch(e){error.value=e.message}
 finally{
  busy.value=''
  select.value=kind==='planner'?planner.value?.model:tasks.value.find(task=>task.id===kind)?.model
 }
}
async function removeTask(task){
 if(busy.value||!window.confirm(`Usunąć zadanie „${task.name}” z listy i zatrzymać jego pracę? Zapisane miejsca, zdjęcia i wyniki pozostaną w bazie.`))return
 busy.value=task.id;error.value='';message.value=''
 try{
  const response=await fetch(taskPath(task),{method:'DELETE',headers:{'Content-Type':'application/json',Authorization:'Bearer '+props.token},body:JSON.stringify({region:task.region||'lubuskie'}),signal:AbortSignal.timeout(20000)})
  await readApiJson(response,'Nie udało się usunąć zadania.')
  await load();emit('changed');message.value='Usunięto zadanie z listy i zlecono zatrzymanie pracy. Zapisane dane pozostają w bazie.'
 }catch(e){error.value=e.message}
 finally{busy.value=''}
}
async function restoreTasks(){
 if(busy.value)return
 busy.value='restore';error.value='';message.value=''
 try{
  const response=await fetch('/api/admin/tasks/restore',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+props.token},body:JSON.stringify({region:props.region?.slug||'lubuskie'}),signal:AbortSignal.timeout(20000)})
  await readApiJson(response,'Nie udało się przywrócić zadań.')
  await load();message.value='Przywrócono zadania na listę. Uruchomienie wymaga przycisku Start.'
 }catch(e){error.value=e.message}
 finally{busy.value=''}
}
async function createTask(){
 if(busy.value||newPrompt.value.trim().length<10)return
 busy.value='create';error.value='';message.value=''
 try{
  const response=await fetch('/api/admin/prompt-tasks',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+props.token},body:JSON.stringify({prompt:newPrompt.value.trim(),model:newModel.value,region:null}),signal:AbortSignal.timeout(20000)})
  const task=await readApiJson(response,'Nie udało się zapisać zadania.')
  newPrompt.value='';await load()
  message.value=task.task_type==='region_import'?'Zapisano zadanie dodania województwa. Kliknij Start — miejsca, opisy i dostępne zdjęcia będą dodawane na bieżąco.':`Zapisano zadanie. Obiektów do sprawdzenia: ${task.total}. Uruchom je przyciskiem Start.`
 }catch(e){error.value=e.message}
 finally{busy.value=''}
}
watch(()=>props.region?.slug,load,{immediate:true})
onBeforeUnmount(()=>{disposed=true;version++;clearTimeout(timer);controller?.abort()})
</script>
<template>
 <section class="admin-card admin-tasks" aria-label="Zadania administratora">
  <div class="tasks-heading"><h2>Zadania</h2><button class="text-link" @click="load">Odśwież</button></div>
  <p>Każde zadanie uruchamiasz i zatrzymujesz osobno. Płatne zadania AI kończą pracę po wskazanej porcji.</p>
  <form class="prompt-task-form" @submit.prevent="createTask">
   <label for="new-task-prompt">Dodaj zadanie — wpisz prompt</label>
   <textarea id="new-task-prompt" v-model="newPrompt" required minlength="10" maxlength="2000" rows="3" placeholder="Dodaj województwo lubelskie — atrakcje, opisy i zdjęcia" :disabled="!!busy"></textarea>
   <div class="prompt-examples"><span>Przykłady:</span><button type="button" class="text-link" :disabled="!!busy" @click="newPrompt='Dodaj województwo lubelskie — atrakcje, opisy i zdjęcia'">Dodaj województwo</button><button type="button" class="text-link" :disabled="!!busy" @click="newPrompt='Uzupełnij wszystkie numery telefonów dla zamków'">Uzupełnij telefony</button></div>
   <small>Wpisz polecenie z nazwą województwa lub rodzajem miejsc. Dodawanie województwa obejmuje atrakcje bez noclegów, winiarni i restauracji. Zapisz zadanie, a następnie kliknij Start.</small>
   <div class="prompt-task-options"><label>Model AI<select v-model="newModel" :disabled="!!busy"><option v-for="model in models" :key="model.id" :value="model.id">{{model.label}}</option></select></label><button class="button" type="submit" :disabled="!!busy||!models.length||newPrompt.trim().length<10">{{busy==='create'?'Zapisuję…':'Zapisz zadanie'}}</button></div>
  </form>
  <p v-if="error" role="alert" class="task-error">{{error}}</p><p v-if="message" role="status">{{message}}</p>
  <button v-if="archivedCount" class="text-link restore-tasks" :disabled="!!busy" @click="restoreTasks">Przywróć usunięte zadania ({{archivedCount}})</button>
  <div class="task-columns" aria-hidden="true"><span>Zadanie</span><span>Wykonawca / model</span><span>Status i postęp</span><span>Sterowanie</span></div>
  <article v-for="task in tasks" :key="task.id" class="admin-task-row" :data-task="task.id">
   <div class="task-name"><strong>{{task.name}}</strong><small>{{task.paid?`Płatne AI · do ${task.limit||25} obiektów / Start`:'Bez tokenów AI'}}</small><template v-if="task.custom"><small>{{task.scope}}</small><small>Uzupełniane: {{task.fields}}</small><details class="saved-prompt"><summary>Prompt</summary><p>{{task.prompt}}</p></details></template></div>
   <div class="task-agent"><template v-if="task.model&&models.length"><label :for="`task-model-${task.id}`">Model AI</label><select :id="`task-model-${task.id}`" :value="task.model" :disabled="!!busy||!task.can_change_model" @change="changeModel(task.id,$event)"><option v-if="!models.some(model=>model.id===task.model)" :value="task.model">{{task.model}}</option><option v-for="model in models" :key="model.id" :value="model.id">{{model.label}}</option></select><small v-if="!task.can_change_model">Zatrzymaj zadanie, aby zmienić model.</small></template><strong v-else>{{task.model||task.agent}}</strong><small v-if="task.model">{{task.agent}}</small></div>
   <div class="task-progress"><span class="task-status" :class="task.status">{{labels[task.status]||task.status}}</span><progress v-if="task.total" :value="task.processed" :max="task.total" :aria-label="`Sprawdzono ${task.processed} z ${task.total}`"></progress><small v-if="task.total">Sprawdzono {{task.processed}} / {{task.total}}<span v-if="task.id==='photos'"> · Dodano zdjęć: {{task.added||0}} · Brak: {{task.missing||0}}</span><span v-if="task.custom"> · Uzupełniono: {{task.updated||0}}</span><span v-if="task.failed"> · Błędy: {{task.failed}}</span></small><small v-if="task.message" class="task-message">{{task.message}}</small></div>
   <div class="task-actions"><button class="button" :disabled="!!busy||!task.can_start" @click="act(task,'start')">{{busy===task.id?'Chwilę…':'Start'}}</button><button class="button outline" :disabled="!!busy||!task.can_stop" @click="act(task,'stop')">Zatrzymaj</button><button class="text-link delete-task" :disabled="!!busy" @click="removeTask(task)">Usuń zadanie</button></div>
  </article>
  <div v-if="planner" class="planner-agent task-agent"><label for="task-model-planner">Planer AI</label><select v-if="models.length" id="task-model-planner" :value="planner.model" :disabled="!!busy||!planner.can_change_model" @change="changeModel('planner',$event)"><option v-if="!models.some(model=>model.id===planner.model)" :value="planner.model">{{planner.model}}</option><option v-for="model in models" :key="model.id" :value="model.id">{{model.label}}</option></select><strong v-else>{{planner.model}}</strong><small>{{planner.status}}. Wybór modelu jest zapamiętywany. Droższe modele zwiększają koszt zadania.</small></div>
 </section>
</template>
<style scoped>
.prompt-examples{display:flex;flex-wrap:wrap;gap:7px 12px;align-items:center;font-size:11px;margin:3px 0 12px;color:#718369}.prompt-examples button{font-size:11px;padding:3px 0}.prompt-task-form{padding:16px;margin:18px 0;border:1px solid #dbe4d3;border-radius:10px;background:#f8faf5}.prompt-task-form label{display:block;font-size:12px;color:#345341}.prompt-task-form textarea,.prompt-task-form select{box-sizing:border-box;width:100%;max-width:100%;min-width:0;padding:10px;border:1px solid #d2dfc9;border-radius:7px;background:#fff;color:#173b32;font:inherit;margin:6px 0}.prompt-task-form small{display:block;font-size:11px;color:#718369;line-height:1.7}.prompt-task-options{display:flex;align-items:end;gap:12px;flex-wrap:wrap;margin-top:12px}.prompt-task-options label{flex:1;min-width:150px}.prompt-task-options .button{margin-bottom:6px;min-height:40px}.saved-prompt{margin-top:8px;font-size:11px}.saved-prompt summary{cursor:pointer;color:#19744f}.saved-prompt p{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7}.task-agent label{display:block;font-size:11px;color:#718369;margin-bottom:5px}.task-agent select{display:block;width:100%;max-width:100%;min-width:0;padding:9px 7px;border:1px solid #d2dfc9;border-radius:8px;background:#fff;color:#173b32;font:inherit}.task-agent select:disabled{background:#f4f6f1;color:#718369}.task-agent select:focus-visible{outline:2px solid #19744f;outline-offset:2px}.planner-agent{margin-top:16px;font-size:12px;max-width:420px}.planner-agent select{max-width:270px}.admin-tasks{border:1px solid #dbe4d3;background:#fff;border-radius:12px;padding:24px;margin:20px 0}.tasks-heading{display:flex;align-items:center;justify-content:space-between;gap:15px}.tasks-heading h2{font-size:21px;margin:0}.admin-tasks>p{font-size:12px;color:#718369;line-height:1.8;margin:12px 0}.task-columns,.admin-task-row{display:grid;grid-template-columns:minmax(170px,1.2fr) minmax(140px,1fr) minmax(180px,1.3fr) 175px;gap:18px;align-items:center}.task-columns{margin-top:22px;font-size:11px;color:#718369}.admin-task-row{padding:20px 0;border-bottom:1px solid #e3eadd;font-size:12px}.admin-task-row strong{font-size:13px;line-height:1.6;overflow-wrap:anywhere}.admin-task-row small{display:block;font-size:11px;color:#718369;line-height:1.7;margin-top:5px}.task-status{display:inline-block;padding:4px 9px;background:#f0f3ec;color:#65775b;border-radius:14px;font-size:11px}.task-status.running,.task-status.completed{background:#e8f3e2;color:#176f4b}.task-status.blocked,.task-status.failed{background:#fff0df;color:#8c581d}.task-progress progress{display:block;width:100%;height:9px;margin:10px 0 3px;accent-color:#19744f}.task-actions{display:flex;flex-wrap:wrap;gap:7px}.task-actions .delete-task{flex-basis:100%;color:#973b2e;font-size:11px;padding:5px}.restore-tasks{font-size:12px}.task-actions .button{padding:10px 12px;font-size:11px;min-height:40px;flex:1;justify-content:center}.task-actions button:disabled{opacity:.45;cursor:default}.task-actions button:focus-visible{outline:2px solid #19744f;outline-offset:3px}.task-message{overflow-wrap:anywhere}.admin-tasks .task-error{color:#973b2e}.admin-tasks .planner-agent{margin-bottom:0}.task-columns+article{margin-top:5px}@media(max-width:1000px){.task-columns{display:none}.admin-task-row{grid-template-columns:1fr 1fr}.task-actions{justify-self:end}.task-progress{grid-column:1}.task-agent{text-align:right}.admin-tasks{padding:20px}}@media(max-width:550px){.admin-tasks{padding:17px}.admin-task-row{grid-template-columns:1fr;gap:9px;padding:20px 0}.task-agent{text-align:left}.task-actions{justify-self:stretch}.task-progress{grid-column:auto}.task-actions .button{min-height:42px}.task-name strong{font-size:14px}}
</style>
