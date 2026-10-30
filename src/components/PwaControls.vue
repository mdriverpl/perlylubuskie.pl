<script setup>
import {ref,shallowRef,onMounted,onBeforeUnmount} from 'vue'
import Download from 'lucide-vue-next/dist/esm/icons/download.js'
const installPrompt=shallowRef(null),update=shallowRef(null),hint=ref(''),offline=ref(navigator.onLine===false),installed=ref(false)
function beforeInstall(event){event.preventDefault();installPrompt.value=event}
function appInstalled(){installed.value=true;installPrompt.value=null;hint.value=''}
function connection(){offline.value=navigator.onLine===false}
function available(event){update.value=event.detail}
function failed(){hint.value='Nie udało się przygotować trybu offline. Spróbuj ponownie po odświeżeniu.'}
async function install(){
 if(installPrompt.value){try{const prompt=installPrompt.value;installPrompt.value=null;await prompt.prompt();const choice=await prompt.userChoice;if(choice.outcome==='accepted')appInstalled()}catch{hint.value='Instalacja jest teraz niedostępna. Spróbuj ponownie z menu przeglądarki.'}}
 else hint.value=/iPad|iPhone|iPod/.test(navigator.userAgent)?'Aby zainstalować: otwórz menu Udostępnij i wybierz „Do ekranu początkowego”.':'W menu przeglądarki wybierz „Zainstaluj aplikację” lub „Dodaj do ekranu głównego”.'
}
function applyUpdate(){navigator.serviceWorker.addEventListener('controllerchange',()=>window.location.reload(),{once:true});update.value?.waiting?.postMessage({type:'SKIP_WAITING'})}
const listeners=[['beforeinstallprompt',beforeInstall],['appinstalled',appInstalled],['online',connection],['offline',connection],['perly:pwa-update',available],['perly:pwa-error',failed]]
onMounted(()=>{installed.value=window.matchMedia?.('(display-mode: standalone)').matches||navigator.standalone===true;for(const [event,handler] of listeners)window.addEventListener(event,handler)})
onBeforeUnmount(()=>{for(const [event,handler] of listeners)window.removeEventListener(event,handler)})
</script>
<template>
 <div class="pwa-controls">
  <button v-if="!installed" class="pwa-install" aria-label="Zainstaluj aplikację" title="Zainstaluj aplikację" @click="install"><Download :size="21"/></button>
  <div v-if="hint||offline||update" class="pwa-messages">
  <p v-if="hint" role="status">{{hint}} <button @click="hint=''" aria-label="Zamknij wskazówkę instalacji">×</button></p>
  <p v-if="offline" role="status">Tryb offline · katalog i lokalne plany są dostępne. Mapy i wyznaczanie tras wymagają internetu.</p>
  <p v-if="update" role="status">Dostępna nowa wersja. <button class="pwa-update" @click="applyUpdate">Odśwież aplikację</button></p>
  </div>
 </div>
</template>
<style scoped>
.pwa-controls{display:flex;flex-wrap:wrap;align-items:center;gap:10px}.pwa-install,.pwa-update{font-size:11px;color:#19744f;border:1px solid #cddfc3;border-radius:7px;background:#f4f8ef;padding:9px 12px;white-space:nowrap}.pwa-controls p{font-size:11px;color:#687e5f;line-height:1.7;max-width:650px}.pwa-controls p>button:not(.pwa-update){padding:0 6px}
.pwa-controls .pwa-install{display:grid;place-items:center;padding:6px;border:0;background:transparent}.pwa-messages{position:fixed;top:90px;right:16px;max-width:calc(100vw - 32px);width:400px;z-index:1100;background:#fcfcf9;border:1px solid #d4e1cb;border-radius:10px;box-shadow:0 6px 25px #173c2b20;padding:12px 15px}.pwa-messages p+p{margin-top:10px}
</style>
