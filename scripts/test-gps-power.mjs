import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage','navigator'])Object.defineProperty(globalThis,key,{value:dom.window[key],configurable:true})
const {createApp,nextTick}=await import('vue')
const {useGeolocation}=await import('../src/useGeolocation.js')
const realTimeout=globalThis.setTimeout,realClear=globalThis.clearTimeout,timers=new Map(),calls=[],cleared=[]
let timerId=0,watchId=20,visibility='visible'
Object.defineProperty(document,'visibilityState',{get:()=>visibility,configurable:true})
globalThis.setTimeout=(fn,ms)=>{const id=++timerId;timers.set(id,{fn,ms});return id}
globalThis.clearTimeout=id=>timers.delete(id)
Object.defineProperty(navigator,'geolocation',{value:{getCurrentPosition(success,failure,options){calls.push({kind:'single',success,failure,options})},watchPosition(success,failure,options){calls.push({kind:'watch',success,failure,options});return ++watchId},clearWatch(id){cleared.push(id)}}})
let gps
const app=createApp({setup(){gps=useGeolocation();return()=>null}});app.mount('#app')
function fix(index=calls.length-1){calls[index].success({coords:{latitude:52.33,longitude:15.29,accuracy:8},timestamp:Date.now()})}
function tick(ms){const entry=[...timers].find(([,job])=>job.ms===ms);assert.ok(entry,'Expected timer '+ms);timers.delete(entry[0]);entry[1].fn()}
try{
 assert.equal(calls.length,0,'Opening the app does not start GPS')
 assert.equal(gps.refreshInterval.value,15000)
 gps.locate();assert.equal(calls.length,1);assert.equal(calls[0].kind,'single');fix()
 assert.equal(calls.length,1,'A GPS fix does not leave continuous watching enabled')
 tick(15000);assert.equal(calls.length,2)
 gps.setRefreshInterval(60000);assert.equal(calls.length,3);fix()
 assert.equal(localStorage.getItem('perly:gps-interval'),'60000')
 assert.ok([...timers.values()].some(t=>t.ms===60000))
 const last=gps.position.value
 visibility='hidden';document.dispatchEvent(new Event('visibilitychange'))
 assert.equal([...timers.values()].filter(t=>t.ms>=5000).length,0,'Hidden pages cancel future GPS requests: '+JSON.stringify([...timers.values()].map(t=>t.ms)))
 calls[1].success({coords:{latitude:50,longitude:14,accuracy:8}})
 assert.equal(gps.position.value,last,'Late results cannot restart background tracking')
 visibility='visible';document.dispatchEvent(new Event('visibilitychange'));assert.equal(calls.length,4);fix()
 gps.setHighAccuracy(false);assert.equal(calls.length,5)
 assert.equal(calls.at(-1).options.enableHighAccuracy,false)
 assert.equal(localStorage.getItem('perly:gps-high-accuracy'),'false')
 fix();gps.setRefreshInterval(0)
 assert.equal(calls.at(-1).kind,'watch','Continuous watching requires the explicit live setting')
 fix();assert.equal([...timers.values()].filter(t=>t.ms>=5000).length,0)
 visibility='hidden';document.dispatchEvent(new Event('visibilitychange'));assert.deepEqual(cleared,[21])
 visibility='visible';document.dispatchEvent(new Event('visibilitychange'));assert.equal(calls.at(-1).kind,'watch')
 calls.at(-1).failure({code:1});assert.deepEqual(cleared,[21,22]);assert.equal(gps.position.value,null)
 const denied=calls.length
 document.dispatchEvent(new Event('visibilitychange'));assert.equal(calls.length,denied,'Denied permission never retries automatically')
 app.unmount();assert.equal([...timers.values()].filter(t=>t.ms>=5000).length,0)
 console.log('PASS: GPS polling default/interval preferences, lower accuracy, no continuous watch by default, background pause/resume, stale callbacks, denial and cleanup')
}finally{globalThis.setTimeout=realTimeout;globalThis.clearTimeout=realClear;dom.window.close()}
