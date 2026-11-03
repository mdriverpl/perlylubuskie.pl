<script setup>
import {computed} from 'vue'
import MapPin from 'lucide-vue-next/dist/esm/icons/map-pin.js'
import Footprints from 'lucide-vue-next/dist/esm/icons/footprints.js'
import Bike from 'lucide-vue-next/dist/esm/icons/bike.js'
import ArrowUpRight from 'lucide-vue-next/dist/esm/icons/arrow-up-right.js'
import {regionOverview} from '../regionOverview.js'
const props=defineProps({listOnly:Boolean,regions:{type:Array,default:()=>[]},places:{type:Array,default:()=>[]},routes:{type:Array,default:()=>[]}})
const emit=defineEmits(['select'])
const overview=computed(()=>regionOverview(props.regions,props.places,props.routes))
const totals=computed(()=>({places:overview.value.reduce((sum,r)=>sum+r.places,0),regions:overview.value.filter(r=>r.active&&r.places).length}))
const compact=n=>new Intl.NumberFormat('pl',{notation:'compact',maximumFractionDigits:1}).format(n)
const pluralRules=new Intl.PluralRules('pl')
const words=(n,one,few,many)=>({one,few,many,other:few})[pluralRules.select(n)]
const label=r=>`${r.name}: ${r.places} ${words(r.places,'miejsce','miejsca','miejsc')}, ${r.walking} ${words(r.walking,'trasa piesza','trasy piesze','tras pieszych')}, ${r.cycling} ${words(r.cycling,'trasa rowerowa','trasy rowerowe','tras rowerowych')}${r.active?'':'. Katalog w przygotowaniu'}`
function select(region){if(region.active)emit('select',region.slug)}
</script>

<template>
 <section v-if="listOnly" id="hero-province-list" class="province-summary" aria-labelledby="province-summary-heading"><h2 id="province-summary-heading">Województwa</h2><div class="province-summary-header" aria-hidden="true"><span>Województwo</span><span><MapPin :size="13"/>Miejsca</span><span><Footprints :size="13"/>Piesze</span><span><Bike :size="13"/>Rowerowe</span></div><div class="province-summary-rows"><button v-for="region in overview" :key="region.slug" class="province-summary-row" :data-region="region.slug" :disabled="!region.active" :aria-label="label(region)" @click="select(region)"><strong>{{region.name}}</strong><span>{{region.places}}</span><span>{{region.walking}}</span><span>{{region.cycling}}</span></button></div><p class="province-summary-note">Opublikowane miejsca i publiczne trasy. Pozostałe województwa są w przygotowaniu.</p></section>
 <section v-else id="poland-regions"  class="poland-regions" aria-labelledby="poland-regions-heading">
  <div class="poland-intro">
   <div class="section-kicker">WYBIERZ SWÓJ KIERUNEK</div>
   <h2 id="poland-regions-heading">Odkrywaj Polskę<span>.</span></h2>
   <p>Miejsca i trasy w Twoim województwie. Wybierz region na mapie i zajrzyj do katalogu.</p>
   <div class="poland-total"><strong>{{totals.places.toLocaleString('pl')}}</strong><span>miejsc w {{totals.regions}} {{totals.regions===1?'województwie':'województwach'}}</span></div>
   <div class="poland-legend"><span><MapPin :size="17"/>Miejsca</span><span><Footprints :size="17"/>Trasy piesze</span><span><Bike :size="17"/>Trasy rowerowe</span></div>
   <p class="poland-note">Opublikowane miejsca i publiczne trasy. Trasa jest liczona raz w każdym województwie, w którym ma zapisany punkt.</p>
   <span class="poland-unavailable"><i></i>Pozostałe regiony w przygotowaniu</span>
  </div>
  <div class="poland-figure">
   <svg class="poland-map" viewBox="0 0 760 730" role="group" aria-label="Mapa Polski z licznikami miejsc i tras w 16 województwach">
    <g v-for="region in overview" :key="region.slug" :data-region="region.slug" class="poland-province" :class="{'is-available':region.active}" role="button" tabindex="0" :aria-label="label(region)" :aria-disabled="!region.active" @click="select(region)" @keydown.enter.prevent="select(region)" @keydown.space.prevent="select(region)">
     <title>{{label(region)}}</title>
     <path :d="region.path" fill-rule="evenodd"/>
     <g class="province-label" :transform="`translate(${region.center.join(',')})`" pointer-events="none" aria-hidden="true">
      <text v-for="(line,i) in region.lines" :key="line" class="province-name" text-anchor="middle" :y="region.lines.length>1?-24+i*14:-12">{{line}}</text>
      <text class="province-places" text-anchor="middle" y="9">{{compact(region.places)}} <tspan>{{words(region.places,'miejsce','miejsca','miejsc')}}</tspan></text>
      <Footprints x="-39" y="17" width="13" height="13"/><text class="province-routes" x="-22" y="28">{{compact(region.walking)}}</text>
      <Bike x="7" y="17" width="14" height="14"/><text class="province-routes" x="25" y="28">{{compact(region.cycling)}}</text>
     </g>
    </g>
   </svg>
   <p class="poland-attribution">Kontury poglądowe: <a href="https://www.geoboundaries.org/api/current/gbOpen/POL/ADM1/" target="_blank" rel="noopener noreferrer">geoBoundaries</a> / © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> · <a href="/datasets/poland-voivodeships-source.json">ODbL · źródło</a></p>
  </div>
  <details class="poland-region-list">
   <summary>Lista województw i liczników</summary>
   <div class="poland-region-rows"><button v-for="region in overview" :key="region.slug" :disabled="!region.active" :aria-label="label(region)" @click="select(region)"><strong>{{region.name}}</strong><span><span><MapPin :size="14"/>{{region.places}}</span><span><Footprints :size="14"/>{{region.walking}}</span><span><Bike :size="14"/>{{region.cycling}}</span><ArrowUpRight v-if="region.active" :size="16"/></span></button></div>
  </details>
 </section>
