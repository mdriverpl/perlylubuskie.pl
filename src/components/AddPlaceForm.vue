<script setup>
import {ref} from 'vue'
defineProps({busy:Boolean,error:String})
const emit=defineEmits(['submit'])
const draft=ref({name:'',subtitle:'',location:'',description:'',place_type:'heritage',lat:null,lng:null,image:''})
const types=[['castle','Zamek'],['palace','Pałac'],['vineyard','Winnica'],['food','Restauracja'],['lake','Jezioro'],['nature','Park lub przyroda'],['heritage','Zabytek'],['stay','Nocleg'],['leisure','Atrakcja rodzinna']]
</script>
<template>
 <form class="add-place-form modal-body" @submit.prevent="emit('submit',{...draft})">
  <div class="section-kicker">KATALOG MIEJSC</div><h2>Dodaj miejsce</h2>
  <p>Miejsce pojawi się we wspólnym katalogu. Inni będą mogli je polubić i skomentować.</p>
  <label>Nazwa<input id="new-place-name" v-model="draft.name" required maxlength="200" autocomplete="off"></label>
  <label>Rodzaj<select id="new-place-type" v-model="draft.place_type"><option v-for="[id,name] in types" :key="id" :value="id">{{name}}</option></select></label>
  <label>Miejscowość<input id="new-place-location" v-model="draft.location" required maxlength="200"></label>
  <label>Krótki opis<input id="new-place-subtitle" v-model="draft.subtitle" maxlength="250"></label>
  <label>Opis<textarea id="new-place-description" v-model="draft.description" required maxlength="2000" rows="4"></textarea></label>
  <div class="place-coordinate-fields"><label>Szerokość geograficzna<input id="new-place-lat" v-model.number="draft.lat" required type="number" step="any" min="-90" max="90" placeholder="np. 51.95"></label><label>Długość geograficzna<input id="new-place-lng" v-model.number="draft.lng" required type="number" step="any" min="-180" max="180" placeholder="np. 15.70"></label></div>
  <label>Link do zdjęcia (opcjonalnie)<input id="new-place-image" v-model="draft.image" type="url" pattern="https://.*" maxlength="2000" placeholder="https://…"></label>
  <p v-if="error" class="form-error" role="alert">{{error}}</p>
  <button class="button full-width" type="submit" :disabled="busy||!draft.name.trim()||!draft.location.trim()||!draft.description.trim()||!Number.isFinite(draft.lat)||!Number.isFinite(draft.lng)">{{busy?'Zapisuję…':'Dodaj miejsce'}}</button>
 </form>
</template>
<style scoped>
.add-place-form label{display:block;font-size:12px;font-weight:600;margin:16px 0}.add-place-form select{display:block;width:100%;margin-top:8px;padding:12px;border:1px solid #d5e2cb;background:white;border-radius:7px;font:inherit}.add-place-form textarea{width:100%;padding:12px;margin-top:8px;border:1px solid #d5e2cb;border-radius:7px;font:inherit;resize:vertical}.place-coordinate-fields{display:grid;grid-template-columns:1fr 1fr;gap:14px}.place-coordinate-fields label{min-width:0}.add-place-form .form-error{color:#a0442c}@media(max-width:480px){.place-coordinate-fields{grid-template-columns:1fr;gap:0}}
</style>
