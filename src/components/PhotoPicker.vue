<script setup>
import {ref,watch,onBeforeUnmount} from 'vue'
const props=defineProps({modelValue:{type:Array,default:()=>[]},max:{type:Number,default:5},disabled:Boolean,primary:{type:Boolean,default:true}})
const emit=defineEmits(['update:modelValue'])
const previews=ref([]),error=ref('')
function clearUrls(){for(const item of previews.value)URL.revokeObjectURL(item.url)}
watch(()=>props.modelValue,files=>{clearUrls();previews.value=files.map(file=>({file,url:URL.createObjectURL(file)}))},{immediate:true})
onBeforeUnmount(clearUrls)
function choose(event){
 const files=[...event.target.files];event.target.value='';error.value=''
 if(files.some(file=>!['image/jpeg','image/png','image/webp'].includes(file.type))){error.value='Wybierz zdjęcia JPG, PNG lub WebP.';return}
 if(files.some(file=>file.size>10*1024*1024)){error.value='Każde zdjęcie może mieć maksymalnie 10 MB.';return}
 if(props.modelValue.length+files.length>props.max){error.value=`Możesz dodać jeszcze ${Math.max(0,props.max-props.modelValue.length)} zdjęć.`;return}
 emit('update:modelValue',[...props.modelValue,...files])
}
</script>
<template>
 <div class="photo-picker">
  <label class="photo-file-label">Zdjęcia z telefonu lub komputera<input class="place-photo-files" type="file" accept="image/jpeg,image/png,image/webp" multiple :disabled="disabled||modelValue.length>=max" @change="choose"></label>
  <p class="photo-picker-hint">Do {{max}} zdjęć · JPG, PNG, WebP · do 10 MB i 20 megapikseli na zdjęcie. <span v-if="primary">Pierwsze będzie główne.</span></p>
  <div v-if="previews.length" class="photo-preview-list"><div v-for="(item,index) in previews" :key="item.url" class="photo-preview"><img :src="item.url" :alt="`Podgląd zdjęcia ${index+1}`"><button type="button" :disabled="disabled" :aria-label="`Usuń zdjęcie ${index+1}`" @click="emit('update:modelValue',modelValue.filter((_,i)=>i!==index))">×</button><span v-if="index===0&&primary">Główne</span></div></div>
  <p v-if="error" class="form-error" role="alert">{{error}}</p>
 </div>
</template>
<style scoped>
.photo-file-label{display:block;font-size:12px;font-weight:600}.photo-file-label input{display:block;width:100%;margin-top:9px;max-width:100%;font:inherit;padding:10px;border:1px solid #d5e2cb;border-radius:7px;background:#fff}.photo-picker-hint{font-size:11px!important;color:#71826a;line-height:1.7;margin:8px 0!important}.photo-preview-list{display:flex;gap:9px;flex-wrap:wrap;margin:12px 0}.photo-preview{position:relative;width:95px;height:85px}.photo-preview img{width:100%;height:100%;object-fit:cover;border-radius:7px}.photo-preview button{position:absolute;top:3px;right:3px;background:#fff;border:0;border-radius:50%;width:26px;height:26px;font-size:21px;color:#a0442c}.photo-preview span{position:absolute;bottom:4px;left:4px;font-size:9px;background:#fff;padding:3px 5px;border-radius:3px}.form-error{color:#a0442c;font-size:12px}
</style>
