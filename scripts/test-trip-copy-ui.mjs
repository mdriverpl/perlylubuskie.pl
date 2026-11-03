import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import {demoPlaces} from '../src/data.js'
const dom=new JSDOM('<div id="app"></div>',{url:'https://localhost/wycieczki',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
globalThis.requestAnimationFrame=window.requestAnimationFrame.bind(window);globalThis.getComputedStyle=window.getComputedStyle.bind(window)
window.scrollTo=()=>{};Element.prototype.scrollIntoView=()=>{}
localStorage.setItem('perly-user',JSON.stringify({id:1,name:'Tester'}));localStorage.setItem('perly-token','test-token')
const original={id:202,name:'Cudza publiczna',description:'Opis autora',transport:'bike',place_ids:[1,5],point_positions:[{id:1,lat:52.33,lng:15.29}],is_public:true,custom_points:[]}
const custom={id:203,name:'Cudza z punktem',description:'Start zapisany przez autora',transport:'bike',place_ids:[-9,5],point_positions:[],is_public:true,custom_points:[{id:-9,name:'Punkt autora',lat:52.34,lng:15.3}]}
const sourceSnapshot=JSON.stringify([original,custom]),own=[],posts=[],updates=[]
globalThis.fetch=async(path,options={})=>{
 let data=[]
 if(path==='/api/places')data=demoPlaces
 else if(path==='/api/routes/public')data=[original,custom]
 else if(path==='/api/routes'&&options.method==='POST'){const body=JSON.parse(options.body);posts.push(body);const created={...body,id:303+own.length};own.push(created);data=created}
 else if(path==='/api/routes')data=own
 else if(path.startsWith('/api/routes/')&&options.method==='PUT'){
  const id=Number(path.split('/').at(-1));assert.ok(id>=303,'The original author route can never be updated')
  const body=JSON.parse(options.body);updates.push({id,...body});Object.assign(own.find(r=>r.id===id),body);data=own.find(r=>r.id===id)
 }
 else if(path==='/api/routing')data={geometry:{type:'LineString',coordinates:[[15.29,52.33],[15.3,52.34]]},distance_m:3000,duration_s:1000}
 return {ok:true,json:async()=>structuredClone(data)}
}
const {createApp,nextTick}=await import('vue')
const App=(await import('../artifacts/ui-test.mjs')).default
const app=createApp(App);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
const click=async el=>{assert.ok(el);el.click();await settle();await settle()}
const card=name=>[...document.querySelectorAll('.route-library-item')].find(el=>el.querySelector('.route-library-info>strong').textContent===name)
await settle();await settle()
assert.equal(card(original.name).querySelector('.route-library-edit'),null,'Only own trips offer Edit')
assert.equal(card(original.name).querySelector('.route-library-delete'),null)
await click(card(original.name).querySelector('.route-library-copy'))
assert.equal(posts.length,1)
assert.equal(posts[0].is_public,false,'Copies start private even when the source is public')
assert.deepEqual(posts[0].point_positions,original.point_positions)
assert.equal(window.location.pathname,'/planer')
assert.ok(document.querySelector('.explore-home'))
assert.equal(document.querySelector('.planner-catalog'),null)
assert.equal(document.querySelectorAll('.planned-stop').length,2)
assert.ok(document.querySelector('.test-drag-point'),'The copy is editable by its new owner')
assert.match(document.querySelector('.planned-places-panel>.button').textContent,/Zapisz zmiany/)
await click(document.querySelector('.test-drag-point'))
await click(document.querySelector('.planned-places-panel>.button'))
const name=document.querySelector('.modal input');name.value='Moja edytowana kopia';name.dispatchEvent(new Event('input',{bubbles:true}));await settle()
await click(document.querySelector('.modal-body>button.full-width'))
assert.equal(updates.length,1);assert.equal(updates[0].id,303)
assert.equal(own.length,1,'Saving changes updates the copy instead of making another trip')
assert.equal(own[0].name,'Moja edytowana kopia')
assert.equal(JSON.stringify([original,custom]),sourceSnapshot,'Copying and editing leave the author records untouched')
await click(card(custom.name).querySelector('.route-library-copy'))
const local=JSON.parse(localStorage.getItem('perly-saved'))
assert.equal(local.length,1)
assert.equal(local[0].is_public,false)
assert.equal(local[0].owner_id,1)
assert.deepEqual(local[0].custom_points,custom.custom_points,'Custom start points retain their own snapshot')
assert.equal(document.querySelector('.planned-open strong').textContent,'Punkt autora')
assert.equal(JSON.stringify([original,custom]),sourceSnapshot)
app.unmount();dom.window.close()
console.log('PASS: owner-only editing in the map planner, private copies, source protection, same-copy updates and custom-point snapshots')
