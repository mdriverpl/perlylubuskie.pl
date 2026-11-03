<script setup>
import {computed} from 'vue'
import Phone from 'lucide-vue-next/dist/esm/icons/phone.js'
import Mail from 'lucide-vue-next/dist/esm/icons/mail.js'
import Globe from 'lucide-vue-next/dist/esm/icons/globe.js'
import Bed from 'lucide-vue-next/dist/esm/icons/bed.js'
import Utensils from 'lucide-vue-next/dist/esm/icons/utensils.js'
const props=defineProps({contact:Object,lakeInfo:Object})
const lakeFacts=computed(()=>[{key:'swimming',label:'Kąpiel'},{key:'motorboats',label:'Motorówki'},{key:'beach',label:'Plaża'}].map(f=>({...f,...props.lakeInfo?.[f.key]})))
function safeSource(url){try{return new URL(url).protocol==='https:'}catch{return false}}
const services=computed(()=>[
 {key:'accommodation',label:'Nocleg',icon:Bed},
 {key:'restaurant',label:'Restauracja',icon:Utensils},
].map(s=>({...s,...props.contact?.[s.key]})))
const links=computed(()=>[
 {key:'phone',label:'Telefon',icon:Phone,href:v=>'tel:'+v.replace(/[^+\d]/g,'')},
 {key:'email',label:'E-mail',icon:Mail,href:v=>'mailto:'+v},
 {key:'website',label:'Strona WWW',icon:Globe,href:v=>v},
].map(s=>({...s,...props.contact?.[s.key]})).filter(s=>s.value))
const date=computed(()=>props.contact?.checked_at?new Date(props.contact.checked_at).toLocaleDateString('pl-PL'):'')
</script>

<template>
 <section v-if="contact" class="place-contact" aria-label="Usługi i kontakt">
  <h3>Usługi i kontakt</h3>
  <div class="place-services"><div v-for="service in services" :key="service.key" class="place-service"><component :is="service.icon" :size="18"/><span>{{service.label}}<small>{{service.value===true?'Dostępny':service.value===false?'Brak usługi':'Brak potwierdzonych informacji'}}</small></span></div></div>
  <a v-for="link in links" :key="link.key" class="place-contact-link" :href="link.href(link.value)" :target="link.key==='website'?'_blank':undefined" rel="noopener noreferrer"><component :is="link.icon" :size="18"/><span><small>{{link.label}}</small>{{link.value}}</span></a>
  <p v-if="!links.length" class="contact-note">Nie znaleziono potwierdzonych danych kontaktowych.</p>
  <p class="contact-note">Sprawdzono: {{date}}. Aktualną dostępność potwierdź w obiekcie.</p>
 </section>
 <section v-if="lakeInfo" class="place-contact lake-info" aria-label="Informacje o jeziorze">
  <h3>Informacje o jeziorze</h3>
  <div v-for="fact in lakeFacts" :key="fact.key" class="lake-fact"><strong>{{fact.label}}</strong><span>{{fact.status==='yes'?'Tak':fact.status==='no'?'Nie':'Brak potwierdzonych informacji'}}</span><p v-if="fact.explanation" class="contact-note">{{fact.explanation}}</p><a v-if="safeSource(fact.source_url)" :href="fact.source_url" target="_blank" rel="noopener noreferrer">Źródło informacji</a><small v-if="fact.checked_at">Sprawdzono: {{new Date(fact.checked_at).toLocaleDateString('pl-PL')}}</small></div>
 </section>
</template>

<style scoped>
.lake-fact{display:flex;flex-direction:column;gap:5px;padding:12px 0;border-bottom:1px solid #e3eadd;font-size:13px}.lake-fact:last-child{border-bottom:0;padding-bottom:0}.lake-fact .contact-note{margin:0}.lake-fact a{font-size:12px;color:#176e4f}.place-contact{margin:20px 0;padding:16px;border:1px solid #dce5d4;border-radius:12px}.place-contact h3{font-size:17px;margin:0 0 14px}.place-services{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}.place-service,.place-contact-link{display:flex;align-items:flex-start;gap:9px}.place-service svg,.place-contact-link svg{flex-shrink:0;margin-top:3px;color:#18734f}.place-contact small{display:block;color:#718369;font-size:12px;line-height:1.5}.place-contact-link{padding:8px 0;color:#176e4f;text-decoration:none;overflow-wrap:anywhere}.place-contact-link span{min-width:0}.contact-note{font-size:12px;color:#718369;line-height:1.6;margin:10px 0 0}
@media(max-width:380px){.place-services{grid-template-columns:1fr}}
</style>
