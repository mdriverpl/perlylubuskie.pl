<script setup>
import {ref,computed,watch} from 'vue'
import PhotoPicker from './PhotoPicker.vue'
import {uploadPlacePhotos} from '../placePhotos.js'
import {readApiJson} from '../apiResponse.js'
const props=defineProps({place:{type:Object,required:true},user:Object,token:String,online:Boolean})
const emit=defineEmits(['updated'])
const selected=ref(''),files=ref([]),rights=ref(false),busy=ref(false),error=ref(''),opened=ref(false)
const photos=computed(()=>props.place.details?.user_photos||[])
const images=computed(()=>[...new Set([props.place.image,...photos.value.map(p=>p.url)])].filter(Boolean))
const canAdd=computed(()=>props.online&&props.user&&props.place.details?.submitted_by===props.user.id&&photos.value.length<5)
const current=computed(()=>images.value.includes(selected.value)?selected.value:images.value[0])
const author=computed(()=>photos.value.find(p=>p.url===current.value)?.author)
watch(()=>props.place.id,()=>{selected.value='';files.value=[];rights.value=false;error.value='';opened.value=false})
function fallback(event){event.target.onerror=null;event.target.src='/images/heritage-placeholder.svg'}
async function save(){
 if(busy.value||!files.value.length||!rights.value)return
 busy.value=true;error.value=''
 try{
  const photo_ids=await uploadPlacePhotos(files.value,props.token)
  const response=await fetch(`/api/places/${props.place.id}/photos`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${props.token}`},body:JSON.stringify({photo_ids,photo_rights_confirmed:true}),signal:AbortSignal.timeout(15000)})
  const place=await readApiJson(response);emit('updated',place);files.value=[];rights.value=false;opened.value=false
 }catch(e){error.value=e.message}finally{busy.value=false}
}
</script>
<template>
 <div class="place-photos">
  <img class="detail-image" :src="current" @error="fallback" :alt="place.name">
  <div v-if="images.length>1" class="place-photo-thumbs" role="group" aria-label="Zdjęcia miejsca"><button v-for="(image,index) in images" :key="image" type="button" :aria-label="`Pokaż zdjęcie ${index+1}`" :aria-pressed="current===image" @click="selected=image"><img :src="image" alt="" @error="fallback"></button></div>
  <p v-if="author" class="place-photo-author">Zdjęcie: {{author}} · autor miejsca</p>
  <div v-if="canAdd" class="place-photo-editor"><button v-if="!opened" class="button outline" @click="opened=true">Dodaj zdjęcia{{photos.length?` (${photos.length}/5)`:''}}</button><form v-else @submit.prevent="save"><PhotoPicker v-model="files" :max="5-photos.length" :primary="!photos.length" :disabled="busy"/><label class="photo-rights"><input type="checkbox" v-model="rights" required :disabled="busy"> Dodaję własne zdjęcia i zgadzam się na ich publikację w tym serwisie.</label><p v-if="error" class="form-error" role="alert">{{error}}</p><div class="photo-editor-actions"><button class="button" :disabled="busy||!files.length||!rights">{{busy?'Przesyłam zdjęcia…':'Zapisz zdjęcia'}}</button><button type="button" class="button outline" :disabled="busy" @click="opened=false">Anuluj</button></div></form></div>
 </div>
</template>
<style scoped>
.place-photos{min-width:0}.place-photos>.detail-image{width:100%;display:block;object-fit:cover}.place-photo-thumbs{display:flex;gap:8px;overflow-x:auto;padding:12px 20px}.place-photo-thumbs button{flex:0 0 64px;height:55px;border:2px solid transparent;padding:2px;border-radius:7px;background:white}.place-photo-thumbs button[aria-pressed=true]{border-color:#19744f}.place-photo-thumbs img{height:100%;width:100%;object-fit:cover;border-radius:4px}.place-photo-author{font-size:11px;color:#74846d;padding:8px 20px;margin:0}.place-photo-editor{padding:12px 20px;border-bottom:1px solid #e2e9dc}.photo-rights{display:flex;align-items:flex-start;gap:8px;font-size:12px;line-height:1.7;margin:14px 0}.photo-rights input{width:16px;height:16px;flex-shrink:0;margin-top:2px}.photo-editor-actions{display:flex;flex-wrap:wrap;gap:8px}.form-error{color:#a0442c;font-size:12px}
</style>
