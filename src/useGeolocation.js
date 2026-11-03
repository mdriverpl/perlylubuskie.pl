import { ref, onBeforeUnmount } from 'vue'
import {movementDirection} from './navigationDirections.js'

export const geolocationKey=Symbol('geolocation')

export function useGeolocation(){
 const position=ref(null),loading=ref(false),error=ref('')
 let generation=0,watchId=null,headingAnchor=null
 function clearWatch(){if(watchId!==null){navigator.geolocation.clearWatch(watchId);watchId=null}}
 function stop(){generation++;clearWatch();position.value=null;headingAnchor=null;loading.value=false;error.value=''}
 function locate(){
  if(loading.value)return
  clearWatch()
  error.value=''
  if(!navigator.geolocation){error.value='Ta przeglądarka nie udostępnia lokalizacji.';return}
  if(window.isSecureContext===false){error.value='Lokalizacja wymaga bezpiecznego połączenia HTTPS.';return}
  const current=++generation;loading.value=true
  const success=result=>{
   if(current!==generation)return
   const {latitude:lat,longitude:lng,accuracy}=result.coords
   if(!Number.isFinite(lat)||!Number.isFinite(lng)||Math.abs(lat)>90||Math.abs(lng)>180){position.value=null;error.value='Nie udało się ustalić poprawnej lokalizacji.'}
   else {
    error.value=''
    const point={lat,lng,accuracy:Number.isFinite(accuracy)&&accuracy>=0?accuracy:null}
    const direction=movementDirection(headingAnchor,point,result.coords.heading,result.coords.speed)
    headingAnchor=direction.anchor;position.value={...point,heading:direction.heading}
   }
   loading.value=false
  }
  const failure=reason=>{
   if(current!==generation)return
   position.value=null
   error.value=reason.code===1?'Brak zgody na lokalizację. Możesz ją włączyć w ustawieniach przeglądarki.':reason.code===3?'Ustalanie lokalizacji trwało zbyt długo. Spróbuj ponownie.':'Lokalizacja jest teraz niedostępna. Spróbuj ponownie.'
   loading.value=false
   if(reason.code===1){generation++;clearWatch()}
  }
  const options={enableHighAccuracy:true,timeout:12000,maximumAge:0}
  if(typeof navigator.geolocation.watchPosition==='function')watchId=navigator.geolocation.watchPosition(success,failure,options)
  else navigator.geolocation.getCurrentPosition(success,failure,options)
 }
 onBeforeUnmount(stop)
 return {position,loading,error,locate,stop}
}
