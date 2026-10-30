import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {demoPlaces} from '../src/data.js'
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
const points=[{id:-810000,name:'Jezioro Łagowskie',lat:52.33,lng:15.29},{id:-810001,name:'Punkt trasy',lat:52.32,lng:15.28},{id:-810002,name:'Powrót',lat:52.33,lng:15.29}]
const plan={name:'Spacer <b>AI</b>',description:'Wokół jeziora',transport:'walk',place_ids:points.map(p=>p.id),custom_points:points,sources:[],geometry:{type:'LineString',coordinates:points.map(p=>[p.lng,p.lat])},distance_m:9000,duration_s:7200}
let fail=true,requests=0,routing,lastPrompt
globalThis.fetch=async(path,options={})=>{
 let data,ok=true
 if(path==='/api/places')data=demoPlaces
 else if(path==='/api/routes/public')data=[]
 else if(path==='/api/ai/config')data={enabled:true}
 else if(path==='/api/ai/plan'){requests++;lastPrompt=JSON.parse(options.body).prompt;assert.deepEqual(Object.keys(JSON.parse(options.body)),['prompt']);ok=!fail;data=fail?{detail:'AI jest chwilowo niedostępne.'}:plan}
 else if(path==='/api/routing'){routing=JSON.parse(options.body);data=plan}
 else throw Error('Unexpected '+path)
 return {ok,json:async()=>structuredClone(data)}
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async el=>{assert.ok(el);el.click();await settle()}
await settle();await click([...document.querySelectorAll('.main-navigation button')].find(el=>el.textContent==='Start'))
assert.equal(document.querySelector('.home-ai'),null)
assert.ok(document.querySelector('.hero-search input'))
assert.equal(document.querySelector('.ai-planner'),null)
const firstPrompt=document.querySelector('.hero-search input');firstPrompt.value='Zaplanuj dzień w Łagowie';firstPrompt.dispatchEvent(new Event('input',{bubbles:true}));await settle()
const submit=()=>document.querySelector('.hero-search').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))
submit();await settle();await settle();assert.match(document.querySelector('.ai-error[role=alert]').textContent,/niedostępne/)
assert.equal(document.querySelector('#ai-prompt'),null)
assert.equal(document.querySelector('.ai-examples'),null)
assert.equal(document.querySelector('.ai-planner form'),null)
assert.equal(document.querySelector('.ai-planner h2'),null)
fail=false;const retry=document.querySelector('.ai-retry');retry.click();retry.click();await settle();assert.equal(requests,2)
assert.equal(document.querySelector('.ai-proposal h3').textContent,plan.name)
assert.equal(document.querySelector('.ai-proposal h3 b'),null)
assert.match(document.querySelector('.ai-route-summary').textContent,/9 km po trasie/)
const share=document.querySelector('.ai-share>button')
assert.equal(share.textContent.trim(),'Wyślij trasę')
assert.equal(share.getAttribute('aria-expanded'),'false')
assert.equal(document.querySelector('.ai-share a'),null)
await click(share)
assert.equal(share.getAttribute('aria-expanded'),'true')
const sms=new URL(document.querySelector('.ai-share a[href^="sms:"]').href)
const email=new URL(document.querySelector('.ai-share a[href^="mailto:"]').href)
assert.equal(email.searchParams.get('subject'),plan.name)
assert.equal(sms.searchParams.get('body'),email.searchParams.get('body'))
assert.match(email.searchParams.get('body'),/9 km/)
assert.ok(points.every(p=>email.searchParams.get('body').includes(p.name)))
const maps=new URL(email.searchParams.get('body').split('\n').at(-1))
assert.equal(maps.origin,'https://www.google.com')
assert.equal(maps.searchParams.get('travelmode'),'walking')
assert.equal(maps.searchParams.get('origin'),'52.33,15.29')
assert.equal(maps.searchParams.get('waypoints'),'52.32,15.28')
assert.equal(requests,2,'Sharing prepares messages without another AI request or automatic sending')
await click(document.querySelector('.ai-use'))
assert.equal(document.querySelector('.ai-planner'),null)
assert.deepEqual([...document.querySelectorAll('.route-stop strong')].map(el=>el.textContent),points.map(p=>p.name))
assert.equal(document.querySelector('.planner-catalog'),null)
assert.equal(localStorage.getItem('perly-saved'),null,'Accepting a proposal does not save or publish it')
for(let i=0;i<40&&!routing;i++)await new Promise(r=>setTimeout(r,20))
assert.deepEqual(routing.place_ids,plan.place_ids)
assert.equal(routing.custom_points.length,3)
await click([...document.querySelectorAll('.main-navigation button')].find(el=>el.textContent==='Start'))
const hero=document.querySelector('.hero-search input')
hero.value='Zaplanuj dzień w Łagowie';hero.dispatchEvent(new Event('input',{bubbles:true}));await settle()
assert.equal(requests,2,'Typing in hero never calls AI before submit')
document.querySelector('.hero-search').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))
document.querySelector('.hero-search').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))
await settle();await settle()
assert.equal(requests,3,'Hero arrow/Enter automatically starts exactly one planning request')
assert.equal(lastPrompt,'Zaplanuj dzień w Łagowie')
assert.equal(document.querySelector('#ai-prompt'),null)
assert.ok(document.querySelector('.ai-proposal'))
await click(document.querySelector('[aria-label="Zamknij okno"]'))
assert.equal(requests,3,'Closing the preview does not resubmit the hero prompt')
assert.equal(document.querySelector('.ai-planner'),null)
app.unmount();dom.window.close()
console.log('PASS: Start AI badge/prompts, retry, duplicate request guard, escaped proposal, real route metrics and route-only points opened without saving/publishing')
