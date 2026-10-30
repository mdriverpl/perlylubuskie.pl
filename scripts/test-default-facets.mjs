import assert from 'node:assert/strict'
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import {parse,compileScript} from '@vue/compiler-sfc'
import {JSDOM} from 'jsdom'
import {placeFacets,defaultPlaceFacets} from '../src/explore.js'
import {places} from '../src/data.js'
assert.deepEqual(placeFacets.slice(-3).map(f=>f.name),['Noclegi','Winiarnie','Restauracje'])
assert.deepEqual(defaultPlaceFacets,['castles','palaces','family','lakes','nature','history'])
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event','localStorage'])globalThis[key]=dom.window[key]
const {createApp,nextTick}=await import('vue')
const descriptor=parse(await readFile('src/components/ExploreHome.vue','utf8')).descriptor
const compiled=compileScript(descriptor,{id:'default-facets',inlineTemplate:true}).content.replace("from '../explore.js'","from '../src/explore.js'").replace("from '../useGeolocation.js'","from '../src/useGeolocation.js'").replace("from '../useLocationSearch.js'","from '../src/useLocationSearch.js'").replace("import TravelMap from './TravelMap.vue'","const TravelMap={props:['places'],template:'<div />'}")
await mkdir('artifacts',{recursive:true});await writeFile('artifacts/default-facets-test.mjs',compiled)
const Component=(await import('../artifacts/default-facets-test.mjs')).default
for(const catalogOnly of [false,true]){
 const app=createApp(Component,{catalogOnly,places,online:true});app.mount('#app');await nextTick()
 const inputs=[...document.querySelectorAll('.facet-list input')]
 assert.deepEqual(inputs.filter(i=>i.checked).map(i=>i.value),defaultPlaceFacets)
 assert.deepEqual(inputs.slice(-3).map(i=>i.value),['stays','wineries','restaurants'])
 if(catalogOnly){
  assert.ok(document.querySelectorAll('.explore-place').length>0)
  assert.ok(![...document.querySelectorAll('.place-title')].some(e=>e.textContent==='Laura Spa'))
  document.querySelector('input[value="stays"]').click();await nextTick()
  assert.ok([...document.querySelectorAll('.place-title')].some(e=>e.textContent==='Laura Spa'))
 }
 app.unmount()
}
dom.window.close()
console.log('PASS: category order, six default checked categories, lodging/wineries/food unchecked, manual lodging selection in catalog and planner')
