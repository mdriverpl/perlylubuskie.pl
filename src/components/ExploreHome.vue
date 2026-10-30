<script setup>
function imageFallback(event){event.target.onerror=null;event.target.src="/images/heritage-placeholder.svg"}
import { computed, ref, watch, nextTick } from 'vue'
import Search from 'lucide-vue-next/dist/esm/icons/search.js'
import MapPin from 'lucide-vue-next/dist/esm/icons/map-pin.js'
import Map from 'lucide-vue-next/dist/esm/icons/map.js'
import Grid2X2 from 'lucide-vue-next/dist/esm/icons/grid-2x2.js'
import List from 'lucide-vue-next/dist/esm/icons/list.js'
import Castle from 'lucide-vue-next/dist/esm/icons/castle.js'
import Grape from 'lucide-vue-next/dist/esm/icons/grape.js'
import Sparkles from 'lucide-vue-next/dist/esm/icons/sparkles.js'
import Utensils from 'lucide-vue-next/dist/esm/icons/utensils.js'
import Waves from 'lucide-vue-next/dist/esm/icons/waves.js'
import Trees from 'lucide-vue-next/dist/esm/icons/trees.js'
import Landmark from 'lucide-vue-next/dist/esm/icons/landmark.js'
import Bed from 'lucide-vue-next/dist/esm/icons/bed.js'
import ThumbsUp from 'lucide-vue-next/dist/esm/icons/thumbs-up.js'
import MessageCircle from 'lucide-vue-next/dist/esm/icons/message-circle.js'
import Heart from 'lucide-vue-next/dist/esm/icons/heart.js'
import ArrowUpRight from 'lucide-vue-next/dist/esm/icons/arrow-up-right.js'
import ArrowRight from 'lucide-vue-next/dist/esm/icons/arrow-right.js'
import LocateFixed from 'lucide-vue-next/dist/esm/icons/locate-fixed.js'
import Plus from 'lucide-vue-next/dist/esm/icons/plus.js'
import ChevronUp from 'lucide-vue-next/dist/esm/icons/chevron-up.js'
import ChevronDown from 'lucide-vue-next/dist/esm/icons/chevron-down.js'
import Route from 'lucide-vue-next/dist/esm/icons/route.js'
import X from 'lucide-vue-next/dist/esm/icons/x.js'
import TravelMap from './TravelMap.vue'
import { placeFacets, defaultPlaceFacets, filterPlaces, sortNearby, distanceKm, normalizeRegion } from '../explore.js'
import { useGeolocation } from '../useGeolocation.js'
import { useLocationSearch } from '../useLocationSearch.js'
const props=defineProps({catalogOnly:Boolean,focusLocation:Object,places:{type:Array,required:true},routePoints:{type:Array,default:()=>[]},favorites:{type:Array,default:()=>[]},online:Boolean,liking:{type:Array,default:()=>[]},selected:{type:Array,default:()=>[]}})
const emit=defineEmits(['open','favorite','like','add','remove','move','clear','planner','create-point','create-place'])
const plannedPlaces=computed(()=>props.selected.map(id=>[...props.places,...props.routePoints].find(p=>p.id===id)).filter(Boolean))
const pointDraft=ref(null)
const pointDialog=ref(null)
watch(pointDraft,async draft=>{if(!draft)return;await nextTick();pointDialog.value?.showModal();const input=document.getElementById('custom-point-name');input?.focus();input?.select()})
const customPoints=computed(()=>props.routePoints.filter(p=>props.selected.includes(p.id)))
const catalogPlaces=computed(()=>props.places.filter(p=>p.details?.kind!=='custom'))
const mapPlaces=computed(()=>[...results.value,...customPoints.value])
function draftCustomPoint(point){pointDraft.value={...point,name:'Własny punkt '+(customPoints.value.length+1)}}
function saveCustomPoint(){if(!pointDraft.value?.name.trim())return;emit('create-point',{...pointDraft.value,name:pointDraft.value.name.trim()});pointDraft.value=null}
const region='Lubuskie'
const queryStorageKey=props.catalogOnly?'perly:places-query':'perly:planner-query'
function savedQuery(){try{return (localStorage.getItem(queryStorageKey)||'').slice(0,200)}catch{return ''}}
const query=ref(savedQuery()),chosen=ref([...defaultPlaceFacets]),displayMode=ref(props.catalogOnly?'grid':'map'),sort=ref(props.catalogOnly?'recommended':'nearby')
const radius=ref('')
const icons={castle:Castle,grape:Grape,sparkles:Sparkles,utensils:Utensils,waves:Waves,trees:Trees,landmark:Landmark,bed:Bed}
const {position:userLocation,loading:locating,error:locationError,locate}=useGeolocation()
const {items:locationMatches,selected:searchedLocation,loading:searchingLocation,error:searchError,search:searchLocation,clear:clearLocation}=useLocationSearch()
const mapFocus=ref(props.focusLocation)
watch(()=>props.focusLocation,value=>{mapFocus.value=value;if(value)displayMode.value='map'})
watch([query,chosen,userLocation,searchedLocation],()=>{mapFocus.value=null},{deep:true})
watch(query,clearLocation)
// GPS only draws the user's marker; it never limits the catalog.
const distanceOrigin=computed(()=>searchedLocation.value)
const townFocus=computed(()=>{
 const name=normalizeRegion(query.value)
 if(name.length<2||searchedLocation.value)return null
 const points=catalogPlaces.value.filter(p=>normalizeRegion(p.location||'')===name&&Number.isFinite(p.lat)&&Number.isFinite(p.lng))
 if(!points.length)return null
 return {lat:(Math.min(...points.map(p=>p.lat))+Math.max(...points.map(p=>p.lat)))/2,lng:(Math.min(...points.map(p=>p.lng))+Math.max(...points.map(p=>p.lng)))/2,zoom:13}
})
watch(query,value=>{
 try{if(value.trim())localStorage.setItem(queryStorageKey,value.slice(0,200));else localStorage.removeItem(queryStorageKey)}catch{}
 if(value.trim()){
  radius.value=''
  if(sort.value==='local'||sort.value==='distance')sort.value='recommended'
 }
})
watch(distanceOrigin,origin=>{if(!origin){radius.value='';if(sort.value==='distance')sort.value='nearby'}})
function withinRadius(places){return radius.value&&distanceOrigin.value?places.filter(p=>distanceKm(distanceOrigin.value,p)<=Number(radius.value)):places}
function distanceLabel(place){const km=distanceKm(distanceOrigin.value,place);return Number.isFinite(km)?`${km.toLocaleString('pl-PL',{maximumFractionDigits:1})} km w linii prostej`:''}
async function findLocation(){if(query.value.trim().length<2)return;displayMode.value='map';await searchLocation(query.value)}
const catalogQuery=computed(()=>searchedLocation.value&&(radius.value||sort.value==='distance')?'':query.value)
const base=computed(()=>withinRadius(filterPlaces(catalogPlaces.value,region,catalogQuery.value,[])))
const results=computed(()=>{const found=withinRadius(filterPlaces(catalogPlaces.value,region,catalogQuery.value,chosen.value));if(sort.value==='nearby')return sortNearby(found,distanceOrigin.value);if(sort.value==='local'&&distanceOrigin.value)return [...found].sort((a,b)=>(b.popularity??0)-(a.popularity??0)||distanceKm(distanceOrigin.value,a)-distanceKm(distanceOrigin.value,b));if(sort.value==='distance'&&distanceOrigin.value)return [...found].sort((a,b)=>distanceKm(distanceOrigin.value,a)-distanceKm(distanceOrigin.value,b)||a.name.localeCompare(b.name,'pl'));return [...found].sort((a,b)=>sort.value==='name'?a.name.localeCompare(b.name,'pl'):(sort.value==='likes'?(b.like_count??0)-(a.like_count??0):sort.value==='comments'?(b.comment_count??0)-(a.comment_count??0):(b.popularity??0)-(a.popularity??0)))})
const activeFacets=computed(()=>placeFacets.filter(f=>chosen.value.includes(f.id)))
const viewModes=[{id:'list',name:'Lista',label:'Widok listy',icon:List},{id:'grid',name:'Kafelki',label:'Widok kafelków',icon:Grid2X2},{id:'map',name:'Mapa',label:'Widok mapy',icon:Map}]
function reset(){query.value='';chosen.value=[];radius.value='';mapFocus.value=null;if(props.catalogOnly)sort.value='recommended'}
function removeFacet(id){chosen.value=chosen.value.filter(x=>x!==id)}
function openMarker(id){const place=[...props.places,...props.routePoints].find(p=>p.id===id);if(place)emit('open',place)}
</script>

