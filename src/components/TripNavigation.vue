<script setup>
import {ref,watch,onMounted,onBeforeUnmount} from 'vue'
import TravelMap from './TravelMap.vue'
import ArrowLeft from 'lucide-vue-next/dist/esm/icons/arrow-left.js'
import LocateFixed from 'lucide-vue-next/dist/esm/icons/locate-fixed.js'
import SlidersHorizontal from 'lucide-vue-next/dist/esm/icons/sliders-horizontal.js'
import Route from 'lucide-vue-next/dist/esm/icons/route.js'
import Clock3 from 'lucide-vue-next/dist/esm/icons/clock-3.js'
const props=defineProps({geometry:Object,distance:String,duration:String,position:Object,locating:Boolean,loading:Boolean,error:String,locationError:String})
const emit=defineEmits(['back','refresh','retry'])
const host=ref(null),backButton=ref(null),options=ref(false)
const emptyPlaces=[]
let initialTrackOnly=false
try{initialTrackOnly=localStorage.getItem('perly:navigation-track-only')==='true'}catch{}
const trackOnly=ref(initialTrackOnly)
watch(trackOnly,value=>{try{localStorage.setItem('perly:navigation-track-only',String(value))}catch{}})
const previousFocus=document.activeElement,previousOverflow=document.body.style.overflow
onMounted(()=>{document.body.style.overflow='hidden';backButton.value?.focus()})
onBeforeUnmount(()=>{document.body.style.overflow=previousOverflow;previousFocus?.focus?.()})
function trap(event){
 if(event.key!=='Tab')return
 const items=[...host.value.querySelectorAll('button:not([disabled]),input,a[href]')]
 const first=items[0],last=items.at(-1)
 if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus()}
 else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus()}
}
</script>
<template>
 <section ref="host" class="trip-navigation" role="dialog" aria-modal="true" aria-label="Nawigacja wycieczki" @keydown="trap" @keydown.esc.stop="emit('back')">
  <TravelMap :places="emptyPlaces" :geometry="geometry" :user-location="position" :track-only="trackOnly" directional-position route-directions minimal/>
  <div class="navigation-toolbar"><button ref="backButton" class="navigation-back" @click="emit('back')"><ArrowLeft :size="19"/>Cofnij</button><button :aria-expanded="options" aria-controls="navigation-options" @click="options=!options"><SlidersHorizontal :size="19"/>Opcje</button></div>
  <div v-if="options" id="navigation-options" class="navigation-options"><label><input v-model="trackOnly" type="checkbox">Tylko ślad, bez mapy</label></div>
  <div v-if="loading||error||locationError" class="navigation-status" role="status"><span v-if="loading">Wyznaczam trasę…</span><span v-else-if="error">{{error}} <button @click="emit('retry')">Spróbuj ponownie</button></span><span v-if="locationError">{{locationError}}</span></div>
  <div v-if="geometry" class="navigation-metrics" aria-label="Dystans i czas całej trasy"><div><Route :size="19"/><span><small>Cała trasa</small><strong>{{distance}} km</strong></span></div><div><Clock3 :size="19"/><span><small>Czas bez postojów</small><strong>{{duration}}</strong></span></div></div>
  <button class="navigation-refresh" :disabled="locating" :aria-busy="locating" @click="emit('refresh')"><LocateFixed :size="20"/>{{locating?'Ustalam pozycję…':'Odśwież pozycję'}}</button>
  <a v-if="trackOnly" class="navigation-credit" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">Trasa © OpenStreetMap</a>
 </section>
</template>
<style scoped>
.trip-navigation{position:fixed;inset:0;z-index:3000;background:#f6f8f2;height:100dvh}.trip-navigation>.travel-map{height:100%;min-height:100%}.navigation-toolbar{position:absolute;z-index:600;top:max(14px,env(safe-area-inset-top));left:14px;right:14px;display:flex;justify-content:space-between;gap:12px;pointer-events:none}.navigation-toolbar button,.navigation-refresh{display:flex;align-items:center;justify-content:center;gap:8px;min-height:46px;padding:12px 16px;border:1px solid #d3dfc8;border-radius:12px;background:#fff;color:#24563b;font-size:13px;font-weight:600;box-shadow:0 3px 16px #153c2926;pointer-events:auto}.navigation-toolbar button:focus-visible,.navigation-refresh:focus-visible{outline:3px solid #19744f;outline-offset:3px}.navigation-options{position:absolute;z-index:650;top:calc(max(14px,env(safe-area-inset-top)) + 57px);right:14px;padding:18px;background:white;border:1px solid #d3dfc8;border-radius:12px;box-shadow:0 4px 20px #153c2926;font-size:13px;color:#24563b}.navigation-options label{display:flex;align-items:center;gap:10px;min-height:30px}.navigation-options input{width:18px;height:18px;accent-color:#19744f}.navigation-refresh{position:absolute;z-index:600;bottom:max(28px,env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);white-space:nowrap;background:#19744f;color:white;border-color:#19744f}.navigation-refresh:disabled{opacity:.7}.navigation-status{position:absolute;z-index:600;top:78px;left:14px;max-width:calc(100% - 28px);padding:10px 13px;border-radius:10px;background:#fffffff0;color:#6c775c;font-size:12px;line-height:1.7;box-shadow:0 2px 12px #153c2918}.navigation-status>span{display:block}.navigation-status button{color:#19744f;text-decoration:underline}.navigation-credit{position:absolute;bottom:3px;right:5px;background:#ffffffc9;color:#536c4b;padding:2px 5px;font-size:9px}.trip-navigation :deep(.leaflet-top.leaflet-left){top:76px}
</style>
<style scoped>
.navigation-metrics{position:absolute;z-index:600;bottom:calc(max(28px,env(safe-area-inset-bottom)) + 62px);left:14px;right:14px;max-width:360px;margin:auto;display:grid;grid-template-columns:1fr 1fr;gap:12px;background:#fffffff5;border:1px solid #d3dfc8;border-radius:14px;padding:14px 16px;box-shadow:0 3px 16px #153c2926;color:#24563b;pointer-events:none}.navigation-metrics>div{display:flex;align-items:center;gap:10px;min-width:0}.navigation-metrics svg{flex-shrink:0;color:#19744f}.navigation-metrics small{display:block;font-size:10px;line-height:1.5;color:#718369}.navigation-metrics strong{display:block;font-size:17px;line-height:1.5}.navigation-metrics>div+div{border-left:1px solid #dce5d4;padding-left:12px}
@media(max-width:360px){.navigation-metrics{gap:8px;padding:12px}.navigation-metrics>div{gap:7px}.navigation-metrics strong{font-size:15px}}
</style>