</template>

<style scoped>
.poland-regions{display:grid;grid-template-columns:minmax(210px,.8fr) minmax(0,2fr);gap:12px 32px;align-items:center;margin:28px 0 54px;border:1px solid #dfe7d6;border-radius:18px;background:#f6f8f2;padding:32px}.poland-intro h2{font-size:34px;line-height:1.15;letter-spacing:-1px;margin:14px 0 20px;color:#234734}.poland-intro h2>span{color:#97ad70}.poland-intro>p{font-size:13px;line-height:1.9;color:#687b5f;max-width:290px}.poland-total{display:flex;flex-direction:column;margin:26px 0}.poland-total strong{font-size:42px;line-height:1.1;letter-spacing:-2px;color:#245f42}.poland-total>span{font-size:12px;color:#687b5f;margin-top:8px}.poland-legend{display:flex;flex-direction:column;gap:13px;font-size:12px;color:#315c43}.poland-legend>span{display:flex;align-items:center;gap:10px}.poland-intro>.poland-note{font-size:10px;line-height:1.8;margin-top:20px;color:#788570}.poland-unavailable{display:flex;align-items:center;gap:8px;font-size:10px;color:#87917e;margin-top:20px}.poland-unavailable i{display:inline-block;width:11px;height:11px;background:#e9ede2;border:1px solid #cdd5c4;border-radius:3px}.poland-figure{min-width:0}.poland-map{display:block;width:100%;max-height:650px;overflow:visible}.poland-province{color:#6c7b60;outline:none}.poland-province>path{fill:#edf0e6;stroke:#b9c7ac;stroke-width:1.25;stroke-linejoin:round;transition:fill .15s,stroke .15s}.poland-province.is-available{cursor:pointer;color:#245c3d}.poland-province.is-available>path{fill:#d9e6c9;stroke:#90ac78}.poland-province.is-available:hover>path,.poland-province.is-available:focus-visible>path{fill:#c0d8a8;stroke:#315f40;stroke-width:2.5}.province-name{font:600 13.5px system-ui,sans-serif;fill:currentColor}.province-places{font:700 18px system-ui,sans-serif;fill:currentColor}.province-places tspan{font-size:11px;font-weight:400}.province-routes{font:600 12px system-ui,sans-serif;fill:currentColor}.poland-attribution{font-size:9px;line-height:1.8;color:#839077;text-align:right;margin:7px 0 0}.poland-attribution a{color:inherit}.poland-region-list{grid-column:1/-1;border-top:1px solid #dfe7d6;padding-top:15px;font-size:12px;color:#45653a}.poland-region-list summary{cursor:pointer}.poland-region-rows{display:grid;grid-template-columns:1fr 1fr;gap:0 24px;margin-top:14px}.poland-region-rows button{display:flex;align-items:center;justify-content:space-between;gap:12px;width:100%;border:0;border-bottom:1px solid #e0e7d8;background:none;padding:13px 0;text-align:left;color:#315c43;font:inherit;cursor:pointer}.poland-region-rows button>span{display:flex;align-items:center;gap:13px;flex-shrink:0}.poland-region-rows button>span>span{display:flex;align-items:center;gap:4px}.poland-region-rows button:disabled{color:#85917c;cursor:default}.poland-region-rows button:focus-visible{outline:2px solid #19744f;outline-offset:2px}@media(max-width:850px){.poland-regions{grid-template-columns:1fr;padding:24px;gap:20px}.poland-intro>p{max-width:none}.poland-total{margin:15px 0}.poland-legend{flex-direction:row;flex-wrap:wrap;gap:16px}.poland-intro>.poland-note{margin:14px 0}.poland-unavailable{margin-top:12px}.poland-map{max-height:620px}.poland-figure{max-width:650px;width:100%;margin:auto}.poland-intro h2{font-size:30px;margin-bottom:12px}}@media(max-width:520px){.poland-regions{padding:18px 12px;border-radius:12px;margin-bottom:35px}.poland-intro{padding:0 6px}.poland-intro h2{font-size:28px}.poland-total strong{font-size:34px}.poland-map{min-height:310px}.poland-region-rows{grid-template-columns:1fr}.poland-region-rows button{font-size:11px}.poland-region-rows button>span{gap:10px}.poland-attribution{font-size:8px}.poland-region-list{padding-left:6px;padding-right:6px}.province-name{font-size:14px}.province-places{font-size:19px}}
</style>

<style scoped>.province-summary h2{font-size:24px;letter-spacing:-.6px;color:#245039;margin:0 0 19px}.province-summary-header,.province-summary-row{display:grid;grid-template-columns:minmax(100px,1fr) 49px 43px 55px;gap:8px;align-items:center}.province-summary-header{padding:0 9px 11px;color:#788d6a;border-bottom:1px solid #cfddc1;font-size:9px}.province-summary-header>span:not(:first-child){display:flex;flex-direction:column;align-items:center;gap:5px}.province-summary-rows{max-height:320px;overflow:auto;scrollbar-width:thin;scrollbar-color:#b5c7a3 transparent}.province-summary-row{width:100%;border:0;border-bottom:1px solid #dce6d2;background:transparent;text-align:left;color:#285c3c;padding:12px 9px;font-size:11px;min-height:43px}.province-summary-row>strong{font-weight:600;line-height:1.5}.province-summary-row>span{text-align:center;font-weight:700}.province-summary-row:hover:enabled{background:#e5efd9;border-radius:6px}.province-summary-row:focus-visible{outline:2px solid #19744f;outline-offset:-2px}.province-summary-row:disabled{color:#96a18c;cursor:default}.province-summary-note{font-size:9px;line-height:1.7;color:#829276;margin:12px 0 0}@media(max-width:400px){.province-summary-header,.province-summary-row{grid-template-columns:minmax(80px,1fr) 39px 35px 46px;gap:5px}.province-summary-row{font-size:10px;padding:11px 5px}.province-summary-header{font-size:8px;padding-left:5px;padding-right:5px}}</style>