<template>
 <main class="explore-home">
  <div class="explore-layout menu-horizontal">
   <section class="explore-results" aria-label="Wyniki wyszukiwania">
    <div class="explore-result-top"><div><h1>{{catalogOnly?'Miejsca':'Czego szukam?'}}</h1><p role="status">Znalezione miejsca: <strong>{{results.length}}</strong></p></div><button v-if="catalogOnly" class="button create-place-button" @click="emit('create-place')"><Plus :size="16"/>Dodaj miejsce</button><div class="explore-result-actions"><div class="explore-search-location"><div class="explore-search"><Search :size="17"/><input id="explore-query" aria-label="Nazwa lub miejscowość" v-model="query" placeholder="Nazwa lub miejscowość…" type="search" @keydown.enter.prevent="findLocation"></div></div><label class="explore-sort" title="Blisko siebie: sąsiednie miejsca według współrzędnych. Popularność: suma polubień i komentarzy.">Sortuj<select v-model="sort" aria-label="Sortuj miejsca"><option value="nearby">Blisko siebie</option><option value="distance" :disabled="!distanceOrigin">Odległość — najbliższe</option><option v-if="catalogOnly" value="local" :disabled="!distanceOrigin">Polecane w pobliżu</option><option value="recommended">Popularność</option><option value="likes">Najwięcej polubień</option><option value="comments">Najwięcej komentarzy</option><option value="name">Nazwa A–Z</option></select></label><label class="explore-sort distance-filter">Odległość<select v-model="radius" aria-label="Filtr odległości" :disabled="!distanceOrigin"><option value="">Bez limitu</option><option v-for="km in [5,10,25,50,100]" :key="km" :value="String(km)">Do {{km}} km</option></select></label><div class="explore-view-switch" role="group" aria-label="Rodzaj widoku"><button v-for="mode in viewModes" :key="mode.id" :aria-label="mode.label" :title="mode.name" :aria-pressed="displayMode===mode.id" :class="{active:displayMode===mode.id}" @click="displayMode=mode.id"><component :is="mode.icon" :size="18"/></button></div></div></div>
    <p v-if="locationError" class="location-error" role="alert">{{locationError}}</p>
    <p v-if="searchError" class="location-search-error" role="alert">{{searchError}}</p>
    <div v-if="locationMatches.length>1" class="location-matches" aria-label="Znalezione lokalizacje HERE"><button v-for="item in locationMatches" :key="item.id" :aria-pressed="searchedLocation?.id===item.id" @click="searchedLocation=item;displayMode='map'">{{item.name}}</button></div>
    <button v-if="query||chosen.length||radius" class="clear-explore-filters compact-clear-filters" @click="reset"><X :size="14"/>Wyczyść filtry</button>
    <fieldset class="facet-list"><legend class="facet-legend">Rodzaje miejsc</legend><label v-for="facet in placeFacets" :key="facet.id" :class="['facet-option',{checked:chosen.includes(facet.id)}]"><input type="checkbox" v-model="chosen" :value="facet.id"><component :is="icons[facet.icon]" :size="18"/><span>{{facet.name}}</span><small>{{base.filter(facet.match).length}}</small></label></fieldset>
    <div v-if="activeFacets.length" class="explore-chips" aria-label="Aktywne filtry"><button v-for="facet in activeFacets" :key="facet.id" @click="removeFacet(facet.id)" :aria-label="`Usuń filtr: ${facet.name}`">{{facet.name}}<X :size="12"/></button></div>
    <div :class="['explore-content-layout',{'catalog-content-layout':catalogOnly}]"><div class="explore-content-main">
    <section v-if="displayMode!=='map'" :aria-label="displayMode==='list'?'Lista miejsc':'Kafelki miejsc'">
     <div v-if="results.length" :class="['explore-grid',{'explore-list':displayMode==='list'}]"><article v-for="place in results" :key="place.id" class="place-card explore-place"><button class="place-image" @click="emit('open',place)"><img :src="place.image" @error="imageFallback" :alt="place.name" loading="lazy"><span class="place-tag">{{place.category==='leisure'?'Atrakcje rodzinne':place.category==='vineyard'?'Winnice':place.category==='stay'?'Noclegi':place.category==='food'?(place.details?.kind==='inspiration'?'Inspiracja kulinarna':'Gastronomia'):place.category==='nature'?'Przyroda':'Zabytki i historia'}}</span></button><button title="Twoje prywatne ulubione" :class="['heart-btn',{liked:favorites.includes(place.id)}]" :aria-label="`${favorites.includes(place.id)?'Usuń z ulubionych':'Dodaj do ulubionych'}: ${place.name}`" :aria-pressed="favorites.includes(place.id)" @click="emit('favorite',place.id)"><Heart :size="19" :fill="favorites.includes(place.id)?'currentColor':'none'"/></button><div class="place-info"><span class="place-location"><MapPin :size="12"/>{{place.location}}</span><button class="place-title" @click="emit('open',place)">{{place.name}}</button><p>{{place.subtitle}}</p><small v-if="place.details?.coordinate_accuracy==='street'" class="place-location-accuracy">Lokalizacja przybliżona</small><span v-if="distanceOrigin&&distanceLabel(place)" class="place-distance"><MapPin :size="12"/>{{distanceLabel(place)}}</span><button class="add-place-to-list" :disabled="selected.includes(place.id)" @click="emit('add',place)"><Plus :size="14"/>{{selected.includes(place.id)?'Na liście':catalogOnly?'Dodaj do planera':'Dodaj do listy'}}</button><div class="place-social"><button :class="{liked:place.liked}" :aria-label="`${place.liked?'Cofnij polubienie':'Polub'}: ${place.name}`" :aria-pressed="!!place.liked" :disabled="!online||liking.includes(place.id)" @click="emit('like',place.id)"><ThumbsUp :size="14"/><span>{{online?(place.like_count??0):'—'}}</span></button><button :aria-label="`Komentarze: ${place.name}`" @click="emit('open',place)"><MessageCircle :size="14"/><span>{{place.comment_count??0}}</span></button></div><button class="card-arrow" :aria-label="`Zobacz ${place.name}`" @click="emit('open',place)"><ArrowUpRight :size="20"/></button></div></article></div>
     <div v-else class="explore-empty"><Search :size="34"/><h3>Nie znaleźliśmy takich miejsc</h3><p>Zmień kategorie lub wyszukiwaną nazwę. Możesz też wyczyścić filtry i zobaczyć wszystkie miejsca.</p><button class="button outline" @click="reset">Pokaż miejsca w Lubuskiem<ArrowRight :size="16"/></button></div>
    </section>
    <section v-else aria-label="Mapa miejsc">

     <p v-if="searchedLocation" class="searched-location" role="status"><MapPin :size="15"/>Lokalizacja HERE: {{searchedLocation.name}}<button @click="clearLocation" aria-label="Usuń wyszukaną lokalizację"><X :size="15"/></button></p>
     <div class="explore-map"><TravelMap :focus-location="mapFocus||townFocus" :allow-custom-points="!catalogOnly" @create-point="draftCustomPoint" :places="mapPlaces" :selected="selected" :user-location="userLocation" :search-location="searchedLocation" fit-places @select="openMarker"/><button class="locate-button map-locate-button" :aria-label="locating?'Ustalam lokalizację…':userLocation?'Odśwież moją lokalizację':'Pokaż, gdzie jestem'" :title="locating?'Ustalam lokalizację…':userLocation?'Odśwież moją lokalizację':'Pokaż, gdzie jestem'" :disabled="locating" @click.stop="locate()" @dblclick.stop><LocateFixed :size="17"/><span>{{locating?'Ustalam lokalizację…':userLocation?'Odśwież moją lokalizację':'Pokaż, gdzie jestem'}}</span></button><div class="explore-map-caption"><MapPin :size="14"/>Miejsca z katalogu: {{results.length}}</div><div v-if="!results.length&&!searchedLocation" class="map-no-results">Brak miejsc dla tych filtrów. Zmień wybór po lewej lub wyszukaj miejscowość przyciskiem „Znajdź na mapie”.</div></div>
     <p v-if="!catalogOnly" class="custom-point-hint">Dwukrotnie kliknij mapę, aby dodać własny punkt trasy.</p><div class="explore-map-legend"><span v-if="customPoints.length"><i class="custom-point-dot"></i>Punkty trasy: {{customPoints.length}}</span><span><i class="place-dot"></i>Miejsca z Twoich filtrów</span><span v-if="userLocation"><i class="user-dot"></i>Tu jesteś <small v-if="userLocation.accuracy!==null">(dokładność ok. {{Math.round(userLocation.accuracy)}} m)</small></span><span v-else>Użyj „Pokaż, gdzie jestem”, aby zaznaczyć swoją pozycję.</span></div>
    </section>
    </div>
    <aside v-if="!catalogOnly" class="planned-places-panel" aria-label="Zaplanowane miejsca">
     <div class="planned-heading"><h2>Zaplanowane miejsca <span>{{plannedPlaces.length}}</span></h2><button :disabled="!plannedPlaces.length" @click="emit('clear')">Wyczyść listę</button></div>
     <div v-if="plannedPlaces.length" class="planned-places-list"><article v-for="(place,index) in plannedPlaces" :key="place.id" class="planned-stop">
      <span class="planned-number">{{index+1}}</span><button class="planned-open" @click="emit('open',place)" :aria-label="`Podgląd: ${place.name}`"><img :src="place.image" :alt="place.name" loading="lazy" @error="imageFallback"><span><strong>{{place.name}}</strong><small>{{place.location}}</small></span></button>
      <div class="planned-actions"><button :disabled="index===0" @click="emit('move',index,-1)" :aria-label="`Przesuń ${place.name} wyżej`"><ChevronUp :size="15"/></button><button :disabled="index===plannedPlaces.length-1" @click="emit('move',index,1)" :aria-label="`Przesuń ${place.name} niżej`"><ChevronDown :size="15"/></button><button @click="emit('remove',place.id)" :aria-label="`Usuń ${place.name} z listy`"><X :size="15"/></button></div>
     </article></div>
     <div v-else class="planned-empty"><List :size="28"/><p>Wybierz miejsce na mapie lub w katalogu i kliknij „Dodaj do listy”.</p></div>
     <p class="planned-note">Kolejność miejsc jest wspólna z planerem tras. Lista zapisuje się na tym urządzeniu.</p>
     <button class="button full-width" :disabled="!plannedPlaces.length" @click="emit('planner')"><Route :size="17"/>Dodaj trasę<ArrowRight :size="16"/></button>
    </aside>
    </div>
   </section>
  </div>
 </main>

  <Teleport to="body"><dialog v-if="pointDraft" ref="pointDialog" class="custom-point-dialog" aria-labelledby="custom-point-title" aria-describedby="custom-point-description" @cancel.prevent="pointDraft=null" @click.self="pointDraft=null"><form class="custom-point-form" @submit.prevent="saveCustomPoint"><h2 id="custom-point-title">Dodaj własny punkt</h2><p id="custom-point-description">Nazwij punkt pomocniczy tej trasy. Nie zostanie dodany do katalogu miejsc.</p><div><label for="custom-point-name">Nazwa własnego punktu</label><input autofocus id="custom-point-name" v-model="pointDraft.name" required maxlength="80" autocomplete="off"><p>{{pointDraft.lat.toFixed(6)}}, {{pointDraft.lng.toFixed(6)}} · tylko na tym urządzeniu</p></div><div class="custom-point-dialog-actions"><button class="button" type="submit"><Plus :size="16"/>Dodaj punkt</button><button class="custom-point-cancel" type="button" @click="pointDraft=null">Anuluj</button></div></form></dialog></Teleport>
