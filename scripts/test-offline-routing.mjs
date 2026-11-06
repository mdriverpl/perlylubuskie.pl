import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost'})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','localStorage'])globalThis[key]=dom.window[key]
const {createApp,ref,nextTick}=await import('vue')
const {useRouting}=await import('../src/useRouting.js')
const {readOfflineRoute}=await import('../src/offlineRoutes.js')
const ids=ref([1,5]),transport=ref('walk'),enabled=ref(true),online=ref(true),pointPositions=ref([])
const route={geometry:{type:'LineString',coordinates:[[15.29,52.33],[15.30,52.34]]},distance_m:2500,duration_s:1800}
let calls=0,fail=false,routing
globalThis.fetch=async()=>{calls++;return fail?{ok:false,status:503,json:async()=>({detail:'Unavailable'})}:{ok:true,json:async()=>route}}
let app
function mount(){app=createApp({setup(){routing=useRouting({ids,transport,enabled,online,pointPositions});return()=>null}});app.mount('#app')}
async function settle(){await new Promise(r=>setTimeout(r,450));await nextTick()}
mount();await settle()
assert.deepEqual(routing.route.value,route)
assert.equal(calls,1)
assert.deepEqual(readOfflineRoute({place_ids:[1,5],transport:'walk'}),route)
online.value=false;await nextTick()
assert.deepEqual(routing.route.value,route)
assert.equal(routing.offline.value,true)
assert.equal(calls,1,'Offline restore does not call the route API')
app.unmount();mount();await nextTick()
assert.deepEqual(routing.route.value,route,'Reload restores the calculated track offline')
ids.value=[5,1];await nextTick();assert.equal(routing.route.value,null,'A reversed route never reuses a different track')
ids.value=[1,5];pointPositions.value=[{id:1,lat:52.34,lng:15.29}];await nextTick()
assert.equal(routing.route.value,null,'Moving a point requires a newly calculated route')
pointPositions.value=[];transport.value='bike';await nextTick()
assert.equal(routing.route.value,null,'Walking and cycling tracks stay separate')
transport.value='walk';await nextTick();assert.ok(routing.route.value)
online.value=true;fail=true;await settle()
assert.deepEqual(routing.route.value,route,'A temporary route server outage retains the saved route')
assert.equal(routing.offline.value,true)
assert.equal(routing.error.value,'')
app.unmount();dom.window.close()
console.log('PASS: persisted route geometry/metrics, offline reload, changed route/profile/coordinates isolation and server outage fallback')
