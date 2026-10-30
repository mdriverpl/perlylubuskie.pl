import { places as catalogPlaces } from '../src/data.js'
// Link the actual Vite-served ES module graph to catch missing browser exports.
// Does not execute browser code or substitute for visual QA.
import vm from 'node:vm'
import assert from 'node:assert/strict'
import { JSDOM } from 'jsdom'
const origin=process.env.DEV_ORIGIN || 'http://127.0.0.1:5173'
const dom=new JSDOM('<!doctype html><div id="app"></div>',{url:origin,runScripts:'outside-only',pretendToBeVisual:true})
const context=dom.getInternalVMContext()
dom.window.fetch=(path,options)=>fetch(new URL(path,origin),options)
dom.window.AbortSignal=AbortSignal
dom.window.scrollTo=()=>{}
const modules=new Map()
function load(url){
 if(!modules.has(url)) modules.set(url,(async()=>{
  if(new URL(url).pathname==='/@vite/client') return new vm.SourceTextModule('export const createHotContext=()=>({on(){},accept(){},dispose(){},invalidate(){},send(){},prune(){},data:{}}); export const updateStyle=()=>{}; export const removeStyle=()=>{}; export const injectQuery=(url)=>url;',{identifier:url,context})
  const response=await fetch(url,{signal:AbortSignal.timeout(15000)})
  if(!response.ok)throw new Error(`${response.status}: ${url}`)
  const source=await response.text()
  return new vm.SourceTextModule(source,{identifier:url,context})
 })())
 return modules.get(url)
}
const entry=await load(`${origin}/src/main.js`)
await entry.link((specifier,parent)=>load(new URL(specifier,parent.identifier).href))
console.log(`PASS: ${modules.size} Vite-served modules link without missing imports/exports`)
try {
 await entry.evaluate()
 assert.match(dom.window.document.querySelector('h1')?.textContent || '',/Czego szukam/)
 assert.ok(dom.window.document.querySelector('.leaflet-container'))
 assert.equal(dom.window.document.querySelector('[aria-label="Widok mapy"]').getAttribute('aria-pressed'),'true')
 console.log('PASS: actual Vite entry mounts the homepage in map view')
} finally { dom.window.close() }
