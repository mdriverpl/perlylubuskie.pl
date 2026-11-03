import {ref,watch,onBeforeUnmount} from 'vue'
import {readApiJson} from './apiResponse.js'

const storageKey='perly:trip-metrics'
const lifetime=7*24*60*60*1000
const valid=value=>Number.isFinite(value?.distance_m)&&value.distance_m>=0&&Number.isFinite(value?.duration_s)&&value.duration_s>=0
export const tripDistance=value=>new Intl.NumberFormat('pl',{maximumFractionDigits:2}).format(value.distance_m/1000)
export function tripDuration(value){const minutes=Math.round(value.duration_s/60);return minutes<60?minutes+' min':Math.floor(minutes/60)+' h'+(minutes%60?' '+minutes%60+' min':'')}
export function tripMetricPayload(route){
 const ids=route.place_ids||[]
 const payload={place_ids:[...ids],transport:route.transport}
 for(const field of ['custom_points','point_positions']){
  const points=(route[field]||[]).filter(p=>ids.includes(p.id)).map(p=>field==='custom_points'?{id:p.id,name:p.name,lat:p.lat,lng:p.lng}:{id:p.id,lat:p.lat,lng:p.lng})
  if(points.length)payload[field]=points
 }
 return payload
}
export function tripMetricKey(route){const payload=tripMetricPayload(route);return JSON.stringify([payload.transport,payload.place_ids,...['custom_points','point_positions'].map(field=>(payload[field]||[]).map(({id,lat,lng})=>[id,lat,lng]).sort((a,b)=>a[0]-b[0]))])}

export function useTripMetrics({routes,enabled,online}){
 const cache=ref({}),states=ref({})
 let generation=0,timer,controller
 try{for(const [key,value] of Object.entries(JSON.parse(localStorage.getItem(storageKey)||'{}')).slice(-200)){if(valid(value)&&value.expires>Date.now())cache.value[key]=value}}catch{}
 function remember(route,value){
  if(!valid(value))return
  const key=tripMetricKey(route)
  cache.value={...cache.value,[key]:{distance_m:value.distance_m,duration_s:value.duration_s,expires:Date.now()+lifetime}}
  cache.value=Object.fromEntries(Object.entries(cache.value).slice(-200))
  try{localStorage.setItem(storageKey,JSON.stringify(cache.value))}catch{}
 }
 function get(route){const cached=cache.value[tripMetricKey(route)];return cached?.expires>Date.now()?cached:null}
 function state(route){return get(route)?'ready':!['walk','bike'].includes(route.transport)?'unsupported':!online.value?'offline':states.value[tripMetricKey(route)]||'loading'}
 function start(){
  clearTimeout(timer);controller?.abort();const current=++generation;states.value={}
  if(!enabled.value||!online.value)return
  const pending=[...routes.value]
  timer=setTimeout(async()=>{
   for(const route of pending){
    if(current!==generation)return
    if(get(route)||!['walk','bike'].includes(route.transport))continue
    if(route.place_ids?.length===1){remember(route,{distance_m:0,duration_s:0});continue}
    const key=tripMetricKey(route);states.value[key]='loading'
    const active=new AbortController();controller=active
    const timeout=setTimeout(()=>active.abort(),45000)
    try{
     const response=await fetch('/api/routing',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(tripMetricPayload(route)),signal:active.signal})
     const data=await readApiJson(response,'Nie udało się obliczyć długości i czasu wycieczki.')
     if(!valid(data))throw Error('Invalid trip metrics')
     if(current===generation)remember(route,data)
    }catch{if(current===generation)states.value[key]='error'}
    finally{clearTimeout(timeout)}
   }
  },100)
 }
 watch(()=>[enabled.value,online.value,routes.value.map(tripMetricKey).join('|')],start,{immediate:true})
 onBeforeUnmount(()=>{generation++;clearTimeout(timer);controller?.abort()})
 return {get,state,remember,retry:start}
}
