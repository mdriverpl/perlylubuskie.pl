<script setup>
import {ref,computed,onMounted,onBeforeUnmount} from 'vue'
import Sparkles from 'lucide-vue-next/dist/esm/icons/sparkles.js'
import TravelMap from './TravelMap.vue'
import Send from 'lucide-vue-next/dist/esm/icons/send.js'
import Mail from 'lucide-vue-next/dist/esm/icons/mail.js'
import MessageSquare from 'lucide-vue-next/dist/esm/icons/message-square.js'
import {routeShareLinks} from '../routeShare.js'
const props=defineProps({places:{type:Array,default:()=>[]},online:Boolean,initialPrompt:{type:String,default:''},autoStart:Boolean})
const emit=defineEmits(['use'])
const prompt=ref(props.initialPrompt||'Zaplanuj pieszą trasę dookoła Jeziora Łagowskiego'),busy=ref(false),error=ref(''),proposal=ref(null),enabled=ref(null)
let controller,disposed=false
const shareOpen=ref(false)
const points=computed(()=>proposal.value?.place_ids.map(id=>proposal.value.custom_points.find(p=>p.id===id)||props.places.find(p=>p.id===id)).filter(Boolean)||[])
const kilometers=computed(()=>((proposal.value?.distance_m||0)/1000).toLocaleString('pl-PL',{maximumFractionDigits:1}))
const minutes=computed(()=>Math.round((proposal.value?.duration_s||0)/60))
const shareLinks=computed(()=>routeShareLinks(proposal.value,points.value))
onMounted(async()=>{
 try{const result=await fetch('/api/ai/config',{signal:AbortSignal.timeout(5000)});if(!disposed)enabled.value=result.ok&&(await result.json()).enabled}catch{if(!disposed)enabled.value=false}
 if(!disposed&&props.autoStart&&props.online&&enabled.value===true)generate()
})
onBeforeUnmount(()=>{disposed=true;controller?.abort()})
async function generate(){
 if(disposed||busy.value||!props.online||enabled.value!==true||prompt.value.trim().length<5)return
 busy.value=true;error.value='';proposal.value=null;shareOpen.value=false;controller=new AbortController()
 const timer=setTimeout(()=>controller.abort(),110000)
 try{
  const response=await fetch('/api/ai/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:prompt.value.trim()}),signal:controller.signal})
  const data=await response.json()
  if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Nie udało się przygotować propozycji.')
  if(!data.place_ids?.length||!data.geometry?.coordinates?.length||!Number.isFinite(data.distance_m)||!Array.isArray(data.custom_points))throw Error('Otrzymano niepełną propozycję trasy.')
  if(!disposed)proposal.value=data
 }catch(e){if(!disposed)error.value=e.name==='AbortError'?'Planowanie trwało zbyt długo. Spróbuj ponownie.':e.message}
 finally{clearTimeout(timer);if(!disposed)busy.value=false}
}
</script>
<template>
 <div class="modal-body ai-planner">
  <div class="ai-kicker"><Sparkles :size="18"/>ASYSTENT AI</div>
   <p v-if="busy||enabled===null" role="status" aria-live="polite">Układam trasę…</p>
   <p v-if="!online" class="ai-error" role="status">Planowanie AI wymaga połączenia z internetem i serwerem.</p>
   <p v-else-if="enabled===false" class="ai-error" role="status">AI nie jest teraz dostępne. Sprawdź konfigurację serwera.</p>
   <p v-if="error" class="ai-error" role="alert">{{error}}</p>
   <button v-if="error" class="button full-width ai-retry" :disabled="busy||!online||enabled!==true" @click="generate">Spróbuj ponownie</button>
  <section v-if="proposal" class="ai-proposal" aria-label="Propozycja trasy AI"><h3>{{proposal.name}}</h3><p>{{proposal.description}}</p><p v-for="warning in proposal.warnings||[]" :key="warning" class="ai-access-note" role="note">{{warning}}</p><div class="ai-route-summary">{{proposal.transport==='walk'?'Pieszo':'Rowerem'}} · {{kilometers}} km po trasie · około {{minutes}} min bez postojów</div>
   <div class="ai-route-map"><TravelMap :places="points" :selected="proposal.place_ids" :geometry="proposal.geometry" fit-places/></div>
   <ol><li v-for="point in points" :key="point.id">{{point.name}}</li></ol>
   <p class="ai-sources"><a v-for="source in proposal.sources" :key="source.url" :href="source.url" target="_blank" rel="noopener noreferrer">{{source.title}}</a></p>
   <p class="ai-note">Propozycja AI do sprawdzenia. Przebieg i dystans: BRouter / OpenStreetMap. Sprawdź dostępność ścieżek i warunki w terenie.</p>
   <button class="button full-width ai-use" @click="emit('use',proposal)">Otwórz w planerze</button>
   <div v-if="shareLinks" class="ai-share">
    <button class="button outline full-width" :aria-expanded="shareOpen" aria-controls="ai-share-options" @click="shareOpen=!shareOpen"><Send :size="16"/>Wyślij trasę</button>
    <div v-if="shareOpen" id="ai-share-options"><div class="ai-share-options"><a :href="shareLinks.sms"><MessageSquare :size="16"/>SMS</a><a :href="shareLinks.email"><Mail :size="16"/>E-mail</a></div><p>Otworzy wiadomość z planem i punktami w Google Maps. Wybierz odbiorcę i wyślij.</p></div>
   </div>
  </section>
 </div>
</template>
<style scoped>
.ai-planner{padding:28px 24px}.ai-kicker{display:flex;align-items:center;gap:7px;color:#19744f;font-size:10px;font-weight:700;margin-bottom:12px}.ai-planner h2{font-size:25px;margin-bottom:10px}.ai-planner>p{font-size:12px;line-height:1.7;margin-bottom:15px}.ai-planner form>label{margin:0;font-size:12px}.ai-planner textarea{display:block;width:100%;border:1px solid #d5dfcc;border-radius:8px;padding:10px;font:inherit;font-size:12px;line-height:1.6;resize:vertical}.ai-examples{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 15px}.ai-examples button{font-size:10px;line-height:1.5;text-align:left;border:1px solid #d6e4cb;background:#f1f7eb;color:#497443;border-radius:14px;padding:6px 10px}.ai-generate,.ai-use{font-size:12px;padding:12px}.ai-planner .ai-error{font-size:11px;color:#a54d30;line-height:1.7;margin:12px 0}.ai-proposal{border-top:1px solid #dce4d3;margin-top:22px;padding-top:20px}.ai-proposal h3{font-size:18px;line-height:1.5}.ai-proposal>p{font-size:11px;line-height:1.8;margin:10px 0}.ai-route-summary{font-size:11px;color:#19744f;line-height:1.8;margin-bottom:10px}.ai-route-map{height:260px;overflow:hidden;border-radius:9px}.ai-proposal ol{font-size:11px;line-height:1.8;padding-left:23px;margin-top:12px}.ai-sources a{display:block;color:#19744f;text-decoration:underline}.ai-proposal .ai-note{font-size:10px;color:#7c8e70}
</style>
<style scoped>
.ai-share{margin-top:10px}.ai-share>.button{display:flex;align-items:center;justify-content:center;gap:8px;font-size:12px;padding:12px}.ai-share-options{display:flex;gap:10px;margin-top:10px}.ai-share-options a{flex:1;display:flex;align-items:center;justify-content:center;gap:7px;padding:11px;border:1px solid #d6e4cb;border-radius:8px;color:#19744f;text-decoration:none;font-size:12px;font-weight:600}.ai-share-options a:hover{background:#edf4e6}.ai-share p{font-size:10px;line-height:1.7;color:#7c8e70;margin-top:8px}
</style>
<style scoped>.ai-proposal .ai-access-note{background:#fff3df;border:1px solid #ead4ad;border-radius:8px;padding:10px 12px;color:#895a25;font-size:11px;line-height:1.7}</style>
