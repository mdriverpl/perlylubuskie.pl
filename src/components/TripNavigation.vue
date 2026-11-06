<script setup>
import {ref,computed,watch,onMounted,onBeforeUnmount} from 'vue'
import TravelMap from './TravelMap.vue'
import ArrowLeft from 'lucide-vue-next/dist/esm/icons/arrow-left.js'
import LocateFixed from 'lucide-vue-next/dist/esm/icons/locate-fixed.js'
import SlidersHorizontal from 'lucide-vue-next/dist/esm/icons/sliders-horizontal.js'
import Route from 'lucide-vue-next/dist/esm/icons/route.js'
import Clock3 from 'lucide-vue-next/dist/esm/icons/clock-3.js'
import Share2 from 'lucide-vue-next/dist/esm/icons/share-2.js'
import X from 'lucide-vue-next/dist/esm/icons/x.js'
import {positionShare} from '../sharePosition.js'
import {trackRouteKey,addTrackPoint,readNavigationTrack,saveNavigationTrack} from '../navigationTrack.js'
import {preferredOsmTone,rememberOsmTone} from '../mapPreferences.js'
import {useNearbyPeople} from '../useNearbyPeople.js'
import UsersRound from 'lucide-vue-next/dist/esm/icons/users-round.js'
const props=defineProps({geometry:Object,distance:String,duration:String,position:Object,user:Object,token:{type:String,default:''},places:{type:Array,default:()=>[]},offline:Boolean,locating:Boolean,loading:Boolean,error:String,locationError:String})
const emit=defineEmits(['back','refresh','retry'])
const nearby=useNearbyPeople({position:computed(()=>props.position),token:computed(()=>props.token),requestGps:()=>emit('refresh')})
const host=ref(null),backButton=ref(null),options=ref(false)
const sharing=ref(false),shareBusy=ref(false),shareNotice=ref(''),share= computed(()=>positionShare(props.position))
const canNativeShare=typeof navigator.share==='function'
const travelledTrack=ref([])
const positionFocus=ref(null)
function showPosition(){if(props.position){positionFocus.value={...props.position,zoom:16};sharing.value=false}}
let routeKey=null
watch(()=>trackRouteKey(props.geometry),key=>{
 if(!key||key===routeKey)return
 routeKey=key;travelledTrack.value=readNavigationTrack(key)
 travelledTrack.value=addTrackPoint(travelledTrack.value,props.position)
 saveNavigationTrack(routeKey,travelledTrack.value)
},{immediate:true})
watch(()=>props.position,point=>{
 travelledTrack.value=addTrackPoint(travelledTrack.value,point)
 saveNavigationTrack(routeKey,travelledTrack.value)
},{immediate:true})
function openShare(){sharing.value=!sharing.value;options.value=false;shareNotice.value='';if(sharing.value&&!props.position&&!props.locating)emit('refresh')}
async function nativeShare(){
 if(!share.value||shareBusy.value)return
 shareNotice.value='';shareBusy.value=true
 try{
  if(navigator.share)await navigator.share({title:'Moja pozycja GPS',text:share.value.text})
  else if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(share.value.text);shareNotice.value='Skopiowano pozycję i link. Wklej je do wiadomości.'}
  else shareNotice.value='Wybierz SMS lub WhatsApp albo skopiuj współrzędne i link poniżej.'
 }catch(error){if(error.name!=='AbortError')shareNotice.value='Nie udało się udostępnić pozycji. Wybierz SMS lub WhatsApp.'}
 finally{shareBusy.value=false}
}
const emptyPlaces=[]
let initialTrackOnly=false
try{initialTrackOnly=localStorage.getItem('perly:navigation-track-only')==='true'}catch{}
const trackOnly=ref(initialTrackOnly)
const osmTone=ref(preferredOsmTone())
function setOsmTone(value){osmTone.value=value;rememberOsmTone(value)}
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
 <section ref="host" class="trip-navigation" role="dialog" aria-modal="true" aria-label="Nawigacja wycieczki" @keydown="trap" @keydown.esc.stop="sharing?sharing=false:emit('back')">
  <TravelMap :places="emptyPlaces" :nearby-people="nearby.people.value" :endpoint-places="places" :travelled-track="travelledTrack" :focus-location="positionFocus" :geometry="geometry" :user-location="position" :track-only="trackOnly" directional-position route-directions minimal/>
  <div class="navigation-toolbar"><button ref="backButton" class="navigation-back" @click="emit('back')"><ArrowLeft :size="19"/>Cofnij</button><button class="navigation-share" :aria-expanded="sharing" aria-controls="navigation-share-panel" @click="openShare"><Share2 :size="19"/><span>Wyślij pozycję</span></button><button :aria-expanded="options" aria-controls="navigation-options" @click="options=!options;sharing=false"><SlidersHorizontal :size="19"/>Opcje</button></div>
  <section v-if="sharing" id="navigation-share-panel" class="navigation-share-panel" aria-label="Wyślij aktualną pozycję GPS">
   <div class="position-share-heading"><h2><LocateFixed :size="20"/>Twoja pozycja GPS</h2><button aria-label="Zamknij udostępnianie pozycji" @click="sharing=false"><X :size="20"/></button></div>
   <template v-if="share"><p class="position-coordinates">{{share.coordinates}}</p><p v-if="Number.isFinite(position.accuracy)" class="position-accuracy">Dokładność GPS: około {{Math.round(position.accuracy)}} m</p><p v-if="locationError" class="position-share-warning">{{locationError}} Ostatnia znana pozycja — odśwież GPS przed wysłaniem.</p><div class="position-share-links"><a class="position-sms" :href="share.sms">SMS</a><a class="position-whatsapp" :href="share.whatsapp" target="_blank" rel="noopener noreferrer">WhatsApp</a><button :disabled="shareBusy" @click="nativeShare">{{canNativeShare?'Udostępnij…':'Kopiuj pozycję'}}</button></div><a class="position-google" :href="share.url" target="_blank" rel="noopener noreferrer">Otwórz punkt w Mapach Google ↗</a><small>Wiadomość zawiera tę pozycję i link. To jednorazowy punkt, bez śledzenia na żywo.</small></template>
   <p v-else>{{locating?'Ustalam pozycję GPS…':locationError||'Brak aktualnej pozycji. Włącz lokalizację i odśwież GPS.'}}</p>
   <button v-if="share" class="position-refresh position-show-map" @click="showPosition"><LocateFixed :size="16"/>Pokaż punkt na mapie</button>
   <button class="position-refresh" :disabled="locating" @click="emit('refresh')"><LocateFixed :size="16"/>{{locating?'Ustalam pozycję…':'Odśwież GPS'}}</button>
   <p v-if="shareNotice" role="status">{{shareNotice}}</p>
  </section>
  <div v-if="options" id="navigation-options" class="navigation-options">
   <label><input v-model="trackOnly" type="checkbox">Tylko ślad, bez mapy</label>
   <div v-if="!trackOnly" class="navigation-map-tone"><span>Kolory OpenStreetMap</span><div role="group" aria-label="Wygląd mapy OpenStreetMap"><button :aria-pressed="osmTone==='light'" @click="setOsmTone('light')">Jasna</button><button :aria-pressed="osmTone==='standard'" @click="setOsmTone('standard')">Standardowa</button></div></div>
   <div class="navigation-people-options">
    <label><input v-model="nearby.enabled.value" class="nearby-sharing-toggle" type="checkbox" :disabled="!user||!token||nearby.stopping.value">Pokaż mnie osobom w pobliżu</label>
    <p>Zalogowani uczestnicy w promieniu 5 km zobaczą Twoje imię i dokładną pozycję. Zobaczysz też osoby, które włączyły tę opcję.</p>
    <p>Udostępnianie działa podczas otwartej nawigacji i wymaga internetu. Pozycja znika po 2 minutach bez aktualizacji. Nie zapisujemy historii.</p>
    <p v-if="!user||!token" class="nearby-login-note">Zaloguj się na stronie, aby włączyć udostępnianie.</p>
    <p v-if="nearby.error.value" class="nearby-sharing-error" role="status">{{nearby.error.value}}</p>
    <p v-else-if="nearby.enabled.value" role="status">{{nearby.connected.value?'Udostępnianie włączone. Osób w pobliżu: '+nearby.people.value.length:'Łączę i czekam na aktualną pozycję GPS…'}}</p>
   </div>
  </div>
  <div v-if="nearby.enabled.value" class="nearby-people-status" role="status"><button @click="options=true;sharing=false"><UsersRound :size="17"/>{{nearby.connected.value?'Widoczny · osoby w pobliżu: '+nearby.people.value.length:nearby.error.value?'Pozycja nie jest aktualizowana':'Łączę z osobami w pobliżu…'}}</button><button class="nearby-sharing-stop" @click="nearby.enabled.value=false">Zatrzymaj</button></div>
  <p v-if="!nearby.enabled.value&&nearby.error.value" class="nearby-people-stop-error" role="status">{{nearby.error.value}}</p>
  <div v-if="loading||error||locationError" class="navigation-status" role="status"><span v-if="loading">Wyznaczam trasę…</span><span v-else-if="error">{{error}} <button @click="emit('retry')">Spróbuj ponownie</button></span><span v-if="locationError">{{locationError}}</span></div>
  <div v-if="geometry" class="navigation-metrics" aria-label="Dystans i czas całej trasy"><div><Route :size="19"/><span><small>Cała trasa</small><strong>{{distance}} km</strong></span></div><div><Clock3 :size="19"/><span><small>Czas bez postojów</small><strong>{{duration}}</strong></span></div></div>
  <p v-if="offline&&geometry" class="navigation-offline-note" role="status">Zapisana trasa offline · bez przeliczania</p>
  <button class="navigation-refresh" :disabled="locating" :aria-busy="locating" @click="emit('refresh')"><LocateFixed :size="20"/>{{locating?'Ustalam pozycję…':'Odśwież pozycję'}}</button>
  <a v-if="trackOnly" class="navigation-credit" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">Trasa © OpenStreetMap</a>
 </section>
