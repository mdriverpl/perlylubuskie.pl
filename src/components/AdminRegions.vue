<script setup>
import {ref,computed,onMounted,watch,nextTick} from 'vue'
import RegionResearch from './RegionResearch.vue'
import {readApiJson} from '../apiResponse.js'
const props=defineProps({token:String})
const emit=defineEmits(['login','changed','catalog'])
const verified=ref(false),loading=ref(true),busy=ref(false),error=ref(''),message=ref('')
const regions=ref([]),options=ref([]),types=ref([]),slug=ref(''),newSlug=ref('kujawsko-pomorskie')
const core=['castle','palace','lake','nature','heritage','leisure']
const allowed=ref([...core]),records=ref([]),fileRecords=ref(null),fileName=ref(''),editing=ref(null)
const blank=()=>({name:'',subtitle:'',location:'',description:'',place_type:'heritage',lat:null,lng:null,image:'',source_url:''})
const draft=ref(blank()),researchKey=ref(0),researchLimit=ref(5000),manualOptions=ref(false),researchRunning=ref(false)
const region=computed(()=>regions.value.find(r=>r.slug===slug.value))
const availableOptions=computed(()=>options.value.filter(o=>!regions.value.some(r=>r.slug===o.slug)))
const placeTypes=computed(()=>types.value.filter(t=>region.value?.allowed_types.includes(t.id)))
async function api(path,method='GET',body){
 const response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json',Authorization:'Bearer '+props.token},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(20000)})
 return readApiJson(response,'Panel administracyjny jest chwilowo niedostępny. Spróbuj ponownie.')
}
async function refresh(){
 const data=await api('/admin/regions')
 regions.value=data.regions;options.value=data.options;types.value=data.types;verified.value=true
 if(!regions.value.some(r=>r.slug===slug.value))slug.value=regions.value.find(r=>!r.active)?.slug||regions.value[0]?.slug||''
 if(!availableOptions.value.some(r=>r.slug===newSlug.value))newSlug.value=availableOptions.value[0]?.slug||''
}
watch(placeTypes,value=>{if(value.length&&!value.some(t=>t.id===draft.value.place_type))draft.value.place_type=value[0].id})
let listVersion=0
watch(slug,async value=>{
 const version=++listVersion;records.value=[];editing.value=null;draft.value=blank();fileRecords.value=null;fileName.value='';manualOptions.value=false;researchRunning.value=false
 try{const data=value?await api('/admin/regions/'+value+'/places'):[];if(version===listVersion)records.value=data}
 catch(e){if(version===listVersion)error.value=e.message}
})
onMounted(async()=>{if(!props.token){loading.value=false;return}try{await refresh()}catch(e){error.value=e.message}finally{loading.value=false}})
async function act(task){
 if(busy.value)return
 busy.value=true;error.value='';message.value=''
 try{await task()}catch(e){error.value=e.message}finally{busy.value=false}
}
async function researchChanged(){
 const selected=slug.value,version=++listVersion
 try{
  const [data]=await Promise.all([api('/admin/regions/'+selected+'/places'),refresh()])
  if(version===listVersion&&slug.value===selected){records.value=data;emit('changed')}
 }catch(e){if(version===listVersion)error.value=e.message}
}
function createRegion(automatic=true){return act(async()=>{
 await api('/admin/regions','POST',{slug:newSlug.value,allowed_types:allowed.value})
 const added=newSlug.value;await refresh();slug.value=added
 if(automatic){await api('/admin/regions/'+added+'/research','POST',{max_places:researchLimit.value});researchKey.value++;message.value='AI zbiera dane w tle. Postęp znajdziesz poniżej. Województwo pozostaje szkicem.'}
 else message.value='Utworzono pusty szkic województwa.'
})}
function publish(){return act(async()=>{
 const active=!region.value.active
 await api('/admin/regions/'+slug.value,'PATCH',{active,finish_research:active&&researchRunning.value});researchKey.value++;await refresh();emit('changed');message.value=active?'Województwo jest opublikowane.':'Województwo przeniesiono do szkicu.'
})}
async function edit(place){manualOptions.value=true;editing.value=place.id;draft.value={...blank(),...place,image:place.image?.startsWith('https://')?place.image:'',place_type:place.details?.kind||place.category,source_url:place.details?.source_url||''};await nextTick();document.getElementById('admin-place-editor')?.scrollIntoView({behavior:'smooth',block:'center'})}
function savePlace(){return act(async()=>{
 const payload={...draft.value,region:slug.value}
 await api(editing.value?'/admin/places/'+editing.value:'/places',editing.value?'PUT':'POST',payload)
 records.value=await api('/admin/regions/'+slug.value+'/places');await refresh();draft.value=blank();editing.value=null;emit('changed');message.value='Miejsce zapisane.'
})}
async function readFile(event){
 fileRecords.value=null;error.value=''
 const file=event.target.files?.[0];if(!file)return
 fileName.value=file.name
 if(file.size>4000000){error.value='Plik może mieć maksymalnie 4 MB.';return}
 try{
  const parsed=JSON.parse(await file.text());const rows=Array.isArray(parsed)?parsed:parsed?.places
  if(!Array.isArray(rows)||!rows.length||rows.length>500)throw Error('Plik musi zawierać od 1 do 500 miejsc w tablicy places.')
  const blocked=rows.some(row=>!row||!region.value.allowed_types.includes(row.place_type))
  if(blocked)throw Error('Plik zawiera rodzaj miejsca wyłączony w tym województwie.')
  fileRecords.value=rows
 }catch(e){error.value=e.name==='SyntaxError'?'Plik nie zawiera poprawnych danych JSON.':e.message}
}
function importFile(){return act(async()=>{
 const result=await api('/admin/regions/'+slug.value+'/import','POST',{places:fileRecords.value})
 records.value=await api('/admin/regions/'+slug.value+'/places');await refresh();fileRecords.value=null;emit('changed');message.value=`Dodano ${result.added} miejsc. Pominięto ${result.skipped} duplikatów.`
})}
function downloadTemplate(){
 const sample={places:[{name:'Nazwa atrakcji',subtitle:'Krótki opis',location:'Miejscowość',description:'Opis atrakcji',place_type:'heritage',lat:53.01,lng:18.60,image:'',source_url:''}]}
 const url=URL.createObjectURL(new Blob([JSON.stringify(sample,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='wzor-miejsc.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
</script>

<template>
 <main class="admin-regions content-width">
  <div class="section-kicker">SUPERADMINISTRATOR</div><h1>Panel administratora</h1>
  <p v-if="loading" role="status">Sprawdzam uprawnienia…</p>
  <template v-else-if="!verified"><p>Panel jest dostępny wyłącznie dla superadministratora.</p><button v-if="!token" class="button" @click="emit('login')">Zaloguj się</button></template>
  <p v-if="error" class="admin-error" role="alert">{{error}}</p><p v-if="message" class="admin-message" role="status">{{message}}</p>
  <template v-if="verified">
   <section class="admin-card"><h2>Dodaj województwo</h2><p>AI doda opisy i zdjęcia. Bez noclegów, winiarni i restauracji. Korzysta z płatnego konta OpenAI.</p>
    <form @submit.prevent="createRegion(true)"><fieldset :disabled="busy"><label>Województwo<select id="admin-new-region" v-model="newSlug" required><option v-for="option in availableOptions" :key="option.slug" :value="option.slug">{{option.name}}</option></select></label><details class="admin-options"><summary>Ustawienia</summary><div class="admin-types" role="group" aria-label="Kategorie województwa"><label v-for="type in types" :key="type.id"><input v-model="allowed" type="checkbox" :value="type.id">{{type.name}}</label></div><label>Limit wyszukiwanych obiektów<select v-model.number="researchLimit"><option :value="100">100</option><option :value="500">500</option><option :value="1000">1000</option><option :value="5000">5000</option></select></label><button class="text-link" :disabled="!newSlug||!allowed.length" type="button" @click="createRegion(false)">Utwórz pusty szkic</button></details><button class="button" :disabled="!newSlug||!allowed.length" type="submit">Dodaj i uruchom AI</button></fieldset></form>
   </section>
   <section v-if="regions.length" class="admin-card"><div class="admin-heading"><h2>Zarządzaj regionem</h2><button v-if="region?.active" class="text-link" @click="emit('catalog',slug)">Otwórz katalog</button></div>
    <label>Województwo<select id="admin-region" v-model="slug" :disabled="busy"><option v-for="item in regions" :key="item.slug" :value="item.slug">{{item.name}} · {{item.active?'Opublikowane':'Szkic'}} · {{item.place_count}} miejsc</option></select></label>
    <template v-if="region">
     <RegionResearch :token="token" :region="region" :reload-key="researchKey" @changed="researchChanged" @status="researchRunning=$event"/>
     <button v-if="!region.active" class="button admin-publish" :disabled="busy||!region.place_count" @click="publish">{{researchRunning?'Zakończ i opublikuj':'Opublikuj województwo'}}</button>
     <p v-if="!region.active&&researchRunning">Możesz zakończyć wyszukiwanie i opublikować już zapisane miejsca.</p>
     <details class="admin-options admin-manual" :open="manualOptions" @toggle="manualOptions=$event.target.open"><summary>Opcje dodatkowe · {{records.length}} miejsc</summary>
     <p>Dozwolone: {{placeTypes.map(type=>type.name).join(', ')}}.</p>
     <button v-if="region.active" class="text-link" :disabled="busy||region.slug==='lubuskie'" @click="publish">Przenieś do szkicu</button>
     <form id="admin-place-editor" class="admin-editor" @submit.prevent="savePlace"><fieldset :disabled="busy"><h3>{{editing?'Edytuj miejsce':'Dodaj atrakcję'}}</h3><div class="admin-fields"><label>Nazwa<input id="admin-place-name" v-model="draft.name" required maxlength="200"></label><label>Miejscowość<input id="admin-place-location" v-model="draft.location" required maxlength="200"></label><label>Rodzaj<select id="admin-place-type" v-model="draft.place_type" required><option v-for="type in placeTypes" :key="type.id" :value="type.id">{{type.name}}</option></select></label><label>Krótki opis<input v-model="draft.subtitle" maxlength="250"></label><label>Szerokość geograficzna<input id="admin-place-lat" v-model.number="draft.lat" required type="number" min="-90" max="90" step="any"></label><label>Długość geograficzna<input id="admin-place-lng" v-model.number="draft.lng" required type="number" min="-180" max="180" step="any"></label></div><label>Opis<textarea id="admin-place-description" v-model="draft.description" required maxlength="2000" rows="3"></textarea></label><div class="admin-fields"><label>Zdjęcie (link HTTPS, opcjonalnie)<input v-model="draft.image" type="url" pattern="https://.*" maxlength="2000"></label><label>Źródło informacji (link HTTPS, opcjonalnie)<input v-model="draft.source_url" type="url" pattern="https://.*" maxlength="2000"></label></div><button class="button" type="submit">{{editing?'Zapisz zmiany':'Dodaj miejsce'}}</button><button v-if="editing" type="button" class="text-link" @click="editing=null;draft=blank()">Anuluj edycję</button></fieldset></form>
     <div class="admin-import"><h3>Importuj miejsca z pliku</h3><p>Wybierz plik JSON z tablicą „places”, do 500 pozycji. Duplikaty nazwy i współrzędnych zostaną pominięte. Błędny plik nie zostanie zaimportowany.</p><button class="text-link" @click="downloadTemplate">Pobierz wzór JSON</button><label>Plik JSON<input id="admin-import-file" type="file" accept=".json,application/json" :disabled="busy" @change="readFile"></label><p v-if="fileRecords">{{fileName}} · {{fileRecords.length}} miejsc gotowych do importu</p><button class="button" :disabled="busy||!fileRecords" @click="importFile">Importuj miejsca</button></div>
     <h3 class="admin-list-title">Atrakcje w regionie ({{records.length}})</h3><p v-if="!records.length">Uruchom zbieranie AI powyżej, aby automatycznie dodać atrakcje.</p><ul class="admin-place-list"><li v-for="place in records" :key="place.id"><span><strong>{{place.name}}</strong><small>{{place.location}}</small></span><button class="text-link" :disabled="busy" @click="edit(place)">Edytuj</button></li></ul>
     </details>
    </template>
   </section>
  </template>
 </main>
</template>

<style scoped>
.admin-options{margin:16px 0}.admin-options summary{cursor:pointer;font-size:12px;color:#526b46;padding:8px 0}.admin-manual{border-top:1px solid #e0e8d8;margin-top:22px;padding-top:12px}.admin-publish{margin-top:12px}.admin-regions{padding-top:35px;padding-bottom:55px}.admin-regions h1{font-size:30px;margin:10px 0 24px}.admin-card{border:1px solid #dbe4d3;background:#fff;border-radius:12px;padding:24px;margin:20px 0}.admin-card h2{font-size:21px}.admin-card h3{font-size:17px;margin-bottom:12px}.admin-card p{font-size:12px;line-height:1.8;color:#6f8064;margin:10px 0 17px}.admin-card label{display:flex;flex-direction:column;gap:7px;font-size:12px;margin:14px 0}.admin-card input,.admin-card select,.admin-card textarea{padding:11px;border:1px solid #d4dfcb;border-radius:7px;font:inherit;max-width:100%;min-width:0;background:#fff}.admin-card input:focus-visible,.admin-card select:focus-visible,.admin-card textarea:focus-visible{outline:2px solid #19744f}.admin-card fieldset{border:0;padding:0;min-width:0}.admin-card .admin-types{display:flex;flex-wrap:wrap;gap:8px 20px;margin:15px 0}.admin-types label{flex-direction:row;align-items:center;margin:5px 0}.admin-types input{accent-color:#19744f}.admin-fields{display:grid;grid-template-columns:1fr 1fr;gap:0 18px}.admin-editor,.admin-import{margin-top:28px;padding-top:24px;border-top:1px solid #e0e8d8}.admin-error,.admin-message{padding:12px 15px;border-radius:8px;font-size:13px;line-height:1.7;margin:14px 0}.admin-error{color:#973b2e;background:#fff0e8}.admin-message{color:#1b623d;background:#ebf5e5}.admin-heading{display:flex;align-items:center;justify-content:space-between;gap:15px}.admin-place-list{list-style:none;padding:0}.admin-place-list li{display:flex;align-items:center;justify-content:space-between;gap:15px;border-bottom:1px solid #e4ebde;padding:13px 0}.admin-place-list small{display:block;color:#788970;font-size:11px;margin-top:4px}.admin-place-list strong{font-size:13px;overflow-wrap:anywhere}.admin-card .admin-list-title{margin-top:28px}.admin-card button:disabled{opacity:.5;cursor:default}.admin-editor .text-link{display:inline-flex;margin-left:15px}@media(max-width:600px){.admin-fields{grid-template-columns:1fr}.admin-card{padding:18px}.admin-regions h1{font-size:25px}.admin-heading{flex-wrap:wrap}}
</style>
