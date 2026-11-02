import {ref,onBeforeUnmount} from 'vue'
export function useLocationSearch(){
 const items=ref([]),selected=ref(null),loading=ref(false),error=ref('')
 let controller,version=0
 function clear(){version++;controller?.abort();items.value=[];selected.value=null;loading.value=false;error.value=''}
 async function search(query){
  const text=query.trim()
  if(text.length<2){clear();return}
  return request('/api/maps/search?q='+encodeURIComponent(text))
 }
 async function reverse(point){
  return request('/api/maps/reverse?lat='+encodeURIComponent(point.lat)+'&lng='+encodeURIComponent(point.lng),true)
 }
 async function request(url,isReverse=false){
  clear()
  const current=version;controller=new AbortController();loading.value=true
  try{
   const response=await fetch(url,{signal:AbortSignal.any([controller.signal,AbortSignal.timeout(12000)])})
   const unavailable='Wyszukiwanie adresów jest chwilowo niedostępne. Spróbuj ponownie.'
   const data=await response.json().catch(()=>{throw Error(unavailable)})
   if(!response.ok)throw Error(typeof data?.detail==='string'?data.detail:unavailable)
   if(!Array.isArray(data?.items)||!data.items.every(item=>item&&typeof item.name==='string'&&Number.isFinite(item.lat)&&Math.abs(item.lat)<=90&&Number.isFinite(item.lng)&&Math.abs(item.lng)<=180))throw Error(unavailable)
   if(current!==version)return
   items.value=data.items
   if(items.value.length===1)selected.value=items.value[0]
   if(!items.value.length)error.value=isReverse?'Nie znaleziono adresu dla tej pozycji GPS.':'Nie znaleziono lokalizacji w województwie lubuskim. Spróbuj dopisać gminę lub adres.'
   return selected.value
  }catch(e){if(current===version)error.value=e.name==='TimeoutError'?'Wyszukiwanie trwa zbyt długo. Spróbuj ponownie.':e.name==='TypeError'?'Nie udało się połączyć z wyszukiwaniem adresów. Spróbuj ponownie.':e.message||'Nie udało się wyszukać miejscowości.'}
  finally{if(current===version)loading.value=false}
 }
 onBeforeUnmount(clear)
 return {items,selected,loading,error,search,reverse,clear}
}
