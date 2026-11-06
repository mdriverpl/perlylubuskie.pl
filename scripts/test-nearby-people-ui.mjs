import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage','navigator'])Object.defineProperty(globalThis,key,{value:dom.window[key],configurable:true})
let online=true
Object.defineProperty(navigator,'onLine',{get:()=>online})
const {createApp,ref,computed,h,nextTick}=await import('vue')
const {useNearbyPeople,freshSharedPosition}=await import('../src/useNearbyPeople.js')
const Navigation=(await import('../artifacts/trip-navigation-test.mjs')).default
const requests=[]
let pendingStart,delayStart=false,denyStop=false,gpsRequests=0
const peer={id:2,name:'Inna osoba',lat:52.331,lng:15.29,accuracy:8,distance_m:111,updated_at:new Date().toISOString(),expires_at:new Date(Date.now()+120000).toISOString()}
globalThis.fetch=async(url,options={})=>{
 requests.push({url,method:options.method,auth:options.headers.Authorization,guestToken:options.headers['X-Location-Token'],body:options.body?JSON.parse(options.body):null})
 if(options.method==='POST'&&delayStart)await new Promise(resolve=>pendingStart=resolve)
 if(options.method==='DELETE')return {ok:!denyStop,status:denyStop?503:204}
 return {ok:true,status:200,json:async()=>options.method==='POST'?{session_id:'test-sharing-session',guest_token:'test-guest-sharing-token'}:url.includes('/nearby')?{people:[peer,{...peer,id:3,expires_at:'2020-01-01T00:00:00Z'}]}:{ttl_seconds:120}}
}
const position=ref({lat:52.33,lng:15.29,accuracy:8,measuredAt:Date.now()}),token=ref('own-token')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
let nearby
let app=createApp({setup(){nearby=useNearbyPeople({position,token,interval:30000,requestGps:()=>gpsRequests++});return()=>null}})
app.mount('#app');await settle()
assert.equal(requests.length,0,'Opening navigation never transmits a location without opt-in')
nearby.enabled.value=true;await settle();await settle()
assert.equal(gpsRequests,1)
assert.deepEqual(requests.map(r=>r.method),['POST','GET'])
assert.equal(requests[0].body.lat,52.33)
assert.equal(requests[0].body.measured_at,new Date(position.value.measuredAt).toISOString())
assert.equal(nearby.people.value.length,1,'Expired positions are not displayed')
assert.equal(nearby.connected.value,true)
position.value={...position.value,lat:52.332,measuredAt:Date.now()};await settle();await nearby.refresh()
assert.equal(requests.at(-2).method,'PUT')
assert.equal(requests.at(-2).body.lat,52.332)
assert.equal(requests.at(-2).body.session_id,'test-sharing-session')
online=false;window.dispatchEvent(new Event('offline'));await settle()
assert.equal(nearby.people.value.length,0)
assert.match(nearby.error.value,/Brak internetu/)
const offlineCount=requests.length;await nearby.refresh();assert.equal(requests.length,offlineCount)
online=true;window.dispatchEvent(new Event('online'));await settle();await settle()
assert.equal(nearby.people.value.length,1)
token.value='';await settle();await settle()
assert.equal(nearby.enabled.value,false,'Logout immediately disables publishing')
assert.equal(requests.at(-1).method,'DELETE')
assert.equal(requests.at(-1).auth,'Bearer own-token','Stop uses the authenticated session that originally opted in')
assert.equal(nearby.people.value.length,0)
app.unmount()

// A response arriving after the user stops is cleaned up instead of activating sharing.
token.value='own-token';delayStart=true
app=createApp({setup(){nearby=useNearbyPeople({position,token,interval:30000});return()=>null}});app.mount('#app')
nearby.enabled.value=true;await settle();assert.ok(pendingStart)
nearby.enabled.value=false;pendingStart();await settle();await settle()
assert.equal(requests.at(-1).method,'DELETE')
assert.equal(nearby.connected.value,false)
assert.equal(nearby.people.value.length,0)
app.unmount();delayStart=false

// Old fixes never renew server visibility; the next actual GPS fix starts sharing.
position.value={...position.value,measuredAt:Date.now()-90000}
app=createApp({setup(){nearby=useNearbyPeople({position,token,interval:30000});return()=>null}});app.mount('#app')
const staleCount=requests.length
nearby.enabled.value=true;await settle()
assert.equal(requests.length,staleCount)
assert.match(nearby.error.value,/aktualny/)
position.value={...position.value,measuredAt:Date.now()};await settle();await settle()
assert.equal(nearby.connected.value,true)
denyStop=true;nearby.enabled.value=false;await settle();await settle()
assert.match(nearby.error.value,/2 minutach/,'A failed network stop honestly reports expiry rather than confirmed deletion')
app.unmount();denyStop=false

// Actual navigation controls expose consent, participants and immediate stop.
const props=ref({user:{id:1,name:'Ja'},token:'own-token',position:position.value})
app=createApp({render:()=>h(Navigation,{...props.value,onRefresh:()=>gpsRequests++})});app.mount('#app');await settle()
document.querySelector('[aria-controls="navigation-options"]').click();await settle()
assert.equal(document.querySelector('.nearby-sharing-toggle').checked,false)
document.querySelector('.nearby-sharing-toggle').click();await settle();await settle()
assert.match(document.querySelector('.nearby-people-status').textContent,/osoby w pobliżu: 1/)
document.querySelector('.nearby-sharing-stop').click();await settle();await settle()
assert.equal(document.querySelector('.nearby-people-status'),null)
assert.equal(document.querySelector('.nearby-sharing-toggle').checked,false)
assert.equal(requests.at(-1).method,'DELETE')
const before=requests.length
props.value={...props.value,token:'',user:null};await settle()
assert.equal(document.querySelector('.nearby-sharing-toggle').disabled,false,'A nickname allows sharing without login')
assert.equal(requests.length,before)
document.querySelector('.nearby-sharing-toggle').click();await settle();await settle()
assert.equal(requests.at(-2).url,'/api/live-location/guest')
assert.equal(requests.at(-2).body.nick,'Ja')
assert.equal(requests.at(-2).auth,undefined,'Guest publishing does not need an account token')
assert.equal(requests.at(-1).guestToken,'test-guest-sharing-token')
document.querySelector('.nearby-sharing-stop').click();await settle();await settle()
assert.equal(requests.at(-1).url,'/api/live-location/guest')
assert.equal(requests.at(-1).guestToken,'test-guest-sharing-token')
app.unmount()

assert.equal(freshSharedPosition({...position.value,measuredAt:Date.now()-60000}),false)
assert.equal(freshSharedPosition({...position.value,accuracy:150}),false)
assert.equal(freshSharedPosition({...position.value,measuredAt:null}),false)
assert.equal(localStorage.getItem('perly:nearby-people'),null,'Other people’s locations are not saved offline')
dom.window.close()
console.log('PASS: explicit opt-in, authenticated live updates, current GPS only, stale peers, offline/online, logout/stop, late response cleanup and navigation controls')
