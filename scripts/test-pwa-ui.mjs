import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
const dom=new JSDOM('<div id="app"></div>',{url:'http://localhost/planer',pretendToBeVisual:true})
for(const key of ['window','document','Document','ShadowRoot','Element','HTMLElement','SVGElement','Node','Event'])globalThis[key]=dom.window[key]
Object.defineProperty(globalThis,'navigator',{value:window.navigator,configurable:true})
let online=true,installCalls=0,message
Object.defineProperty(navigator,'onLine',{get:()=>online,configurable:true})
Object.defineProperty(navigator,'serviceWorker',{value:new window.EventTarget(),configurable:true})
const {createApp,nextTick}=await import('vue')
const Component=(await import('../artifacts/pwa-test.mjs')).default
const app=createApp(Component);app.mount('#app')
const settle=async()=>{await nextTick();await new Promise(r=>setTimeout(r,0));await nextTick()}
await settle()
document.querySelector('.pwa-install').click();await settle()
assert.match(document.querySelector('.pwa-messages').textContent,/menu przeglądarki/)
document.querySelector('[aria-label="Zamknij wskazówkę instalacji"]').click();await settle()
const prompt=new Event('beforeinstallprompt',{cancelable:true})
prompt.prompt=async()=>installCalls++;prompt.userChoice=Promise.resolve({outcome:'accepted'})
window.dispatchEvent(prompt);assert.equal(prompt.defaultPrevented,true)
document.querySelector('.pwa-install').click();await settle()
assert.equal(installCalls,1);assert.equal(document.querySelector('.pwa-install'),null)
online=false;window.dispatchEvent(new Event('offline'));await settle()
assert.match(document.querySelector('.pwa-messages').textContent,/Tryb offline/)
online=true;window.dispatchEvent(new Event('online'));await settle()
assert.equal(document.querySelector('.pwa-messages'),null)
window.dispatchEvent(new window.CustomEvent('perly:pwa-update',{detail:{waiting:{postMessage:data=>message=data}}}));await settle()
document.querySelector('.pwa-update').click();assert.deepEqual(message,{type:'SKIP_WAITING'})
app.unmount();dom.window.close()
console.log('PASS: install prompt/instructions, installed state, offline banner and user-triggered PWA update')
