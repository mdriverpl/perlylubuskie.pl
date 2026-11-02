<script setup>
import {ref,inject,watch,nextTick} from 'vue'
import MapPin from 'lucide-vue-next/dist/esm/icons/map-pin.js'
import Search from 'lucide-vue-next/dist/esm/icons/search.js'
import LocateFixed from 'lucide-vue-next/dist/esm/icons/locate-fixed.js'
import {geolocationKey} from '../useGeolocation.js'
import {useLocationSearch} from '../useLocationSearch.js'
import {readAddress,rememberAddress} from '../rememberedAddress.js'
const emit=defineEmits(['found'])
const remembered=readAddress()
const address=ref(remembered?.query||''),waitingGps=ref(false)
const {position,loading:locating,error:gpsError,locate}=inject(geolocationKey)
const {items,loading,error,search,reverse,clear}=useLocationSearch()
watch(address,()=>{waitingGps.value=false;clear()},{flush:'sync'})
function choose(location){rememberAddress(address.value,location);emit('found',location)}
async function submit(){
 waitingGps.value=false
 if(address.value.trim().length<2)return
 const saved=readAddress()
 if(saved?.query===address.value){choose(saved.location);return}
 const result=await search(address.value)
 if(result)choose(result)
}
async function resolveGps(point){
 const result=await reverse(point)
 if(!result)return
 address.value=result.name
 await nextTick()
 choose({...result,lat:point.lat,lng:point.lng})
}
function fromGps(){
 clear()
 if(position.value){resolveGps({...position.value});return}
 waitingGps.value=true;locate()
}
watch([position,gpsError,locating],([point,failure,busy])=>{
 if(!waitingGps.value)return
 if(point){waitingGps.value=false;resolveGps({...point})}
 else if(failure||!busy)waitingGps.value=false
})
</script>

<template>
 <section class="home-address-search" aria-labelledby="home-address-title">
  <h3 id="home-address-title"><MapPin :size="17"/>Szukaj po adresie</h3>
  <p>Znajdź miejsca w pobliżu wybranego adresu.</p>
  <form @submit.prevent="submit">
   <input id="home-address" v-model="address" aria-label="Adres do wyszukania miejsc" placeholder="Wpisz adres lub miejscowość…" autocomplete="street-address" maxlength="200">
   <button class="home-address-gps" type="button" aria-label="Wyszukaj miejsca według GPS" title="Użyj GPS i wyszukaj miejsca" :disabled="waitingGps||loading" :aria-busy="waitingGps||loading" @click="fromGps"><LocateFixed :size="20"/></button>
   <button class="home-address-submit" type="submit" :disabled="loading||waitingGps||address.trim().length<2"><Search :size="17"/><span>Szukaj</span></button>
  </form>
  <p v-if="waitingGps||loading" class="home-address-status" role="status">{{waitingGps?'Ustalam pozycję GPS…':'Szukam adresu…'}}</p>
  <p v-if="error||gpsError" class="home-address-error" role="alert">{{error||gpsError}}</p>
  <div v-if="items.length>1" class="home-address-matches" aria-label="Wybierz adres"><button v-for="item in items" :key="item.id" type="button" @click="choose(item)">{{item.name}}</button></div>
 </section>
</template>

<style scoped>
.home-address-search{margin-top:22px;padding-top:21px;border-top:1px solid #cbd9c0}.home-address-search h3{display:flex;align-items:center;gap:7px;font-size:17px;color:#234d34}.home-address-search>p{font-size:11px;line-height:1.7;color:#687f60;margin:7px 0 12px}.home-address-search form{display:flex;align-items:center;gap:7px;background:#fff;padding:6px;border:1px solid #bacfb0;border-radius:10px}.home-address-search input{flex:1;min-width:0;width:100%;padding:9px 7px;font:inherit;font-size:12px;color:#1d3d30;border:0;background:transparent}.home-address-search input:focus{outline:0}.home-address-search form:focus-within{outline:3px solid #b7d7846b;border-color:#6d9e59}.home-address-search button{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-height:40px;border-radius:7px;padding:9px 11px;font-size:11px;font-weight:700;flex-shrink:0}.home-address-gps{background:#edf4e6;color:#19744f;border:1px solid #d7e3cd}.home-address-submit{background:#19744f;color:#fff}.home-address-search button:disabled{opacity:.5;cursor:wait}.home-address-search button:focus-visible{outline:2px solid #19744f;outline-offset:2px}.home-address-search .home-address-error{color:#9b4234}.home-address-matches{display:grid;gap:6px;margin-top:10px}.home-address-matches button{text-align:left;justify-content:flex-start;background:#f4f8ed;color:#365b35;line-height:1.6}.home-address-search .home-address-status{margin-bottom:0}@media(max-width:400px){.home-address-submit span{display:none}.home-address-search button{padding:8px}.home-address-search input{font-size:11px}}
</style>
