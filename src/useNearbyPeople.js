import {ref,watch,onBeforeUnmount} from 'vue'
import {readApiJson} from './apiResponse.js'

const intervalMs=12000
export function freshSharedPosition(point,now=Date.now()){
 return Number.isFinite(point?.lat)&&Math.abs(point.lat)<=90&&Number.isFinite(point?.lng)&&Math.abs(point.lng)<=180&&Number.isFinite(point?.accuracy)&&point.accuracy>=0&&point.accuracy<=100&&Number.isFinite(point?.measuredAt)&&now-point.measuredAt>=-30000&&now-point.measuredAt<=30000
}
export function useNearbyPeople({position,token,requestGps,interval=intervalMs}){
 const enabled=ref(false),people=ref([]),busy=ref(false),stopping=ref(false),error=ref(''),connected=ref(false)
 let session=null,generation=0,timer,expiryTimer,disposed=false,lastAttempt=0
 async function request(path,{method='GET',body,auth=token.value,keepalive=false}={}){
  const response=await fetch('/api/live-location'+path,{method,headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth},...(body?{body:JSON.stringify(body)}:{}),keepalive,signal:AbortSignal.timeout(8000)})
  if(!response.ok){const problem=Object.assign(new Error('Nie udało się połączyć z osobami w pobliżu.'),{status:response.status});throw problem}
  return response.status===204?null:readApiJson(response)
 }
 async function remove(current){
  if(!current)return
  stopping.value=true
  try{await request('',{method:'DELETE',auth:current.token,body:{session_id:current.id},keepalive:true})}
  catch{if(!disposed&&!enabled.value)error.value='Brak potwierdzenia wyłączenia na serwerze. Ostatnia pozycja zniknie najpóźniej po 2 minutach.'}
  finally{stopping.value=false}
 }
 async function sync(){
  if(disposed||!enabled.value||!token.value||busy.value||document.visibilityState==='hidden')return
  people.value=people.value.filter(person=>Date.parse(person.expires_at)>Date.now())
  if(navigator.onLine===false){people.value=[];connected.value=false;error.value='Brak internetu. Pozycja nie jest aktualizowana.';return}
  const point=position.value
  if(!freshSharedPosition(point)){people.value=[];connected.value=false;error.value='Czekam na aktualny, dokładny odczyt GPS.';return}
  const current= generation,auth=token.value
  busy.value=true;lastAttempt=Date.now();error.value=''
  const payload={lat:point.lat,lng:point.lng,accuracy:point.accuracy,measured_at:new Date(point.measuredAt).toISOString()}
  try{
   if(!session){
    const result=await request('',{method:'POST',body:payload,auth})
    if(typeof result.session_id!=='string')throw Error('Nieprawidłowa odpowiedź serwera.')
    const created={id:result.session_id,token:auth}
    if(disposed||current!==generation||!enabled.value){await remove(created);return}
    session=created
   }else{
    await request('',{method:'PUT',body:{...payload,session_id:session.id},auth:session.token})
   }
   if(disposed||current!==generation)return
   const result=await request('/nearby?radius_km=5',{auth})
   if(disposed||current!==generation)return
   people.value=(Array.isArray(result.people)?result.people:[]).filter(person=>Number.isFinite(person.lat)&&Math.abs(person.lat)<=90&&Number.isFinite(person.lng)&&Math.abs(person.lng)<=180&&Date.parse(person.expires_at)>Date.now()).slice(0,100)
   connected.value=true
  }catch(problem){
   if(disposed||current!==generation)return
   people.value=[];connected.value=false
   if(problem.status===401){enabled.value=false;error.value='Sesja wygasła. Zaloguj się ponownie, aby udostępniać pozycję.'}
   else if(problem.status===403||problem.status===409){session=null;error.value='Odnawiam udostępnianie. Pozycja pojawi się przy kolejnej aktualizacji.'}
   else error.value=problem.message==='Nieprawidłowa odpowiedź serwera.'?problem.message:'Nie udało się odświeżyć osób w pobliżu. Spróbuję ponownie.'
  }finally{
   busy.value=false
   if(!disposed&&enabled.value&&current!==generation)sync()
  }
 }
 function terminate(){
  generation++;clearInterval(timer);clearInterval(expiryTimer);timer=null;expiryTimer=null
  const previous=session;session=null;people.value=[];connected.value=false;error.value=''
  remove(previous)
 }
 watch(enabled,value=>{
  if(!value){terminate();return}
  if(!token.value){enabled.value=false;error.value='Zaloguj się, aby udostępniać pozycję.';return}
  generation++;error.value='';lastAttempt=0;requestGps?.();sync();timer=setInterval(sync,interval)
  expiryTimer=setInterval(()=>{const current=people.value.filter(person=>Date.parse(person.expires_at)>Date.now());if(current.length!==people.value.length)people.value=current},1000)
 },{flush:'sync'})
 watch(position,()=>{if(enabled.value&&(!session||Date.now()-lastAttempt>=interval))sync()})
 watch(token,()=>{if(enabled.value)enabled.value=false})
 function visibility(){
  if(document.visibilityState==='hidden'){people.value=[];return}
  if(enabled.value){requestGps?.();sync()}
 }
 function network(){if(enabled.value)sync()}
 function pagehide(){if(enabled.value)enabled.value=false}
 document.addEventListener('visibilitychange',visibility)
 window.addEventListener('online',network);window.addEventListener('offline',network);window.addEventListener('pagehide',pagehide)
 onBeforeUnmount(()=>{
  disposed=true;enabled.value=false;terminate()
  document.removeEventListener('visibilitychange',visibility)
  window.removeEventListener('online',network);window.removeEventListener('offline',network);window.removeEventListener('pagehide',pagehide)
 })
 return {enabled,people,busy,stopping,error,connected,refresh:sync}
}
