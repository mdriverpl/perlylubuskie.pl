import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
function pwa(){return {name:'perly-pwa',apply:'build',generateBundle:{order:'post',handler(options,bundle){
 const files=Object.keys(bundle).filter(name=>name==='index.html'||/\.(js|css)$/.test(name)).map(name=>'/'+name)
 const precache=[...files,'/manifest.webmanifest','/icons/icon-192.png','/icons/icon-512.png','/icons/icon-maskable.png','/icons/apple-touch-icon.png','/images/heritage-placeholder.svg','/images/winery-placeholder.svg']
 const template=readFileSync(new URL('./src/service-worker.js',import.meta.url),'utf8')
 const version=createHash('sha256').update(template+JSON.stringify(bundle['index.html']?.source)+files.join('|')).digest('hex').slice(0,14)
 this.emitFile({type:'asset',fileName:'sw.js',source:template.replace('__VERSION__',version).replace('__PRECACHE__',JSON.stringify(precache))})
}}}}
export default defineConfig({ plugins: [vue(),pwa()], optimizeDeps: { noDiscovery: true, include: [] }, server: { watch: { ignored: ['**/artifacts/**', '**/.tools/**', '**/.pg-test/**', '**/.pg-data/**'] }, proxy: { '/api': 'http://127.0.0.1:8000' } }, preview: { proxy: { '/api': 'http://127.0.0.1:8000' } } })
