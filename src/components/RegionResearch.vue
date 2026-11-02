<script setup>
import {ref,computed,watch,onBeforeUnmount} from 'vue'
import {readApiJson} from '../apiResponse.js'
const props=defineProps({token:String,region:Object,reloadKey:Number})
const emit=defineEmits(['changed'])
const job=ref(null),configured=ref(false),loading=ref(true),busy=ref(false),error=ref(''),limit=ref(5000)
let timer,version=0,controller
const running=computed(()=>['queued','running'].includes(job.value?.status))
const resumable=computed(()=>['failed','cancelled'].includes(job.value?.status))
const labels={queued:'Oczekuje na rozpoczęcie',running:'Zbieranie danych trwa',completed:'Zbieranie zakończone',failed:'Zbieranie przerwane',cancelled:'Zatrzymano'}
const phase=computed(()=>job.value?.phase==='discovery'?'Wyszukiwanie atrakcji w województwie':'Sprawdzanie informacji, opisy AI i pobieranie zdjęć')
async function api(suffix='',method='GET',body){
 const response=await fetch(`/api/admin/regions/${props.region.slug}/research${suffix}`,{method,headers:{'Content-Type':'application/json',Authorization:'Bearer '+props.token},...(body?{body:JSON.stringify(body)}:{}),signal:controller.signal})
 return readApiJson(response,'Nie udało się odczytać postępu. Spróbuj ponownie.')
}
function schedule(){clearTimeout(timer);if(running.value)timer=setTimeout(poll,3000)}
async function poll(){
 const current=version,previous=job.value
 try{const data=await api();if(current!==version)return;configured.value=data.configured;job.value=data.job;error.value='';if(previous&&previous.id===data.job?.id&&['queued','running'].includes(previous.status)&&!running.value)emit('changed')}
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
 <section class="region-research" aria-label="Automatyczne uzupełnianie województwa">
  <h3>Wyszukaj i dodaj atrakcje z AI</h3>
  <p>System wyszukuje nazwane atrakcje w OpenStreetMap, sprawdza informacje w internecie i zapisuje polskie opisy, współrzędne oraz źródła. Pobiera dostępne zdjęcia z Wikimedia Commons z autorem i licencją. Bez noclegów, winiarni i restauracji.</p>
  <p>Wyszukiwanie korzysta z konta OpenAI skonfigurowanego na serwerze i może naliczać opłaty. Katalog nie gwarantuje wszystkich atrakcji; brak zdjęć i niepotwierdzone informacje pokażemy w raporcie.</p>
  <p v-if="loading" role="status">Odczytuję postęp…</p>
  <p v-else-if="!configured" role="alert">Na serwerze trzeba skonfigurować klucz OpenAI.</p>
  <p v-if="error" role="alert" class="research-error">{{error}} <button class="text-link" @click="poll">Odśwież</button></p>
  <template v-if="job">
   <div class="research-status" role="status" aria-live="polite"><strong>{{labels[job.status]||job.status}}</strong><span v-if="running">{{phase}}</span><span v-if="job.cancel_requested&&running">Zatrzymanie nastąpi po bieżącym zapytaniu.</span></div>
   <progress v-if="job.total" :value="job.processed" :max="job.total" :aria-label="`Sprawdzono ${job.processed} z ${job.total}`"></progress>
   <p>Sprawdzono {{job.processed}} / {{job.total}} · Znaleziono {{job.discovered}} · Dodano {{job.added}} · Uzupełniono {{job.updated}} · Duplikaty {{job.duplicates}} · Do sprawdzenia {{job.review}}</p>
   <p>Ze zdjęciem: {{job.photos}} · Zapisane bez zdjęcia: {{job.missing_photos}}</p>
   <p v-if="job.report?.limited">Znaleziono więcej obiektów niż limit {{job.max_places}}. Zebrano pierwszą partię; zwiększ limit przy kolejnym wyszukiwaniu.</p>
   <p v-if="job.error" class="research-error" role="alert">{{job.error}}</p>
   <details v-if="job.issues?.length"><summary>Braki i uwagi (pierwsze {{job.issues.length}})</summary><ul><li v-for="(issue,index) in job.issues" :key="index"><strong>{{issue.name}}</strong>: {{issue.message}}</li></ul></details>
  </template>
  <p v-if="running">Możesz zamknąć panel. Zadanie działa na serwerze, a postęp jest zapisywany w bazie.</p>
  <div class="research-actions">
   <button v-if="running" class="button outline" :disabled="busy||job.cancel_requested" @click="act('/cancel')">Zatrzymaj zbieranie</button>
   <button v-else-if="resumable&&!region.active" class="button" :disabled="busy||!configured" @click="act('/resume')">Wznów zbieranie</button>
   <template v-if="!running&&!region.active&&!loading">
    <label>Limit obiektów<select v-model.number="limit" :disabled="busy"><option :value="100">100</option><option :value="500">500</option><option :value="1000">1000</option><option :value="5000">5000</option></select></label>
    <button class="button" :disabled="busy||!configured" @click="act('',{max_places:limit})">{{job?'Wyszukaj ponownie':'Wyszukaj i dodaj automatycznie'}}</button>
   </template>
  </div>
  <p v-if="region.active">Automatyczne zbieranie uruchom dla województwa w szkicu.</p>
 </section>
</template>

<style scoped>
.region-research{border:1px solid #d4e2ce;border-radius:10px;padding:20px;margin:24px 0;background:#f7faf4}.region-research h3{margin:0 0 12px;font-size:18px}.region-research p,.region-research li{font-size:12px;line-height:1.8;color:#586b50;margin:12px 0}.research-status{display:flex;flex-direction:column;gap:6px;font-size:13px}.region-research progress{width:100%;accent-color:#19744f;margin-top:14px}.research-actions{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:16px}.research-actions label{display:flex;flex-direction:column;gap:6px;font-size:12px}.research-actions select{padding:10px;border:1px solid #d4dfcb;border-radius:7px;background:#fff}.region-research .research-error{color:#973b2e}.region-research summary{font-size:13px;cursor:pointer}.region-research button:disabled{opacity:.5;cursor:default}
</style>
