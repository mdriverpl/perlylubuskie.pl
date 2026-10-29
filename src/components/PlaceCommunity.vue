<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import Check from 'lucide-vue-next/dist/esm/icons/check.js'
import MessageCircle from 'lucide-vue-next/dist/esm/icons/message-circle.js'
import Users from 'lucide-vue-next/dist/esm/icons/users.js'
const props=defineProps({place:{type:Object,required:true},user:Object,token:String,online:Boolean})
const emit=defineEmits(['login','notify'])
const community=ref(null),loading=ref(false),loadingMore=ref(false),visitBusy=ref(false),commentBusy=ref(false),error=ref(''),actionError=ref(''),draft=ref(''),nextOffset=ref(0)
let generation=0,controller,disposed=false
const comments=computed(()=>community.value?.comments||[])
async function request(path,options={}) {
 const response=await fetch(path,{signal:AbortSignal.timeout(12000),...options,headers:{'Content-Type':'application/json',...(props.token?{Authorization:`Bearer ${props.token}`} :{}),...options.headers}})
 if(!response.ok){let message='Nie udało się zapisać zmiany. Spróbuj ponownie.';try{const data=await response.json();if(typeof data.detail==='string')message=data.detail}catch{}throw new Error(message)}
 return response.status===204?null:response.json()
}
async function load(more=false) {
 if(!props.online)return
 controller?.abort();controller=new AbortController();const version=++generation
 error.value='';more?loadingMore.value=true:loading.value=true
 try {
  const offset=more?nextOffset.value:0
  const data=await request(`/api/places/${props.place.id}/community?offset=${offset}&limit=20`,{signal:AbortSignal.any([controller.signal,AbortSignal.timeout(12000)])})
  if(version!==generation)return
  nextOffset.value=offset+data.comments.length
  if(more&&community.value){const unique=new Map([...community.value.comments,...data.comments].map(c=>[c.id,c]));data.comments=[...unique.values()]}
  community.value=data
 }catch(e){if(version===generation&&e.name!=='AbortError')error.value='Nie udało się pobrać komentarzy i odwiedzin. Spróbuj ponownie.'}
 finally{if(version===generation){loading.value=false;loadingMore.value=false}}
}
watch(()=>[props.place.id,props.user?.id,props.token,props.online],()=>{generation++;controller?.abort();community.value=null;draft.value='';actionError.value='';error.value='';loading.value=false;loadingMore.value=false;load()},{immediate:true})
onBeforeUnmount(()=>{disposed=true;generation++;controller?.abort()})
async function toggleVisit(){
 if(!props.user){emit('login');return}
 if(!community.value||visitBusy.value)return
 const placeId=props.place.id;visitBusy.value=true;actionError.value=''
 try{await request(`/api/places/${placeId}/visit`,{method:community.value.visited?'DELETE':'PUT'});if(!disposed&&props.place.id===placeId)await load()}
 catch(e){if(props.place.id===placeId)actionError.value=e.message}
 finally{visitBusy.value=false}
}
async function addComment(){
 if(!props.user){emit('login');return}
 if(!draft.value.trim()||commentBusy.value)return
 const placeId=props.place.id;commentBusy.value=true;actionError.value=''
 try{await request(`/api/places/${placeId}/comments`,{method:'POST',body:JSON.stringify({body:draft.value.trim()})});if(!disposed&&props.place.id===placeId){draft.value='';emit('notify','Komentarz został dodany.');await load()}}
 catch(e){if(props.place.id===placeId)actionError.value=e.message}
 finally{commentBusy.value=false}
}
async function deleteComment(id){
 if(commentBusy.value)return
 const placeId=props.place.id;commentBusy.value=true;actionError.value=''
 try{await request(`/api/places/${placeId}/comments/${id}`,{method:'DELETE'});if(!disposed&&props.place.id===placeId){emit('notify','Twój komentarz został usunięty.');await load()}}
 catch(e){if(props.place.id===placeId)actionError.value=e.message}
 finally{commentBusy.value=false}
}
function formatDate(value){const date=new Date(value);return Number.isNaN(date.getTime())?'':new Intl.DateTimeFormat('pl-PL',{dateStyle:'medium',timeStyle:'short'}).format(date)}
</script>

