import { ref, watch, onBeforeUnmount } from 'vue'
import {movementDirection} from './navigationDirections.js'

export const geolocationKey=Symbol('geolocation')

export function useGeolocation(){
 const position=ref(null),loading=ref(false),error=ref('')
 let storedInterval=15000,storedAccuracy=true
 try{const value=localStorage.getItem('perly:gps-interval');if(value!==null&&[0,5000,15000,30000,60000].includes(Number(value)))storedInterval=Number(value);storedAccuracy=localStorage.getItem('perly:gps-high-accuracy')!=='false'}catch{}
 const refreshInterval=ref(storedInterval),highAccuracy=ref(storedAccuracy)
 let generation=0,watchId=null,headingAnchor=null,timer,active=false
 function clearWatch(){if(watchId!==null){navigator.geolocation.clearWatch(watchId);watchId=null}}
 function pause(){generation++;clearTimeout(timer);clearWatch();loading.value=false}
 function stop(){active=false;pause();position.value=null;headingAnchor=null;error.value=''}
 function locate(){
  if(loading.value)return
  active=true;requestPosition()
 }
 function requestPosition(){
  if(!active||document.visibilityState==='hidden')return
  clearTimeout(timer)
  clearWatch()
  error.value=''
  if(!navigator.geolocation){active=false;error.value='Ta przeglądarka nie udostępnia lokalizacji.';return}
  if(window.isSecureContext===false){active=false;error.value='Lokalizacja wymaga bezpiecznego połączenia HTTPS.';return}
  const current=++generation;loading.value=true
  let completed=false
  function next(){
   completed=true
   if(refreshInterval.value>0){
    clearWatch();clearTimeout(timer)
    if(active)timer=setTimeout(requestPosition,refreshInterval.value)
   }
  }
  const success=result=>{
   if(current!==generation)return
   const {latitude:lat,longitude:lng,accuracy}=result.coords
   if(!Number.isFinite(lat)||!Number.isFinite(lng)||Math.abs(lat)>90||Math.abs(lng)>180){position.value=null;error.value='Nie udało się ustalić poprawnej lokalizacji.'}
   else {
    error.value=''
    const point={lat,lng,accuracy:Number.isFinite(accuracy)&&accuracy>=0?accuracy:null,measuredAt:Number.isFinite(result.timestamp)?result.timestamp:Date.now()}
    const direction=movementDirection(headingAnchor,point,result.coords.heading,result.coords.speed)
    headingAnchor=direction.anchor;position.value={...point,heading:direction.heading}
   }
   loading.value=false
   next()
  }
  const failure=reason=>{
   if(current!==generation)return
   position.value=null
   error.value=reason.code===1?'Brak zgody na lokalizację. Możesz ją włączyć w ustawieniach przeglądarki.':reason.code===3?'Ustalanie lokalizacji trwało zbyt długo. Spróbuj ponownie.':'Lokalizacja jest teraz niedostępna. Spróbuj ponownie.'
   loading.value=false
   if(reason.code===1){active=false;pause()}
   else next()
  }
  const options={enableHighAccuracy:highAccuracy.value,timeout:12000,maximumAge:0}
  if(refreshInterval.value===0&&typeof navigator.geolocation.watchPosition==='function'||typeof navigator.geolocation.getCurrentPosition!=='function'){
   watchId=navigator.geolocation.watchPosition(success,failure,options)
   if(current!==generation||completed&&refreshInterval.value>0)clearWatch()
  }else navigator.geolocation.getCurrentPosition(success,failure,options)
 }
 function setRefreshInterval(value){const interval=Number(value);if([0,5000,15000,30000,60000].includes(interval))refreshInterval.value=interval}
 function setHighAccuracy(value){highAccuracy.value=!!value}
 watch([refreshInterval,highAccuracy],()=>{
  try{localStorage.setItem('perly:gps-interval',String(refreshInterval.value));localStorage.setItem('perly:gps-high-accuracy',String(highAccuracy.value))}catch{}
  if(active){pause();requestPosition()}
 },{flush:'sync'})
 function visibility(){if(document.visibilityState==='hidden')pause();else if(active)requestPosition()}
 document.addEventListener('visibilitychange',visibility)
 onBeforeUnmount(()=>{document.removeEventListener('visibilitychange',visibility);stop()})
 return {position,loading,error,locate,stop,refreshInterval,highAccuracy,setRefreshInterval,setHighAccuracy}
}
