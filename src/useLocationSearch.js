import {ref,onBeforeUnmount} from 'vue'
export function useLocationSearch(){
 const items=ref([]),selected=ref(null),loading=ref(false),error=ref('')
 let controller,version=0
 function clear(){version++;controller?.abort();items.value=[];selected.value=null;loading.value=false;error.value=''}
 async function search(query){
  clear();const text=query.trim()
  if(text.length<2)return
  const current=version;controller=new AbortController();loading.value=true
  try{
   const response=await fetch('/api/maps/search?q='+encodeURIComponent(text),{signal:AbortSignal.any([controller.signal,AbortSignal.timeout(12000)])})
   const data=await response.json()
   if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Wyszukiwanie miejscowości jest niedostępne.')
   if(current!==version)return
   items.value=data.items||[]
   if(items.value.length===1)selected.value=items.value[0]
   if(!items.value.length)error.value='Nie znaleziono lokalizacji w województwie lubuskim. Spróbuj dopisać gminę lub adres.'
  }catch(e){if(current===version)error.value=e.name==='TimeoutError'?'Wyszukiwanie trwa zbyt długo. Spróbuj ponownie.':e.message||'Nie udało się wyszukać miejscowości.'}
  finally{if(current===version)loading.value=false}
 }
 onBeforeUnmount(clear)
 return {items,selected,loading,error,search,clear}
}
