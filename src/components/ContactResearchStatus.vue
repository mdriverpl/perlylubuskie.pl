<script setup>
import {ref,onMounted,onBeforeUnmount,computed} from 'vue'
import {readApiJson} from '../apiResponse.js'
const props=defineProps({token:String})
const state=ref(null),error=ref('')
const percentage=computed(()=>state.value?.total?Math.round(100*(state.value.checked+state.value.failed)/state.value.total):0)
let timer,stopped=false
async function resume(){
 try{
  const response=await fetch('/api/admin/contact-research/resume',{method:'POST',headers:{Authorization:'Bearer '+props.token},signal:AbortSignal.timeout(15000)})
  state.value=await readApiJson(response,'Nie udało się wznowić sprawdzania.');error.value=''
  clearTimeout(timer);await refresh()
 }catch(e){error.value=e.message}
}
async function refresh(){
 try{
  const response=await fetch('/api/admin/contact-research',{headers:{Authorization:'Bearer '+props.token},signal:AbortSignal.timeout(15000)})
  const data=await readApiJson(response,'Nie udało się odczytać postępu sprawdzania kontaktów.')
  if(stopped)return
  state.value=data;error.value=''
 }catch(e){if(!stopped)error.value=e.message}
 if(!stopped&&!state.value?.finished)timer=setTimeout(refresh,10000)
}
onMounted(refresh)
onBeforeUnmount(()=>{stopped=true;clearTimeout(timer)})
</script>
<template>
 <section v-if="state?.total" class="admin-card contact-research-status" aria-label="Sprawdzanie usług i kontaktów">
  <h2>Zamki i pałace — usługi i kontakt</h2>
  <p>{{state.finished?'Sprawdzanie zakończone.':state.blocked?'Sprawdzanie wstrzymane.':'Sprawdzam na serwerze produkcyjnym…'}}</p>
  <progress :value="state.checked+state.failed" :max="state.total" :aria-label="`Sprawdzono ${state.checked} z ${state.total}`"></progress>
  <p>Sprawdzono {{state.checked}} / {{state.total}} · {{percentage}}%<span v-if="state.failed"> · Nieudane: {{state.failed}}</span></p>
  <p v-if="state.error||error" role="status">{{state.error||error}}</p>
  <button v-if="state.blocked||state.failed" class="button outline" @click="resume">Wznów sprawdzanie</button>
  <small>Wyniki zapisują się na bieżąco. Możesz zamknąć panel. Brak potwierdzenia pozostaje oznaczony jako brak informacji.</small>
 </section>
</template>
<style scoped>.contact-research-status progress{width:100%;height:18px;accent-color:#18734f}.contact-research-status small{color:#718369;line-height:1.6}</style>