</template>

<style scoped>
.explore-home{background:#f4f6f0;padding:34px max(28px,calc((100vw - 1456px)/2)) 54px;min-height:calc(100vh - 180px)}.explore-top{display:flex;align-items:center;justify-content:space-between;gap:24px;margin-bottom:28px}.explore-top h1{font-size:34px;letter-spacing:-1.3px;line-height:1.3;font-weight:800}.explore-top h1 span{color:#19744f}.explore-top p{font-size:13px;color:#7e8a78;margin-top:9px;line-height:1.7}.explore-top .section-kicker{font-size:8px;letter-spacing:2px;color:#8b977f}.explore-planner{font-size:12px;padding:13px 19px}.explore-layout{display:grid;grid-template-columns:280px minmax(0,1fr);gap:30px;align-items:start}.explore-sidebar{background:#fff;border:1px solid #e3e8dc;border-radius:13px;padding:24px 20px;position:sticky;top:20px;box-shadow:0 4px 20px #203d2510}.sidebar-heading{display:flex;align-items:center;justify-content:space-between;margin-bottom:27px;color:#839178}.sidebar-heading h2{font-size:15px;letter-spacing:-.4px;color:#243a2b}.filter-label{display:block;font-size:12px;font-weight:600;margin-bottom:9px}.region-input,.explore-search{display:flex;align-items:center;gap:9px;border:1px solid #dce4d3;background:#fcfdf9;border-radius:7px;padding:12px 11px;color:#749065}.region-input:focus-within,.explore-search:focus-within{outline:2px solid #81ac8a;outline-offset:1px}.region-input input,.explore-search input{background:none;border:0;outline:none;min-width:0;width:100%;font-size:12px;color:#263e2c}.region-input input{font-weight:600}.region-input input:focus,.explore-search input:focus{outline:none}.region-note{display:flex;align-items:center;gap:5px;font-size:8px;color:#8b987f;margin-top:9px}.region-note span{width:4px;height:4px;background:#7b9b67;border-radius:50%}.query-label{margin-top:24px;font-size:11px}.explore-search input{font-size:11px}.facet-list{border:0;padding:0;margin:27px 0 12px}.facet-list legend{font-size:12px;font-weight:700;margin-bottom:6px;padding:0}.facet-list>p{font-size:9px;color:#94a08b;margin-bottom:13px}.facet-option{display:flex;align-items:center;gap:10px;min-height:45px;padding:10px 8px;border-radius:7px;margin:3px -6px;cursor:pointer;color:#74836b;border:1px solid transparent;transition:background .15s}.facet-option:hover{background:#f5f8f0}.facet-option.checked{background:#edf4e6;border-color:#e2ecd9;color:#19744f}.facet-option input{width:16px;height:16px;accent-color:#19744f;margin:0;flex-shrink:0}.facet-option span{font-size:11px;color:#40533c}.facet-option.checked span{font-weight:600;color:#19744f}.facet-option small{margin-left:auto;font-size:9px;background:#f0f4e9;padding:3px 6px;border-radius:4px;color:#8b9c7d}.facet-option.checked small{background:#dfead4;color:#4a773b}.clear-explore-filters{display:flex;align-items:center;justify-content:center;gap:6px;font-size:10px;color:#8b987f;padding:12px;width:100%;border-top:1px solid #edf0e7;margin-top:12px}.clear-explore-filters:hover{color:#19744f}.sidebar-region-image{height:110px;border-radius:9px;overflow:hidden;position:relative;margin-top:15px}.sidebar-region-image:after{content:'';position:absolute;inset:0;background:linear-gradient(90deg,#153e2eab,transparent)}.sidebar-region-image span{position:absolute;left:14px;top:24px;color:#fff;font-family:Manrope,sans-serif;font-size:16px;font-weight:700;line-height:1.5;z-index:1;letter-spacing:-.4px}.explore-results{min-width:0}.explore-result-top{display:flex;align-items:center;justify-content:space-between;margin:2px 0 22px;gap:14px}.explore-result-top h1{font-size:21px;letter-spacing:-.65px;font-weight:800}.explore-result-top p{font-size:11px;color:#8d9983;margin-top:7px}.explore-result-top strong{color:#536d46;font-weight:600}.explore-sort{display:flex;align-items:center;gap:8px;font-size:9px;color:#8b977f}.explore-sort select{font:inherit;font-size:10px;color:#4c6242;padding:9px 10px;border:1px solid #e1e7d9;border-radius:7px;background:#fff;cursor:pointer}.locate-button{display:flex;align-items:center;gap:7px;font-size:10px;color:#19744f;border:1px solid #d5e2cb;background:#fbfdf8;padding:9px 12px;border-radius:7px;margin-bottom:6px}.explore-chips{display:flex;gap:7px;flex-wrap:wrap;margin:-8px 0 18px}.explore-chips button{display:flex;align-items:center;gap:7px;padding:6px 9px;border:1px solid #d7e3cd;color:#4c7540;background:#eef4e6;border-radius:20px;font-size:9px}.explore-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:27px 21px}.explore-place{background:#fff;border:1px solid #e3e9db;border-radius:11px;padding-bottom:17px;overflow:hidden;box-shadow:0 3px 13px #1c402406}.explore-place .place-image{height:190px;border-radius:10px 10px 0 0}.explore-place .place-info{padding:14px 35px 0 16px}.explore-place .card-arrow{right:13px;top:37px}.explore-place .place-title{font-size:14px;line-height:1.5;letter-spacing:-.3px}.explore-place .place-info p{font-size:10px;line-height:1.6}.explore-place .place-location{font-size:9px}.explore-place .place-tag{font-size:8px}.explore-empty{display:flex;flex-direction:column;align-items:center;text-align:center;gap:18px;min-height:410px;justify-content:center;border:1px dashed #d5dfc9;border-radius:13px;padding:40px;color:#19744f;background:#f9fbf5}.explore-empty h3{font-size:22px;letter-spacing:-.6px}.explore-empty p{font-size:12px;line-height:1.9;color:#819174;max-width:420px}.explore-empty .button{font-size:11px}.explore-map{height:610px;min-height:450px;position:relative;border-radius:12px;overflow:hidden;border:1px solid #d6e1ca;background:#e1ead9}.explore-map-caption{position:absolute;z-index:1;top:14px;left:55px;display:flex;align-items:center;gap:6px;background:#fffef5f2;color:#42633a;padding:10px 12px;border-radius:6px;box-shadow:0 2px 6px #2e512a14;font-size:10px}.map-no-results{position:absolute;bottom:20px;left:50%;transform:translateX(-50%);z-index:1;background:#fffef4ed;border-radius:9px;padding:14px 19px;text-align:center;font-size:11px;color:#6d815e;width:max-content;max-width:85%}.explore-map-legend{display:flex;flex-wrap:wrap;gap:15px;align-items:center;font-size:9px;color:#87967b;line-height:1.7;margin-top:13px}.explore-map-legend>span{display:flex;align-items:center;gap:6px}.explore-map-legend small{font-size:9px}.place-dot,.user-dot{width:7px;height:7px;border-radius:50%;background:#34764f;display:inline-block;flex-shrink:0}.user-dot{background:#1876d2}.location-error{font-size:11px;line-height:1.8;color:#a05c3e;background:#fcf0e5;border:1px solid #f1e2cc;padding:12px 15px;border-radius:8px;margin:-5px 0 15px}.mobile-filter-toggle{display:none}
@media(min-width:1700px){.explore-map{height:690px}.explore-place .place-image{height:220px}}
@media(max-width:1150px){.explore-layout{grid-template-columns:245px minmax(0,1fr);gap:22px}.explore-sidebar{padding:21px 16px}.explore-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.explore-place .place-image{height:205px}.explore-result-top h1{font-size:18px}.explore-home{padding:28px 28px 45px}}
@media(max-width:800px){.explore-home{padding:25px 18px 36px}.explore-layout{grid-template-columns:minmax(0,1fr);gap:22px}.explore-top{align-items:flex-start;margin-bottom:23px}.explore-top h1{font-size:28px;letter-spacing:-1px}.explore-top p{font-size:11px;max-width:270px}.explore-planner{font-size:10px;padding:11px 12px;gap:7px}.explore-planner>svg:last-child{display:none}.mobile-filter-toggle{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #d9e3ce;border-radius:8px;padding:12px 16px;font-size:12px;color:#19744f;margin-bottom:20px}.mobile-filter-toggle span{background:#edf3e6;padding:2px 6px;border-radius:4px;font-size:10px}.explore-sidebar{display:none;position:static}.explore-sidebar.expanded{display:block}.sidebar-region-image{display:none}.facet-list{display:grid;grid-template-columns:1fr 1fr;column-gap:20px}.facet-list legend{grid-column:1/-1}.facet-list>p{grid-column:1/-1}.explore-result-top{margin-top:0;margin-bottom:14px}.explore-result-top h1{font-size:20px}.explore-place .place-image{height:210px}.explore-map{height:480px}.locate-button{font-size:9px;padding:8px}.explore-map-legend{gap:8px}}
@media(max-width:480px){.explore-top{display:block}.explore-top h1{font-size:29px}.explore-top p{max-width:none}.explore-planner{margin-top:17px}.explore-grid{gap:15px 11px}.explore-place .place-image{height:145px}.explore-place .place-info{padding:11px 23px 0 11px}.explore-place .place-title{font-size:12px}.explore-place .place-info p{font-size:9px}.explore-place .place-location{font-size:8px}.explore-place .card-arrow{right:7px;top:32px;width:14px}.explore-place .place-tag{font-size:7px;left:8px;bottom:9px;padding:4px 6px}.explore-result-top h1{font-size:17px}.explore-sort{display:block;font-size:8px;text-align:right}.explore-sort select{display:block;margin-top:4px;padding:7px;font-size:9px;max-width:110px}.locate-button{max-width:175px;font-size:9px;line-height:1.5;gap:5px}.explore-map{height:440px;min-height:400px}.explore-empty{padding:35px 20px;min-height:350px}.explore-empty h3{font-size:20px}}

.explore-result-top{flex-wrap:wrap}
.explore-result-actions{display:flex;align-items:center;gap:12px;flex-shrink:0;margin-left:auto}
.explore-view-switch{display:flex;align-items:center;gap:3px;padding:3px;background:#fff;border:1px solid #dce5d3;border-radius:9px}
.explore-view-switch button{display:grid;place-items:center;width:36px;height:36px;padding:0;border-radius:6px;color:#809473;transition:background .15s,color .15s}
.explore-view-switch button.active{background:#19744f;color:#fff}
.explore-view-switch button:not(.active):hover{background:#edf4e6;color:#19744f}
.explore-map-tools{display:flex;justify-content:flex-end;margin:-4px 0 12px}
.explore-map-tools .locate-button{margin-bottom:0}
.explore-list{grid-template-columns:minmax(0,1fr);gap:14px}
.explore-list .explore-place{display:grid;grid-template-columns:180px minmax(0,1fr);align-items:center;gap:20px;padding:14px}
.explore-list .place-image{height:132px;border-radius:8px}
.explore-list .place-info{padding:4px 48px 4px 0}
.explore-list .place-title{font-size:16px}
.explore-list .place-info p{font-size:12px;margin-top:9px}
.explore-list .place-location{font-size:10px;margin-bottom:8px}
.explore-list .card-arrow{right:0;top:auto;bottom:2px}
.explore-list .heart-btn{right:15px;top:15px;background:#f1f6eb;border-color:#dce7d2;color:#7e956e}
.explore-list .heart-btn.liked{color:#19744f;background:#e5efda}
@media(max-width:600px){
 .explore-result-actions{gap:10px}
 .explore-list .explore-place{grid-template-columns:122px minmax(0,1fr);gap:14px;padding:12px}
 .explore-list .place-image{height:112px}
 .explore-list .place-title{font-size:14px}
 .explore-list .place-info p{font-size:11px}
}
@media(max-width:480px){
 .explore-result-actions{width:100%;justify-content:flex-end}
 .explore-result-actions .explore-sort{display:flex;align-items:center;gap:8px;text-align:left;font-size:9px}
 .explore-result-actions .explore-sort select{margin-top:0}
 .explore-list .explore-place{grid-template-columns:102px minmax(0,1fr);gap:12px}
 .explore-list .place-image{height:104px}
 .explore-list .place-info{padding-right:30px}
 .explore-list .place-title{font-size:12px}
 .explore-list .place-info p{font-size:10px}
 .explore-list .place-location{font-size:8px}
 .explore-list .heart-btn{right:10px;top:10px;width:26px;height:26px}
 .explore-list .heart-btn svg{width:15px;height:15px}
}
</style>

<style scoped>
.location-search-actions{margin-top:10px}.find-map-location{display:flex;align-items:center;gap:6px;background:#edf4e6;color:#19744f;border:1px solid #d7e3cd;padding:9px 11px;border-radius:7px;font-size:11px;width:100%;justify-content:center}.location-search-actions p{font-size:9px;color:#7c8973;line-height:1.6;margin-top:7px}.location-search-error{font-size:11px;color:#a05c3e;line-height:1.7;margin-top:10px}.location-matches{display:grid;gap:5px;margin-top:10px}.location-matches button{font-size:11px;text-align:left;padding:9px;border:1px solid #d7e3cd;border-radius:6px;line-height:1.6}.location-matches button[aria-pressed=true]{background:#edf4e6}.searched-location{display:flex;align-items:center;gap:7px;font-size:12px;color:#8c571e;padding:10px 12px;background:#fff4de;border-radius:7px;margin:10px 0}.searched-location button{margin-left:auto}
</style>

<style scoped>
.explore-top-actions{display:flex;gap:16px;align-items:center;flex-wrap:wrap}.explore-results>.facet-list{display:flex;flex-wrap:wrap;gap:6px 12px;margin:0 0 20px;padding:12px 0;border-top:1px solid #dce4d3;border-bottom:1px solid #dce4d3}.facet-legend{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}.explore-results .facet-option{margin:0;padding:7px 9px;min-height:36px;gap:7px}.explore-results .facet-option span{font-size:11px}.explore-result-top{margin-bottom:14px}.explore-sidebar .query-label{margin-top:0}.menu-horizontal{grid-template-columns:minmax(0,1fr);gap:24px}.menu-horizontal .explore-sidebar{position:static;display:grid;grid-template-columns:220px minmax(200px,1fr) auto;align-items:center;gap:12px 20px;padding:18px 22px}.menu-horizontal .sidebar-heading{grid-column:1;margin:0;grid-row:1/3}.menu-horizontal .query-label{grid-column:2;grid-row:1;margin:0}.menu-horizontal .explore-search{grid-column:2;grid-row:2}.menu-horizontal .location-search-actions{grid-column:3;grid-row:1/3;margin:0}.menu-horizontal .location-search-actions p{max-width:180px}.menu-horizontal .clear-explore-filters{grid-column:3;grid-row:3;margin:0;border:0;width:auto}.menu-horizontal .sidebar-region-image{display:none}.menu-horizontal .location-search-error,.menu-horizontal .location-matches{grid-column:2/-1}.menu-horizontal .location-matches{display:flex;flex-wrap:wrap}
@media(max-width:800px){.explore-sidebar{display:block;position:static}.menu-horizontal .explore-sidebar{grid-template-columns:minmax(0,1fr) auto;gap:10px 15px}.menu-horizontal .sidebar-heading{grid-column:1/-1;grid-row:1}.menu-horizontal .query-label{grid-column:1;grid-row:2}.menu-horizontal .explore-search{grid-column:1;grid-row:3}.menu-horizontal .location-search-actions{grid-column:2;grid-row:2/4}.menu-horizontal .clear-explore-filters{grid-column:1/-1;grid-row:4}.explore-top-actions{gap:12px}.explore-results>.facet-list{display:flex;gap:4px}.explore-results .facet-option{padding:6px;gap:5px}.explore-top{flex-wrap:wrap}}
@media(max-width:480px){.explore-top-actions{margin-top:16px;justify-content:space-between}.explore-top-actions .explore-planner{margin-top:0}.menu-horizontal .explore-sidebar{display:block}.menu-horizontal .sidebar-heading{margin-bottom:16px}.menu-horizontal .query-label{margin-bottom:8px}.menu-horizontal .location-search-actions{margin-top:10px}.menu-horizontal .clear-explore-filters{margin-top:10px}.menu-horizontal .location-search-actions p{max-width:none}}
</style>

<style scoped>
.explore-result-actions{flex:1;min-width:0}.explore-result-actions>.explore-search{flex:1;min-width:140px;max-width:620px;margin-left:auto;padding:12px 14px}.explore-result-top{gap:22px}.explore-result-top>div:first-child{flex-shrink:0}.menu-horizontal .explore-sidebar{grid-template-columns:minmax(0,1fr) auto;gap:10px 20px;padding:15px 22px}.menu-horizontal .sidebar-heading{grid-column:1;grid-row:1}.menu-horizontal .clear-explore-filters{grid-column:2;grid-row:1}.menu-horizontal .location-search-actions{grid-column:1/-1;grid-row:2;display:flex;gap:12px;align-items:center}.menu-horizontal .find-map-location{width:auto}.menu-horizontal .location-search-actions p{margin:0;max-width:none}.menu-horizontal .location-search-error,.menu-horizontal .location-matches{grid-column:1/-1}
@media(max-width:800px){.explore-result-top{flex-wrap:wrap;gap:14px}.explore-result-actions{flex-basis:100%;width:100%;flex-wrap:wrap}.explore-result-actions>.explore-search{margin-left:0;min-width:170px;max-width:none}.menu-horizontal .explore-sidebar{display:grid}.menu-horizontal .sidebar-heading{margin:0}}
@media(max-width:480px){.explore-result-actions>.explore-search{flex-basis:100%;width:100%;order:0}.explore-result-actions .explore-sort{order:1}.explore-result-actions .explore-view-switch{order:2;margin-left:auto}.menu-horizontal .location-search-actions{flex-wrap:wrap}.menu-horizontal .sidebar-heading h2{font-size:13px}.menu-horizontal .explore-sidebar{padding:15px}}
</style>

<style scoped>
.explore-results>.location-search-actions{display:flex;align-items:center;gap:12px;margin:0 0 14px}.explore-results .find-map-location{width:auto}.explore-results>.location-search-actions p{margin:0;max-width:none}.explore-results>.location-search-error,.explore-results>.location-matches{margin:0 0 14px}.explore-results>.compact-clear-filters{width:auto;display:flex;padding:6px 0 10px;margin:0 0 6px;border:0}.menu-vertical .explore-sidebar>.clear-explore-filters{margin-top:0;border:0}
@media(max-width:480px){.explore-results>.location-search-actions{flex-wrap:wrap;gap:7px}}
</style>

<style scoped>
.explore-search-location{display:flex;align-items:center;gap:9px;flex:1;min-width:180px;margin-left:auto;max-width:760px}.explore-search-location>.explore-search{flex:1;min-width:0;padding:12px 14px}.explore-search-location>.locate-button{margin:0;white-space:nowrap;flex-shrink:0;min-height:42px}.explore-search-location input{min-width:0;text-overflow:ellipsis}
@media(max-width:1100px){.explore-result-top{flex-wrap:wrap}.explore-result-actions{width:100%;flex-basis:100%}.explore-search-location{margin-left:0;max-width:none}}
@media(max-width:480px){.explore-search-location{flex-basis:100%;order:0;width:100%}.explore-search-location>.locate-button{padding:11px;min-width:42px;justify-content:center}.explore-search-location>.locate-button span{display:none}}
</style>

<style scoped>
.explore-content-layout{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:22px;align-items:start}.explore-content-main{min-width:0}.planned-places-panel{position:sticky;top:18px;background:#fff;border:1px solid #e0e7d9;border-radius:12px;padding:20px 16px;box-shadow:0 3px 15px #1c402408}.planned-heading{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:16px}.planned-heading h2{font-size:15px;letter-spacing:-.35px;line-height:1.5}.planned-heading h2 span{font-size:11px;background:#edf4e6;color:#19744f;border-radius:20px;padding:3px 7px;margin-left:4px}.planned-heading>button{font-size:10px;color:#7c8c72;white-space:nowrap}.planned-places-list{max-height:490px;overflow-y:auto}.planned-stop{display:flex;align-items:center;gap:8px;padding:13px 0;border-bottom:1px solid #edf1e7}.planned-number{width:20px;height:20px;display:grid;place-items:center;border-radius:50%;background:#19744f;color:#fff;font-size:10px;flex-shrink:0}.planned-open{display:flex;align-items:center;gap:9px;flex:1;min-width:0;text-align:left;padding:0}.planned-open>img{width:52px;height:52px;object-fit:cover;border-radius:7px;flex-shrink:0}.planned-open>span{min-width:0}.planned-open strong{display:block;font-size:11px;line-height:1.5;overflow-wrap:anywhere}.planned-open small{display:block;font-size:9px;color:#88967e;line-height:1.5;margin-top:3px}.planned-actions{display:flex;flex-direction:column;gap:1px}.planned-actions button{display:grid;place-items:center;color:#66845a;width:22px;height:22px;padding:0}.planned-actions button:last-child{color:#ab6f53}.planned-empty{display:flex;flex-direction:column;align-items:center;text-align:center;gap:12px;color:#789269;padding:32px 10px}.planned-empty p{font-size:11px;line-height:1.9}.planned-note{font-size:9px;line-height:1.8;color:#8b987f;margin:16px 0}.planned-places-panel>.button{font-size:11px;padding:12px 10px;gap:7px}.add-place-to-list{display:flex;align-items:center;gap:6px;padding:7px 9px;margin-top:10px;background:#edf4e6;color:#19744f;border:1px solid #dbe6d2;border-radius:6px;font-size:10px}.explore-content-main .explore-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.explore-content-main .explore-list{grid-template-columns:minmax(0,1fr)}
@media(min-width:1700px){.explore-content-main .explore-grid:not(.explore-list){grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:1100px){.explore-content-layout{grid-template-columns:minmax(0,1fr) 290px;gap:16px}.planned-places-panel{padding:16px 12px}.planned-heading{flex-wrap:wrap}.planned-open>img{width:44px;height:44px}}
@media(max-width:850px){.explore-content-layout{grid-template-columns:minmax(0,1fr)}.planned-places-panel{position:static}.planned-places-list{max-height:340px}.planned-heading{flex-wrap:nowrap}.planned-open>img{width:52px;height:52px}.planned-open strong{font-size:12px}}
</style>

<style scoped>
.custom-point-form{display:flex;align-items:center;gap:12px;padding:15px;background:#fff8e8;border:1px solid #e8d8b5;border-radius:9px;margin-bottom:14px}.custom-point-form>div{flex:1;min-width:0}.custom-point-form label{font-size:12px;font-weight:600;display:block;margin:0 0 7px}.custom-point-form input{display:block;width:100%;padding:10px;border:1px solid #d8c9a7;border-radius:6px;font-size:12px;background:#fff}.custom-point-form p{font-size:10px;color:#8e7e5d;margin-top:6px}.custom-point-form .button{font-size:11px;white-space:nowrap;padding:11px}.custom-point-cancel{font-size:11px;color:#88724a}.custom-point-hint{font-size:10px;color:#8c7a58;line-height:1.8;margin:12px 0 0}.custom-point-dot{width:7px;height:7px;background:#b17b3c;border-radius:50%;display:inline-block}
@media(max-width:600px){.custom-point-form{flex-wrap:wrap}.custom-point-form>div{flex-basis:100%}}
</style>
<style>.map-pin.custom-point{background:#b17b3c}</style>

<style scoped>
.distance-origin-note{font-size:10px;color:#7b8d71;line-height:1.7;margin:0 0 14px;overflow-wrap:anywhere}.place-distance{display:flex;align-items:center;gap:5px;font-size:10px;color:#19744f;margin-top:8px}.explore-sort select:disabled{opacity:.6;cursor:not-allowed}.explore-result-actions{flex-wrap:wrap}.distance-filter{white-space:nowrap}
</style>

<style scoped>
.custom-point-dialog{position:fixed;inset:0;margin:auto;border:1px solid #dce5d3;border-radius:16px;padding:0;width:min(460px,calc(100% - 32px));max-height:calc(100dvh - 40px);overflow:auto;color:#173c2b;box-shadow:0 20px 70px #122e3433;background:#fff}.custom-point-dialog::backdrop{background:#142c2a80;backdrop-filter:blur(3px)}.custom-point-dialog .custom-point-form{display:block;background:#fff;border:0;border-radius:0;margin:0;padding:30px}.custom-point-dialog h2{font-size:23px;letter-spacing:-.5px;margin:0 0 10px}.custom-point-dialog #custom-point-description{font-size:12px;line-height:1.8;margin-bottom:22px;color:#74836b}.custom-point-dialog input{border-color:#d5e2cb;padding:12px}.custom-point-dialog input:focus{outline:2px solid #19744f;outline-offset:2px}.custom-point-dialog-actions{display:flex;align-items:center;gap:18px;margin-top:24px}.custom-point-dialog .custom-point-form>div{min-width:0}
</style>

<style scoped>
.explore-map>.map-locate-button{position:absolute;right:12px;bottom:30px;z-index:2;margin:0;max-width:calc(100% - 24px);min-height:40px;padding:10px 13px;background:#fff;color:#19744f;border:1px solid #d5e2cb;box-shadow:0 2px 10px #173c2b26;font-size:11px;line-height:1.5}.map-locate-button:disabled{opacity:.7;cursor:wait}.map-locate-button:hover{background:#f1f6eb}
</style>

<style scoped>
.explore-content-layout.catalog-content-layout{grid-template-columns:minmax(0,1fr)}.create-place-button{font-size:12px;padding:11px 14px}
.explore-content-main .explore-grid:not(.explore-list){grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.catalog-content-layout .explore-grid:not(.explore-list){grid-template-columns:repeat(4,minmax(0,1fr))}
.explore-grid:not(.explore-list) .explore-place{padding-bottom:12px}
.explore-grid:not(.explore-list) .place-image{height:140px}
.explore-grid:not(.explore-list) .place-info{padding:11px 28px 0 12px}
.explore-grid:not(.explore-list) .place-title{font-size:13px;line-height:1.5}
.explore-grid:not(.explore-list) .add-place-to-list{margin-top:8px;padding:6px 8px}
@media(min-width:1700px){.catalog-content-layout .explore-grid:not(.explore-list){grid-template-columns:repeat(5,minmax(0,1fr))}}
@media(max-width:1200px){.explore-content-main .explore-grid:not(.explore-list){grid-template-columns:repeat(2,minmax(0,1fr))}.catalog-content-layout .explore-grid:not(.explore-list){grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:800px){.catalog-content-layout .explore-grid:not(.explore-list){grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:480px){.explore-content-main .explore-grid:not(.explore-list){gap:12px 10px}.explore-grid:not(.explore-list) .place-image{height:110px}.explore-grid:not(.explore-list) .place-info{padding:9px 22px 0 10px}.explore-grid:not(.explore-list) .place-title{font-size:12px}}
</style>

<style scoped>
.nearby-gps-toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:11px 13px;margin:0 0 12px;border:1px solid #dce6d3;background:#edf4e6;border-radius:8px}.nearby-gps-toolbar>p{font-size:11px;color:#466d3e;line-height:1.7}.nearby-gps-toolbar>div{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.nearby-gps-toolbar button{display:flex;gap:5px;align-items:center;font-size:10px;color:#19744f;border:1px solid #cddfc3;background:#fff;border-radius:6px;padding:7px 9px}.nearby-gps-toolbar button:disabled{opacity:.6}
</style>
