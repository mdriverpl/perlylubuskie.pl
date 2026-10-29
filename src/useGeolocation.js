import { ref, onBeforeUnmount } from 'vue'

export function useGeolocation(){
 const position=ref(null),loading=ref(false),error=ref('')
 let generation=0
 function locate(){
  if(loading.value)return
  error.value=''
  if(!navigator.geolocation){error.value='Ta przeglądarka nie udostępnia lokalizacji.';return}
  if(window.isSecureContext===false){error.value='Lokalizacja wymaga bezpiecznego połączenia HTTPS.';return}
  const current=++generation;loading.value=true
  navigator.geolocation.getCurrentPosition(result=>{
   if(current!==generation)return
   const {latitude:lat,longitude:lng,accuracy}=result.coords
   if(!Number.isFinite(lat)||!Number.isFinite(lng)||Math.abs(lat)>90||Math.abs(lng)>180){error.value='Nie udało się ustalić poprawnej lokalizacji.'}
   else position.value={lat,lng,accuracy:Number.isFinite(accuracy)&&accuracy>=0?accuracy:null}
   loading.value=false
  },reason=>{
   if(current!==generation)return
   error.value=reason.code===1?'Brak zgody na lokalizację. Możesz ją włączyć w ustawieniach przeglądarki.':reason.code===3?'Ustalanie lokalizacji trwało zbyt długo. Spróbuj ponownie.':'Lokalizacja jest teraz niedostępna. Spróbuj ponownie.'
   loading.value=false
  },{enableHighAccuracy:true,timeout:12000,maximumAge:60000})
 }
 onBeforeUnmount(()=>generation++)
 return {position,loading,error,locate}
}
