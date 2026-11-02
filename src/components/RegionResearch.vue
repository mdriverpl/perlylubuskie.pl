<script setup>
import {ref,computed,watch,onBeforeUnmount} from 'vue'
import {readApiJson} from '../apiResponse.js'
const props=defineProps({token:String,region:Object,reloadKey:Number})
const emit=defineEmits(['changed','status'])
const job=ref(null),configured=ref(false),loading=ref(true),busy=ref(false),error=ref(''),limit=ref(5000)
let timer,version=0,controller
const running=computed(()=>['queued','running'].includes(job.value?.status))
watch(running,value=>emit('status',value),{immediate:true})
const resumable=computed(()=>['failed','cancelled'].includes(job.value?.status))
const labels={queued:'Oczekuje na rozpoczęcie',running:'Zbieranie danych trwa',completed:'Zbieranie zakończone',failed:'Zbieranie przerwane',cancelled:'Zatrzymano'}
const phase=computed(()=>job.value?.phase==='discovery'?'Wyszukiwanie atrakcji w województwie':'Sprawdzanie informacji, opisy AI i pobieranie zdjęć')
const percent=computed(()=>job.value?.total?Math.min(100,Math.floor(job.value.processed/job.value.total*100)):null)
async function api(suffix='',method='GET',body){
 const response=await fetch(`/api/admin/regions/${props.region.slug}/research${suffix}`,{method,headers:{'Content-Type':'application/json',Authorization:'Bearer '+props.token},...(body?{body:JSON.stringify(body)}:{}),signal:controller.signal})
 return readApiJson(response,'Nie udało się odczytać postępu. Spróbuj ponownie.')
}
function schedule(){clearTimeout(timer);if(running.value)timer=setTimeout(poll,3000)}
async function poll(){
 const current=version,previous=job.value
 try{
  const data=await api();if(current!==version)return
  configured.value=data.configured;job.value=data.job;error.value=''
  if(previous&&previous.id===data.job?.id){
   const saved=data.job.added+data.job.updated,previousSaved=previous.added+previous.updated
   if(saved!==previousSaved||['queued','running'].includes(previous.status)&&!running.value)emit('changed')
  }
 }
 catch(e){if(current===version&&e.name!=='AbortError')error.value=e.message}
 finally{if(current===version){loading.value=false;schedule()}}
}
watch(()=>[props.region.slug,props.reloadKey],()=>{version++;clearTimeout(timer);controller?.abort();controller=new AbortController();job.value=null;loading.value=true;error.value='';poll()},{immediate:true})
onBeforeUnmount(()=>{version++;clearTimeout(timer);controller?.abort()})
async function act(suffix='',body){
 if(busy.value)return
 const current=version;busy.value=true;error.value=''
 try{const data=await api(suffix,'POST',body);if(current!==version)return;job.value=data;schedule()}
 catch(e){if(current===version&&e.name!=='AbortError')error.value=e.message}
 finally{busy.value=false}
}
</script>

