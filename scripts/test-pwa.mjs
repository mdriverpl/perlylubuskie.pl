import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import vm from 'node:vm'
import sharp from 'sharp'
const manifest=JSON.parse(await fs.readFile('public/manifest.webmanifest','utf8'))
assert.equal(manifest.display,'standalone');assert.equal(manifest.start_url,'/?view=places')
assert.ok(manifest.icons.some(i=>i.purpose==='maskable'))
for(const icon of manifest.icons){const metadata=await sharp('public'+icon.src).metadata();assert.equal(`${metadata.width}x${metadata.height}`,icon.sizes)}
const handlers={},stored=new Map(),deleted=[]
const cache={addAll:async files=>files.forEach(p=>stored.set(p,new Response(p))),match:async request=>stored.get(typeof request==='string'?request:request.url),put:async()=>{},keys:async()=>[]}
const caches={open:async()=>cache,keys:async()=>['perly-shell-old','unrelated-app'],delete:async key=>deleted.push(key)}
const self={location:{origin:'https://perly.test'},addEventListener:(name,fn)=>handlers[name]=fn,clients:{claim:async()=>{}},skipWaiting:()=>{self.skipped=true}}
let networkFails=false
const source=(await fs.readFile('src/service-worker.js','utf8')).replace('__VERSION__','test').replace('__PRECACHE__',JSON.stringify(['/index.html','/assets/app.js','/images/heritage-placeholder.svg']))
vm.runInNewContext(source,{self,caches,URL,fetch:async()=>{if(networkFails)throw Error('offline');return new Response('network')}})
let job
handlers.install({waitUntil:p=>job=p});await job
assert.ok(stored.has('/index.html'));handlers.activate({waitUntil:p=>job=p});await job
assert.deepEqual(deleted,['perly-shell-old'])
for(const [url,method] of [['https://perly.test/api/routes','GET'],['https://perly.test/api/maps/tiles/terrain/1/1/1','GET'],['https://perly.test/api/auth/login','POST'],['https://tiles.example/1.png','GET']]){
 let intercepted=false;handlers.fetch({request:{url,method,mode:'cors'},respondWith(){intercepted=true}});assert.equal(intercepted,false,'Private/API/map requests bypass caches')
}
networkFails=true
handlers.fetch({request:{url:'https://perly.test/?view=places',method:'GET',mode:'navigate'},respondWith:p=>job=p})
assert.equal(await(await job).text(),'/index.html')
handlers.message({data:{type:'SKIP_WAITING'}});assert.equal(self.skipped,true)
console.log('PASS: PWA manifest/icons, offline shell, cache version cleanup and API/private/map cache isolation')
