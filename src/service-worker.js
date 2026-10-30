const CACHE='perly-shell-__VERSION__'
const IMAGES='perly-images-v1'
const PRECACHE=__PRECACHE__
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(PRECACHE))))
self.addEventListener('activate',event=>event.waitUntil((async()=>{
 for(const key of await caches.keys())if(key.startsWith('perly-shell-')&&key!==CACHE)await caches.delete(key)
 await self.clients.claim()
})()))
self.addEventListener('message',event=>{if(event.data?.type==='SKIP_WAITING')self.skipWaiting()})
self.addEventListener('fetch',event=>{
 const request=event.request,url=new URL(request.url)
 // Private responses, GPS, routing and supplier map tiles never enter a cache.
 if(request.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return
 if(request.mode==='navigate'){
  event.respondWith(fetch(request).catch(()=>caches.open(CACHE).then(cache=>cache.match('/index.html'))))
  return
 }
 if(PRECACHE.includes(url.pathname)){
  event.respondWith(caches.open(CACHE).then(async cache=>(await cache.match(url.pathname))||fetch(request)))
  return
 }
 if(url.pathname.startsWith('/images/')){
  event.respondWith((async()=>{
   const cache=await caches.open(IMAGES),saved=await cache.match(request)
   if(saved)return saved
   try{
    const response=await fetch(request)
    if(response.ok){await cache.put(request,response.clone());const keys=await cache.keys();for(const key of keys.slice(0,Math.max(0,keys.length-80)))await cache.delete(key)}
    return response
   }catch{return (await caches.open(CACHE)).match('/images/heritage-placeholder.svg')}
  })())
 }
})
