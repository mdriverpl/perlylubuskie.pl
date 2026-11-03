<script setup>
import {ref,onMounted} from 'vue'
import AdminTasks from './AdminTasks.vue'
import {readApiJson} from '../apiResponse.js'
const props=defineProps({token:String})
const emit=defineEmits(['login','changed','catalog'])
const loading=ref(true),verified=ref(false),error=ref(''),region=ref(null)
onMounted(async()=>{
 try{
  if(!props.token)return
  const response=await fetch('/api/admin/regions',{headers:{Authorization:'Bearer '+props.token},signal:AbortSignal.timeout(20000)})
  const data=await readApiJson(response,'Nie udało się otworzyć panelu administratora.')
  region.value=data.regions?.[0]||null;verified.value=true
 }catch(e){error.value=e.message}
 finally{loading.value=false}
})
</script>
<template>
 <main class="admin-regions content-width">
  <div class="section-kicker">SUPERADMINISTRATOR</div><h1>Panel administratora</h1>
  <p v-if="loading" role="status">Sprawdzam uprawnienia…</p>
  <p v-if="error" class="admin-error" role="alert">{{error}}</p>
  <template v-if="!loading&&!verified"><p>Panel jest dostępny wyłącznie dla superadministratora.</p><button v-if="!token" class="button" @click="emit('login')">Zaloguj się</button></template>
  <AdminTasks v-if="verified" :token="token" :region="region" @changed="emit('changed')"/>
 </main>
</template>
<style scoped>
.admin-regions{padding-top:35px;padding-bottom:55px}.admin-regions h1{font-size:30px;margin:10px 0 24px}.admin-error{padding:12px 15px;border-radius:8px;font-size:13px;color:#973b2e;background:#fff0e8}@media(max-width:600px){.admin-regions h1{font-size:25px}}
</style>