</template>
<style scoped>
.trip-navigation{position:fixed;inset:0;z-index:3000;background:#f6f8f2;height:100dvh}.trip-navigation>.travel-map{height:100%;min-height:100%}.navigation-toolbar{position:absolute;z-index:600;top:max(14px,env(safe-area-inset-top));left:14px;right:14px;display:flex;justify-content:space-between;gap:12px;pointer-events:none}.navigation-toolbar button,.navigation-refresh{display:flex;align-items:center;justify-content:center;gap:8px;min-height:46px;padding:12px 16px;border:1px solid #d3dfc8;border-radius:12px;background:#fff;color:#24563b;font-size:13px;font-weight:600;box-shadow:0 3px 16px #153c2926;pointer-events:auto}.navigation-toolbar button:focus-visible,.navigation-refresh:focus-visible{outline:3px solid #19744f;outline-offset:3px}.navigation-options{position:absolute;z-index:650;top:calc(max(14px,env(safe-area-inset-top)) + 57px);right:14px;padding:18px;background:white;border:1px solid #d3dfc8;border-radius:12px;box-shadow:0 4px 20px #153c2926;font-size:13px;color:#24563b}.navigation-options label{display:flex;align-items:center;gap:10px;min-height:30px}.navigation-options input{width:18px;height:18px;accent-color:#19744f}.navigation-refresh{position:absolute;z-index:600;bottom:max(28px,env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);white-space:nowrap;background:#19744f;color:white;border-color:#19744f}.navigation-refresh:disabled{opacity:.7}.navigation-status{position:absolute;z-index:600;top:78px;left:14px;max-width:calc(100% - 28px);padding:10px 13px;border-radius:10px;background:#fffffff0;color:#6c775c;font-size:12px;line-height:1.7;box-shadow:0 2px 12px #153c2918}.navigation-status>span{display:block}.navigation-status button{color:#19744f;text-decoration:underline}.navigation-credit{position:absolute;bottom:3px;right:5px;background:#ffffffc9;color:#536c4b;padding:2px 5px;font-size:9px}.trip-navigation :deep(.leaflet-top.leaflet-left){top:76px}
</style>
<style scoped>
.nearby-people-stop-error{position:absolute;z-index:600;bottom:calc(max(28px,env(safe-area-inset-bottom)) + 185px);left:14px;right:14px;max-width:360px;margin:auto;padding:11px 13px;border:1px solid #e4d3af;border-radius:12px;background:#fffaf0f5;color:#805c2e;font-size:11px;line-height:1.6}
</style>
<style scoped>
.navigation-options{max-width:min(350px,calc(100% - 28px));max-height:calc(100dvh - 115px);overflow:auto}.navigation-people-options{border-top:1px solid #e2e9dc;margin-top:15px;padding-top:15px}.navigation-people-options label{font-size:12px;font-weight:600;line-height:1.5}.navigation-people-options input{flex-shrink:0}.navigation-people-options p{font-size:11px;line-height:1.65;color:#6d7e63;margin:9px 0 0}.navigation-people-options .nearby-sharing-error{color:#97612e}.navigation-people-options .nearby-login-note{color:#24563b}.nearby-people-status{position:absolute;z-index:600;bottom:calc(max(28px,env(safe-area-inset-bottom)) + 185px);left:14px;right:14px;max-width:360px;margin:auto;display:flex;align-items:center;gap:5px;border:1px solid #b8cfa8;border-radius:12px;background:#fffffff5;padding:5px;box-shadow:0 3px 12px #153c2920;color:#24563b}.nearby-people-status button{display:flex;align-items:center;justify-content:center;gap:7px;min-height:38px;padding:8px;border:0;border-radius:7px;color:#24563b;background:transparent;font:600 10px/1.5 system-ui}.nearby-people-status button:first-child{flex:1}.nearby-people-status button svg{flex-shrink:0}.nearby-people-status .nearby-sharing-stop{background:#edf4e7}.nearby-people-status button:focus-visible{outline:2px solid #19744f;outline-offset:1px}
</style>
<style scoped>
.navigation-toolbar{gap:7px}.navigation-toolbar button{padding:11px 12px;font-size:12px}.navigation-toolbar .navigation-share{margin-left:auto}.navigation-share-panel{position:absolute;z-index:700;top:calc(max(14px,env(safe-area-inset-top)) + 58px);left:14px;right:14px;max-width:380px;max-height:calc(100dvh - 115px);overflow:auto;margin:auto;padding:18px;border:1px solid #c5d7b8;border-radius:16px;background:#fff;color:#24563b;box-shadow:0 10px 40px #153c2940;font-size:12px;line-height:1.6}.position-share-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.position-share-heading h2{display:flex;align-items:center;gap:8px;font-size:16px;margin:0}.position-share-heading>button{display:grid;place-items:center;width:40px;height:40px;border:0;border-radius:9px;background:#f0f5ea;color:#24563b;flex-shrink:0}.position-coordinates{font:600 18px/1.6 ui-monospace,monospace;user-select:all;overflow-wrap:anywhere;margin:14px 0 3px}.position-accuracy{color:#718369;font-size:11px;margin:0 0 14px}.position-share-links{display:flex;flex-wrap:wrap;gap:7px;margin:15px 0}.position-share-links>a,.position-share-links>button,.position-refresh{display:flex;align-items:center;justify-content:center;gap:7px;min-height:44px;border:1px solid #c9dabd;border-radius:9px;padding:10px 13px;background:#edf5e6;color:#19744f;font:600 12px/1.5 system-ui}.position-share-links>a{flex:1}.position-share-links .position-whatsapp{background:#19744f;color:#fff;border-color:#19744f}.position-google{display:block;color:#19744f;text-decoration:underline;margin:12px 0;overflow-wrap:anywhere}.navigation-share-panel small{display:block;color:#718369;font-size:11px;line-height:1.6}.position-refresh{margin-top:15px;width:100%;background:#fff}.navigation-share-panel button:focus-visible,.navigation-share-panel a:focus-visible{outline:3px solid #19744f;outline-offset:2px}.position-share-warning{color:#966529}.navigation-status{top:190px;max-width:calc(100% - 28px)}.navigation-offline-note{position:absolute;z-index:600;bottom:calc(max(28px,env(safe-area-inset-bottom)) + 150px);left:14px;right:14px;margin:auto;text-align:center;max-width:360px;background:#fffffff0;padding:5px 8px;border-radius:8px;font-size:10px;color:#526b45;pointer-events:none}
@media(max-width:360px){.navigation-toolbar button{padding:10px;font-size:11px;gap:5px}.navigation-toolbar .navigation-share span{max-width:65px;text-align:left;line-height:1.3}.position-coordinates{font-size:16px}}
</style>
<style scoped>
.navigation-map-tone{margin-top:12px;padding-top:12px;border-top:1px solid #e2e9dc}.navigation-map-tone>span{display:block;font-size:11px;margin-bottom:8px;color:#718369}.navigation-map-tone>div{display:flex;gap:5px}.navigation-map-tone button{padding:9px 12px;border:1px solid #d3dfc8;border-radius:8px;background:#fff;color:#24563b;font-size:12px}.navigation-map-tone button[aria-pressed=true]{background:#edf3e8;border-color:#9cb892}.navigation-map-tone button:focus-visible{outline:2px solid #19744f;outline-offset:2px}
</style>
<style scoped>
.navigation-metrics{position:absolute;z-index:600;bottom:calc(max(28px,env(safe-area-inset-bottom)) + 62px);left:14px;right:14px;max-width:360px;margin:auto;display:grid;grid-template-columns:1fr 1fr;gap:12px;background:#fffffff5;border:1px solid #d3dfc8;border-radius:14px;padding:14px 16px;box-shadow:0 3px 16px #153c2926;color:#24563b;pointer-events:none}.navigation-metrics>div{display:flex;align-items:center;gap:10px;min-width:0}.navigation-metrics svg{flex-shrink:0;color:#19744f}.navigation-metrics small{display:block;font-size:10px;line-height:1.5;color:#718369}.navigation-metrics strong{display:block;font-size:17px;line-height:1.5}.navigation-metrics>div+div{border-left:1px solid #dce5d4;padding-left:12px}
@media(max-width:360px){.navigation-metrics{gap:8px;padding:12px}.navigation-metrics>div{gap:7px}.navigation-metrics strong{font-size:15px}}
</style>
