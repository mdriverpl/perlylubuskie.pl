export async function registerPwa(){
 if(!import.meta.env.PROD||!('serviceWorker' in navigator)||!window.isSecureContext)return
 try{
  const registration=await navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'})
  const announce=()=>window.dispatchEvent(new CustomEvent('perly:pwa-update',{detail:registration}))
  if(registration.waiting)announce()
  registration.addEventListener('updatefound',()=>{
   const worker=registration.installing
   worker?.addEventListener('statechange',()=>{if(worker.state==='installed'&&navigator.serviceWorker.controller)announce()})
  })
 }catch{window.dispatchEvent(new CustomEvent('perly:pwa-error'))}
}
