import { ref, watch, onBeforeUnmount } from 'vue'

export function useRouting({ ids, transport, enabled, online }) {
 const route=ref(null), loading=ref(false), error=ref('')
 let timer, controller, generation=0
 function refresh() {
  clearTimeout(timer); controller?.abort(); const current=++generation
  route.value=null; error.value=''; loading.value=false
  if(!enabled.value || !online.value || transport.value==='car' || ids.value.length<2) return
  loading.value=true
  const payload={place_ids:[...ids.value],transport:transport.value}
  timer=setTimeout(async()=>{
   const activeController=new AbortController();controller=activeController
   const timeout=setTimeout(()=>activeController.abort(),45000)
   try {
    const response=await fetch('/api/routing',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:activeController.signal})
    const data=await response.json()
    if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Nie udało się wyznaczyć trasy.')
    if(data.geometry?.type!=='LineString' || data.geometry.coordinates.length<2 || !Number.isFinite(data.distance_m) || !Number.isFinite(data.duration_s))throw new Error('Otrzymano nieprawidłową trasę.')
    if(current===generation)route.value=data
   } catch(e) {
    if(current===generation)error.value=e.name==='AbortError'?'Wyznaczanie trasy trwało zbyt długo. Spróbuj ponownie.':e.message
   } finally { clearTimeout(timeout); if(current===generation)loading.value=false }
  },350)
 }
 watch(()=>[enabled.value,online.value,transport.value,JSON.stringify(ids.value)],refresh,{immediate:true})
 onBeforeUnmount(()=>{generation++;clearTimeout(timer);controller?.abort()})
 return {route,loading,error,refresh}
}

export function buildGpx(name,places,route) {
 const escape=s=>String(s).replace(/[<>&"']/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&apos;'}[c]))
 const waypoints=places.map(p=>`<wpt lat="${p.lat}" lon="${p.lng}"><name>${escape(p.name)}</name></wpt>`).join('')
 const track=route?`<trk><name>${escape(name)}</name><trkseg>${route.geometry.coordinates.map(p=>`<trkpt lat="${p[1]}" lon="${p[0]}">${Number.isFinite(p[2])?`<ele>${p[2]}</ele>`:''}</trkpt>`).join('')}</trkseg></trk>`:`<rte><name>${escape(name)}</name>${places.map(p=>`<rtept lat="${p.lat}" lon="${p.lng}"><name>${escape(p.name)}</name></rtept>`).join('')}</rte>`
 return `<?xml version="1.0" encoding="UTF-8"?><gpx version="1.1" creator="Perły Ziemi Lubuskiej" xmlns="http://www.topografix.com/GPX/1/1"><metadata><desc>${route?'Trasa BRouter / OpenStreetMap. Sprawdź warunki w terenie.':'Tylko punkty do odwiedzenia, bez przebiegu po drogach.'}</desc></metadata>${waypoints}${track}</gpx>`
}
