<script setup>
import {ref,watch,onBeforeUnmount} from 'vue'
import {readApiJson} from '../apiResponse.js'
const props=defineProps({token:String,region:Object})
const emit=defineEmits(['changed'])
const tasks=ref([]),planner=ref(null),error=ref(''),message=ref(''),busy=ref('')
const labels={idle:'Gotowe do uruchomienia',queued:'W kolejce',running:'W trakcie',stopped:'Zatrzymane',cancelled:'Zatrzymane',paused:'Limit porcji — zatrzymane',blocked:'Wstrzymane',failed:'Błąd',completed:'Zakończone',published:'Opublikowane'}
let timer,controller,version=0,disposed=false
async function load(){
 clearTimeout(timer);controller?.abort();controller=new AbortController();const current=++version
 try{
  const response=await fetch('/api/admin/tasks?region='+encodeURIComponent(props.region?.slug||'lubuskie'),{headers:{Authorization:'Bearer '+props.token},signal:controller.signal})
  const data=await readApiJson(response,'Nie udało się odczytać zadań.')
  if(current!==version||disposed)return
  const previous=tasks.value
  tasks.value=Array.isArray(data.tasks)?data.tasks:[];planner.value=data.planner;error.value=''
  if(previous.some(old=>['running','queued'].includes(old.status)&&tasks.value.some(next=>next.id===old.id&&!['running','queued'].includes(next.status))))emit('changed')
 }catch(e){if(current===version&&!disposed&&e.name!=='AbortError')error.value=e.message}
 finally{if(current===version&&!disposed)timer=setTimeout(load,tasks.value.some(t=>['running','queued'].includes(t.status))?5000:15000)}
}
async function act(task,action){
 if(busy.value)return
 busy.value=task.id;message.value='';error.value=''
 try{
  const response=await fetch(`/api/admin/tasks/${task.id}/${action}`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+props.token},body:JSON.stringify({region:task.region||'lubuskie',max_places:25}),signal:AbortSignal.timeout(20000)})
  await readApiJson(response,'Nie udało się zmienić stanu zadania.')
  message.value=action==='stop'?'Zatrzymano zadanie. Zapisane wyniki pozostają w bazie.':'Uruchomiono zadanie.'
  await load();emit('changed')
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
  <p v-if="error" role="alert" class="task-error">{{error}}</p><p v-if="message" role="status">{{message}}</p>
  <div class="task-columns" aria-hidden="true"><span>Zadanie</span><span>Wykonawca / model</span><span>Status i postęp</span><span>Sterowanie</span></div>
  <article v-for="task in tasks" :key="task.id" class="admin-task-row" :data-task="task.id">
   <div class="task-name"><strong>{{task.name}}</strong><small>{{task.paid?`Płatne AI · do ${task.limit||25} obiektów / Start`:'Bez tokenów AI'}}</small></div>
   <div class="task-agent"><strong>{{task.model||task.agent}}</strong><small v-if="task.model">{{task.agent}}</small></div>
   <div class="task-progress"><span class="task-status" :class="task.status">{{labels[task.status]||task.status}}</span><progress v-if="task.total" :value="task.processed" :max="task.total" :aria-label="`Sprawdzono ${task.processed} z ${task.total}`"></progress><small v-if="task.total">Sprawdzono {{task.processed}} / {{task.total}}<span v-if="task.id==='photos'"> · Dodano zdjęć: {{task.added||0}} · Brak: {{task.missing||0}}</span><span v-if="task.failed"> · Błędy: {{task.failed}}</span></small><small v-if="task.message" class="task-message">{{task.message}}</small></div>
   <div class="task-actions"><button class="button" :disabled="!!busy||!task.can_start" @click="act(task,'start')">{{busy===task.id?'Chwilę…':'Start'}}</button><button class="button outline" :disabled="!!busy||!task.can_stop" @click="act(task,'stop')">Zatrzymaj</button></div>
  </article>
  <p v-if="planner" class="planner-agent">Planer AI: <strong>{{planner.model}}</strong> · {{planner.status}}.</p>
 </section>
</template>
<style scoped>
.admin-tasks{border:1px solid #dbe4d3;background:#fff;border-radius:12px;padding:24px;margin:20px 0}.tasks-heading{display:flex;align-items:center;justify-content:space-between;gap:15px}.tasks-heading h2{font-size:21px;margin:0}.admin-tasks>p{font-size:12px;color:#718369;line-height:1.8;margin:12px 0}.task-columns,.admin-task-row{display:grid;grid-template-columns:minmax(170px,1.2fr) minmax(140px,1fr) minmax(180px,1.3fr) 175px;gap:18px;align-items:center}.task-columns{margin-top:22px;font-size:11px;color:#718369}.admin-task-row{padding:20px 0;border-bottom:1px solid #e3eadd;font-size:12px}.admin-task-row strong{font-size:13px;line-height:1.6;overflow-wrap:anywhere}.admin-task-row small{display:block;font-size:11px;color:#718369;line-height:1.7;margin-top:5px}.task-status{display:inline-block;padding:4px 9px;background:#f0f3ec;color:#65775b;border-radius:14px;font-size:11px}.task-status.running,.task-status.completed{background:#e8f3e2;color:#176f4b}.task-status.blocked,.task-status.failed{background:#fff0df;color:#8c581d}.task-progress progress{display:block;width:100%;height:9px;margin:10px 0 3px;accent-color:#19744f}.task-actions{display:flex;gap:7px}.task-actions .button{padding:10px 12px;font-size:11px;min-height:40px;flex:1;justify-content:center}.task-actions button:disabled{opacity:.45;cursor:default}.task-actions button:focus-visible{outline:2px solid #19744f;outline-offset:3px}.task-message{overflow-wrap:anywhere}.admin-tasks .task-error{color:#973b2e}.admin-tasks .planner-agent{margin-bottom:0}.task-columns+article{margin-top:5px}@media(max-width:1000px){.task-columns{display:none}.admin-task-row{grid-template-columns:1fr 1fr}.task-actions{justify-self:end}.task-progress{grid-column:1}.task-agent{text-align:right}.admin-tasks{padding:20px}}@media(max-width:550px){.admin-tasks{padding:17px}.admin-task-row{grid-template-columns:1fr;gap:9px;padding:20px 0}.task-agent{text-align:left}.task-actions{justify-self:stretch}.task-progress{grid-column:auto}.task-actions .button{min-height:42px}.task-name strong{font-size:14px}}
</style>
