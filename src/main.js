import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
import 'leaflet/dist/leaflet.css'
import {registerPwa} from './pwa.js'
createApp(App).mount('#app')
registerPwa()