<template>
 <section class="place-community" aria-label="Odwiedziny i komentarze" :aria-busy="loading">
  <div class="visit-summary"><div class="visit-total"><Users :size="23"/><span><strong>{{loading&&!community?'…':community?.visit_count??'—'}}</strong><small>Liczba odwiedzających</small></span></div><button :class="['visit-button',{visited:community?.visited}]" :disabled="!online||loading||visitBusy||!community" :aria-pressed="!!community?.visited" @click="toggleVisit"><Check :size="17"/>{{visitBusy?'Zapisuję…':community?.visited?'Byłem tu ✓':'Byłem tu'}}</button></div>
  <p v-if="community?.visited" class="visit-hint">Twoja wizyta jest zapisana. Kliknij ponownie, aby cofnąć oznaczenie.</p>
  <div class="comments-heading"><h3><MessageCircle :size="18"/>Komentarze <span v-if="community">{{community.comment_count}}</span></h3></div>
  <p v-if="!online" class="community-notice">Komentarze i odwiedziny są dostępne po połączeniu z serwerem.</p>
  <p v-else-if="loading&&!community" class="community-notice" role="status">Wczytuję komentarze i odwiedziny…</p>
  <p v-if="error" class="community-error" role="alert">{{error}} <button :disabled="loading" @click="load()">Ponów próbę</button></p>
  <template v-if="online">
   <form v-if="user" class="comment-form" @submit.prevent="addComment"><label :for="`comment-${place.id}`">Podziel się wrażeniami</label><textarea :id="`comment-${place.id}`" v-model="draft" rows="3" maxlength="2000" required placeholder="Co warto wiedzieć przed odwiedzinami?" :disabled="commentBusy"></textarea><div class="comment-form-bottom"><small>{{draft.length}} / 2000</small><button class="button" :disabled="!draft.trim()||commentBusy">{{commentBusy?'Zapisuję…':'Dodaj komentarz'}}</button></div></form>
   <div v-else class="community-login"><p>Byłeś tu? Zaloguj się, aby oznaczyć wizytę i dodać komentarz.</p><button class="text-link" @click="emit('login')">Zaloguj się lub załóż konto →</button></div>
  </template>
  <p v-if="actionError" class="community-error" role="alert">{{actionError}}</p>
  <p v-if="community&&!comments.length" class="comments-empty">To miejsce czeka na pierwszą opinię. Podziel się swoim odkryciem.</p>
  <div class="comments-list"><article v-for="comment in comments" :key="comment.id" class="place-comment"><div class="comment-avatar" aria-hidden="true">{{[...comment.author.trim()][0]?.toUpperCase()||'•'}}</div><div class="comment-content"><div class="comment-meta"><strong>{{comment.author}}</strong><time :datetime="comment.created_at">{{formatDate(comment.created_at)}}</time></div><p class="comment-body">{{comment.body}}</p><button v-if="comment.can_delete" class="delete-comment" :disabled="commentBusy" @click="deleteComment(comment.id)" aria-label="Usuń swój komentarz">Usuń swój komentarz</button></div></article></div>
  <button v-if="community&&nextOffset<community.comment_count" class="text-link more-comments" :disabled="loadingMore||loading" @click="load(true)">{{loadingMore?'Wczytuję…':'Pokaż starsze komentarze'}}</button>
 </section>
</template>

<style scoped>
.place-community{border-top:1px solid #e3e9dc;margin-top:27px;padding-top:24px}.visit-summary{display:flex;align-items:center;justify-content:space-between;gap:15px}.visit-total{display:flex;align-items:center;gap:12px;color:#19744f}.visit-total span{display:flex;flex-direction:column;gap:3px}.visit-total strong{font-family:Manrope,sans-serif;font-size:25px;line-height:1.2}.visit-total small{font-size:10px;color:#7c8876}.visit-button{border:1px solid #cddbc5;border-radius:8px;padding:11px 16px;font-size:12px;font-weight:600;display:flex;align-items:center;gap:7px;color:#19744f;background:#f1f6ec}.visit-button.visited{background:#19744f;color:white;border-color:#19744f}.place-community .visit-hint{font-size:10px;line-height:1.6;margin:12px 0 0}.comments-heading{margin:27px 0 16px}.comments-heading h3{display:flex;align-items:center;gap:8px;font-size:17px;letter-spacing:-.5px}.comments-heading h3 span{background:#edf3e6;color:#19744f;border-radius:20px;padding:3px 8px;font-size:10px}.place-community .community-notice,.place-community .comments-empty{font-size:12px;line-height:1.8;margin:14px 0;color:#829077}.community-login{background:#f0f4e9;padding:15px;border-radius:9px;margin-bottom:18px}.place-community .community-login p{font-size:11px;line-height:1.7;margin:0 0 5px}.community-login .text-link{font-size:11px}.comment-form{margin-bottom:22px}.comment-form label{margin:0 0 8px;font-size:12px;font-weight:600}.comment-form textarea{display:block;width:100%;resize:vertical;min-height:90px;max-height:260px;border:1px solid #d5dfcc;border-radius:9px;background:white;padding:12px;font:inherit;font-size:12px;color:#172b2b;line-height:1.7}.comment-form textarea:focus{outline:2px solid #81ac8a;outline-offset:2px}.comment-form-bottom{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:10px}.comment-form-bottom small{font-size:9px;color:#84927a}.comment-form-bottom .button{padding:10px 14px;font-size:11px}.place-comment{display:flex;gap:11px;border-top:1px solid #e8edde;padding:18px 0}.comment-avatar{width:30px;height:30px;border-radius:50%;background:#e8f0e0;color:#4e7546;font-size:12px;font-weight:700;display:grid;place-items:center;flex-shrink:0}.comment-content{min-width:0;flex:1}.comment-meta{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap}.comment-meta strong{font-size:12px;overflow-wrap:anywhere}.comment-meta time{font-size:9px;color:#8b9585}.place-community .comment-body{font-size:12px;line-height:1.8;white-space:pre-wrap;overflow-wrap:anywhere;margin:8px 0 0;color:#5b6856}.delete-comment{color:#8c6a51;font-size:9px;text-decoration:underline;padding:0;margin-top:9px}.place-community .community-error{font-size:11px;line-height:1.7;color:#a64d37;margin:13px 0}.community-error button{color:#19744f;text-decoration:underline;padding:0;font-size:inherit}.more-comments{margin:auto;font-size:11px}
@media(max-width:480px){.visit-button{padding:10px 12px}.visit-total{gap:8px}.visit-total small{font-size:9px}.comment-meta{gap:4px}.comment-meta time{width:100%}}
</style>
