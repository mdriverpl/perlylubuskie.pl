<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import Check from 'lucide-vue-next/dist/esm/icons/check.js'
import MessageCircle from 'lucide-vue-next/dist/esm/icons/message-circle.js'
import ThumbsUp from 'lucide-vue-next/dist/esm/icons/thumbs-up.js'
import Heart from 'lucide-vue-next/dist/esm/icons/heart.js'
const props=defineProps({place:{type:Object,required:true},user:Object,token:String,online:Boolean,favorite:Boolean})
const emit=defineEmits(['login','notify','updated','favorite'])
const likeBusy=ref(false)
const commentsOpen=ref(false)
watch(()=>props.place.id,()=>{commentsOpen.value=false})
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
  emit('updated',{id:props.place.id,like_count:data.like_count??0,comment_count:data.comment_count??0,popularity:(data.like_count??0)+(data.comment_count??0),liked:!!data.liked})
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
async function toggleLike(){
 if(!props.user){emit('login');return}
 if(!community.value||likeBusy.value)return
 const placeId=props.place.id;likeBusy.value=true;actionError.value=''
 try{await request(`/api/places/${placeId}/like`,{method:community.value.liked?'DELETE':'PUT'});if(!disposed&&props.place.id===placeId)await load()}
 catch(e){if(props.place.id===placeId)actionError.value=e.message}
 finally{likeBusy.value=false}
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
 <section class="place-community" aria-label="Polubienia, odwiedziny i komentarze" :aria-busy="loading">
  <div class="community-action-row" role="group" aria-label="Aktywność miejsca">
   <button class="place-like-button" :class="{liked:community?.liked}" :aria-pressed="!!community?.liked" :disabled="!online||loading||likeBusy||!community" title="Publiczne polubienia — jedno na konto" @click="toggleLike"><ThumbsUp :size="17"/><span>{{likeBusy?'Zapisuję…':community?.liked?'Lubisz to':'Lubię to'}}</span><strong>{{loading&&!community?'…':community?.like_count??'—'}}</strong></button>
   <button :class="['visit-button',{visited:community?.visited}]" :disabled="!online||loading||visitBusy||!community" :aria-pressed="!!community?.visited" title="Oznacz lub cofnij wizytę. Licznik pokazuje odwiedzające konta." @click="toggleVisit"><Check :size="17"/><span>{{visitBusy?'Zapisuję…':'Byłem tu'}}</span><strong>{{loading&&!community?'…':community?.visit_count??'—'}}</strong></button>
   <button class="comments-toggle" :aria-expanded="commentsOpen" :aria-controls="`place-comments-${place.id}`" @click="commentsOpen=!commentsOpen"><MessageCircle :size="17"/><span>Komentarze</span><strong>{{community?.comment_count??'—'}}</strong></button>
   <button class="community-favorite" :class="{saved:favorite}" :aria-pressed="favorite" :aria-label="favorite?'Usuń miejsce z ulubionych':'Dodaj miejsce do ulubionych'" title="Twoje prywatne ulubione" @click="emit('favorite')"><Heart :size="17" :fill="favorite?'currentColor':'none'"/><span>Ulubione</span></button>
  </div>
  <p v-if="!online" class="community-notice">Komentarze i odwiedziny są dostępne po połączeniu z serwerem.</p>
  <p v-else-if="loading&&!community" class="community-notice" role="status">Wczytuję komentarze i odwiedziny…</p>
  <p v-if="error" class="community-error" role="alert">{{error}} <button :disabled="loading" @click="load()">Ponów próbę</button></p>
  <p v-if="actionError" class="community-error" role="alert">{{actionError}}</p>
  <div v-if="commentsOpen" :id="`place-comments-${place.id}`" class="comments-panel" role="region" aria-label="Komentarze do miejsca">
  <template v-if="online">
   <form v-if="user" class="comment-form" @submit.prevent="addComment"><label :for="`comment-${place.id}`">Podziel się wrażeniami</label><textarea :id="`comment-${place.id}`" v-model="draft" rows="3" maxlength="2000" required placeholder="Co warto wiedzieć przed odwiedzinami?" :disabled="commentBusy"></textarea><div class="comment-form-bottom"><small>{{draft.length}} / 2000</small><button class="button" :disabled="!draft.trim()||commentBusy">{{commentBusy?'Zapisuję…':'Dodaj komentarz'}}</button></div></form>
   <div v-else class="community-login"><p>Byłeś tu? Zaloguj się, aby polubić miejsce, oznaczyć wizytę i dodać komentarz.</p><button class="text-link" @click="emit('login')">Zaloguj się lub załóż konto →</button></div>
  </template>

  <p v-if="community&&!comments.length" class="comments-empty">To miejsce czeka na pierwszą opinię. Podziel się swoim odkryciem.</p>
  <div class="comments-list"><article v-for="comment in comments" :key="comment.id" class="place-comment"><div class="comment-avatar" aria-hidden="true">{{[...comment.author.trim()][0]?.toUpperCase()||'•'}}</div><div class="comment-content"><div class="comment-meta"><strong>{{comment.author}}</strong><time :datetime="comment.created_at">{{formatDate(comment.created_at)}}</time></div><p class="comment-body">{{comment.body}}</p><button v-if="comment.can_delete" class="delete-comment" :disabled="commentBusy" @click="deleteComment(comment.id)" aria-label="Usuń swój komentarz">Usuń swój komentarz</button></div></article></div>
  <button v-if="community&&nextOffset<community.comment_count" class="text-link more-comments" :disabled="loadingMore||loading" @click="load(true)">{{loadingMore?'Wczytuję…':'Pokaż starsze komentarze'}}</button>
  </div>
 </section>
</template>

<style scoped>
.place-community{border-top:1px solid #e3e9dc;margin-top:27px;padding-top:24px}.visit-summary{display:flex;align-items:center;justify-content:space-between;gap:15px}.visit-total{display:flex;align-items:center;gap:12px;color:#19744f}.visit-total span{display:flex;flex-direction:column;gap:3px}.visit-total strong{font-family:Manrope,sans-serif;font-size:25px;line-height:1.2}.visit-total small{font-size:10px;color:#7c8876}.visit-button{border:1px solid #cddbc5;border-radius:8px;padding:11px 16px;font-size:12px;font-weight:600;display:flex;align-items:center;gap:7px;color:#19744f;background:#f1f6ec}.visit-button.visited{background:#19744f;color:white;border-color:#19744f}.place-community .visit-hint{font-size:10px;line-height:1.6;margin:12px 0 0}.comments-heading{margin:27px 0 16px}.comments-heading h3{display:flex;align-items:center;gap:8px;font-size:17px;letter-spacing:-.5px}.comments-heading h3 span{background:#edf3e6;color:#19744f;border-radius:20px;padding:3px 8px;font-size:10px}.place-community .community-notice,.place-community .comments-empty{font-size:12px;line-height:1.8;margin:14px 0;color:#829077}.community-login{background:#f0f4e9;padding:15px;border-radius:9px;margin-bottom:18px}.place-community .community-login p{font-size:11px;line-height:1.7;margin:0 0 5px}.community-login .text-link{font-size:11px}.comment-form{margin-bottom:22px}.comment-form label{margin:0 0 8px;font-size:12px;font-weight:600}.comment-form textarea{display:block;width:100%;resize:vertical;min-height:90px;max-height:260px;border:1px solid #d5dfcc;border-radius:9px;background:white;padding:12px;font:inherit;font-size:12px;color:#172b2b;line-height:1.7}.comment-form textarea:focus{outline:2px solid #81ac8a;outline-offset:2px}.comment-form-bottom{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:10px}.comment-form-bottom small{font-size:9px;color:#84927a}.comment-form-bottom .button{padding:10px 14px;font-size:11px}.place-comment{display:flex;gap:11px;border-top:1px solid #e8edde;padding:18px 0}.comment-avatar{width:30px;height:30px;border-radius:50%;background:#e8f0e0;color:#4e7546;font-size:12px;font-weight:700;display:grid;place-items:center;flex-shrink:0}.comment-content{min-width:0;flex:1}.comment-meta{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap}.comment-meta strong{font-size:12px;overflow-wrap:anywhere}.comment-meta time{font-size:9px;color:#8b9585}.place-community .comment-body{font-size:12px;line-height:1.8;white-space:pre-wrap;overflow-wrap:anywhere;margin:8px 0 0;color:#5b6856}.delete-comment{color:#8c6a51;font-size:9px;text-decoration:underline;padding:0;margin-top:9px}.place-community .community-error{font-size:11px;line-height:1.7;color:#a64d37;margin:13px 0}.community-error button{color:#19744f;text-decoration:underline;padding:0;font-size:inherit}.more-comments{margin:auto;font-size:11px}
@media(max-width:480px){.visit-button{padding:10px 12px}.visit-total{gap:8px}.visit-total small{font-size:9px}.comment-meta{gap:4px}.comment-meta time{width:100%}}
</style>

<style scoped>
.place-community{padding-top:18px;margin-top:22px}.community-action-row{display:flex;gap:7px;align-items:stretch;width:100%}.community-action-row>button{flex:1;min-width:0;display:flex;justify-content:center;align-items:center;gap:6px;padding:10px 8px;margin:0;border:1px solid #d5dfcc;border-radius:8px;background:#f4f7ef;color:#19744f;font-family:inherit;font-weight:600;font-size:11px;line-height:1.3;white-space:nowrap}.community-action-row>button svg{flex-shrink:0}.community-action-row>button strong{font-family:inherit;font-weight:700;font-size:11px;line-height:1.3;padding-left:6px;border-left:1px solid #c9d7c1}.community-action-row>.place-like-button.liked,.community-action-row>.visit-button.visited{background:#19744f;color:white;border-color:#19744f}.community-action-row>.comments-toggle[aria-expanded=true]{background:#e3eedb;border-color:#91af7d}.comments-panel{margin-top:20px}.community-action-row>button:focus-visible{outline:2px solid #19744f;outline-offset:3px}
@media(max-width:480px){.community-action-row{gap:4px}.community-action-row>button{padding:10px 5px;gap:4px;font-size:10px}.community-action-row>button strong{font-size:10px;padding-left:4px}.community-action-row>button svg{width:14px;height:14px}}
</style>

<style scoped>@media(max-width:360px){.community-action-row>button svg{display:none}}</style>

<style scoped>
.community-action-row>button{padding-left:6px;padding-right:6px;gap:5px;font-size:10px}.community-action-row>button strong{font-size:10px;padding-left:5px}.community-action-row>button svg{width:15px;height:15px}.community-action-row>.community-favorite.saved{background:#19744f;border-color:#19744f;color:#fff}
@media(max-width:480px){.community-action-row>button{padding-left:3px;padding-right:3px;gap:4px;font-size:10px}.community-action-row>button svg{display:none}.community-action-row>button strong{font-size:10px;padding-left:4px}}
@media(max-width:360px){.community-action-row{gap:3px}.community-action-row>button{font-size:9px;gap:3px}.community-action-row>button strong{font-size:9px;padding-left:3px}}
</style>