<template>
 <section v-if="!region.active||job" class="region-research" aria-label="Automatyczne uzupełnianie województwa">
  <h3>Atrakcje z AI</h3>
  <p v-if="loading" role="status">Odczytuję postęp…</p>
  <p v-else-if="!configured" role="alert">Na serwerze trzeba skonfigurować klucz OpenAI.</p>
  <p v-if="error" role="alert" class="research-error">{{error}} <button class="text-link" @click="poll">Odśwież</button></p>
  <template v-if="job">
   <div class="research-status" role="status" aria-live="polite"><strong>{{labels[job.status]||job.status}}</strong><span v-if="job.cancel_requested&&running">Zatrzymanie nastąpi po bieżącym zapytaniu.</span></div>
   <p v-if="job.status==='queued'">Oczekuje w kolejce · {{job.active_jobs||1}} aktywnych zadań.</p>
   <p v-else-if="running" role="status">{{job.report?.message||phase}}</p>
   <div class="research-progress">
    <div class="research-progress-label"><strong>Postęp dodawania</strong><strong v-if="percent!==null">{{percent}}%</strong><span v-else>Wyszukuję obiekty…</span></div>
    <progress :value="job.total?job.processed:undefined" :max="job.total||1" :aria-label="job.total?`Sprawdzono ${job.processed} z ${job.total}`:'Wyszukiwanie obiektów — liczba jeszcze nieznana'"></progress>
    <p v-if="job.total">Sprawdzono {{job.processed}} / {{job.total}} · <strong>Dodano {{job.added}}</strong> · Zdjęcia {{job.photos}}</p>
    <p v-if="job.total&&job.discovery_done===false">Liczba obiektów rośnie w trakcie wyszukiwania.</p>
   </div>
   <p v-if="job.error" class="research-error" role="alert">{{job.error}}</p>
   <p v-if="job.report?.discovery_errors?.length" class="research-error" role="alert">Nie pobrano części danych. Sprawdź raport.</p>
   <details class="research-report">
    <summary>Raport i szczegóły</summary>
    <p>Dodano {{job.added}} · Uzupełniono {{job.updated}} · Duplikaty {{job.duplicates}} · Do sprawdzenia {{job.review}}</p>
    <p>Ze zdjęciem: {{job.photos}} · Zapisane bez zdjęcia: {{job.missing_photos}}</p>
    <p v-if="job.report?.discovery_groups">Wyszukane kategorie: {{job.report.discovery_cursor||0}} / {{job.report.discovery_groups}}.</p>
    <p>Dane są przetwarzane porcjami do {{job.batch_size||8}} obiektów. Lista miejsc odświeża się automatycznie. Zadanie działa także po zamknięciu panelu.</p>
    <p v-if="job.discovery_done===false">Procent dotyczy dotychczas znalezionych obiektów.</p>
    <p v-if="job.report?.limited">Osiągnięto limit {{job.max_places}} obiektów. Możesz zwiększyć limit i wyszukać ponownie.</p>
    <ul v-if="job.report?.discovery_errors?.length"><li v-for="issue in job.report.discovery_errors" :key="issue.group">{{issue.name}}: {{issue.message}}</li></ul>
    <ul v-if="job.issues?.length"><li v-for="(issue,index) in job.issues" :key="index"><strong>{{issue.name}}</strong>: {{issue.message}}</li></ul>
   </details>
  </template>
  <p v-if="!running&&!region.active&&!loading">AI dodaje opisy i dostępne zdjęcia. Korzysta z płatnego konta OpenAI.</p>
  <div class="research-actions">
   <button v-if="running" class="button outline" :disabled="busy||job.cancel_requested" @click="act('/cancel')">Zatrzymaj</button>
   <button v-else-if="resumable&&!region.active" class="button" :disabled="busy||!configured" @click="act('/resume')">Wznów</button>
   <button v-else-if="!region.active&&!loading" class="button" :disabled="busy||!configured" @click="act('',{max_places:limit})">{{job?'Wyszukaj ponownie':'Uruchom AI'}}</button>
  </div>
  <details v-if="!running&&!region.active&&!loading" class="research-settings">
   <summary>Ustawienia wyszukiwania</summary>
   <label>Limit obiektów<select v-model.number="limit" :disabled="busy"><option :value="100">100</option><option :value="500">500</option><option :value="1000">1000</option><option :value="5000">5000</option></select></label>
   <button v-if="resumable" class="text-link" :disabled="busy||!configured" @click="act('',{max_places:limit})">Zacznij nowe wyszukiwanie</button>
   <p>Źródła: Wikimedia Commons, Wikidata i OpenStreetMap. Brakujące zdjęcia i niepotwierdzone informacje trafiają do raportu. Katalog nie gwarantuje kompletności.</p>
  </details>
 </section>
</template>

<style scoped>
.research-report,.research-settings{margin:14px 0}.research-settings label{display:flex;flex-direction:column;gap:6px;font-size:12px;margin:14px 0}.research-settings select{padding:10px;border:1px solid #d4dfcb;border-radius:7px;background:#fff}.region-research{border:1px solid #d4e2ce;border-radius:10px;padding:20px;margin:24px 0;background:#f7faf4}.region-research h3{margin:0 0 12px;font-size:18px}.region-research p,.region-research li{font-size:12px;line-height:1.8;color:#586b50;margin:12px 0}.research-status{display:flex;flex-direction:column;gap:6px;font-size:13px}.region-research progress{width:100%;accent-color:#19744f;margin-top:14px}.research-progress{background:#fff;border:1px solid #d4e2ce;border-radius:9px;padding:16px;margin:16px 0}.research-progress-label{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;font-size:14px}.research-progress-label>strong:last-child{font-size:20px;color:#19744f}.research-progress progress{display:block;height:18px;border:0;border-radius:12px;overflow:hidden}.research-progress progress::-webkit-progress-bar{background:#e5eddf;border-radius:12px}.research-progress progress::-webkit-progress-value{background:#19744f;border-radius:12px;transition:width .3s}.research-progress progress::-moz-progress-bar{background:#19744f;border-radius:12px}.research-actions{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:16px}.research-actions label{display:flex;flex-direction:column;gap:6px;font-size:12px}.research-actions select{padding:10px;border:1px solid #d4dfcb;border-radius:7px;background:#fff}.region-research .research-error{color:#973b2e}.region-research summary{font-size:13px;cursor:pointer}.region-research button:disabled{opacity:.5;cursor:default}
</style>
