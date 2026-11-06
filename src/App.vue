<script setup>
function imageFallback(event){event.target.onerror=null;event.target.src="/images/heritage-placeholder.svg"}
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick, provide, defineAsyncComponent } from 'vue'
import Search from "lucide-vue-next/dist/esm/icons/search.js"
import ThumbsUp from 'lucide-vue-next/dist/esm/icons/thumbs-up.js'
import MessageCircle from 'lucide-vue-next/dist/esm/icons/message-circle.js'
import House from "lucide-vue-next/dist/esm/icons/house.js"
import ArrowRight from "lucide-vue-next/dist/esm/icons/arrow-right.js"
import ArrowUpRight from "lucide-vue-next/dist/esm/icons/arrow-up-right.js"
import Heart from "lucide-vue-next/dist/esm/icons/heart.js"
import Trees from "lucide-vue-next/dist/esm/icons/trees.js"
import Castle from "lucide-vue-next/dist/esm/icons/castle.js"
import Bike from "lucide-vue-next/dist/esm/icons/bike.js"
import Footprints from "lucide-vue-next/dist/esm/icons/footprints.js"
import Utensils from "lucide-vue-next/dist/esm/icons/utensils.js"
import Bed from "lucide-vue-next/dist/esm/icons/bed.js"
import MapPin from "lucide-vue-next/dist/esm/icons/map-pin.js"
import Clock3 from "lucide-vue-next/dist/esm/icons/clock-3.js"
import Signal from "lucide-vue-next/dist/esm/icons/signal.js"
import X from "lucide-vue-next/dist/esm/icons/x.js"
import Plus from "lucide-vue-next/dist/esm/icons/plus.js"
import Minus from "lucide-vue-next/dist/esm/icons/minus.js"
import Download from "lucide-vue-next/dist/esm/icons/download.js"
import ChevronRight from "lucide-vue-next/dist/esm/icons/chevron-right.js"
import ChevronUp from "lucide-vue-next/dist/esm/icons/chevron-up.js"
import ChevronDown from "lucide-vue-next/dist/esm/icons/chevron-down.js"
import Compass from "lucide-vue-next/dist/esm/icons/compass.js"
import SlidersHorizontal from "lucide-vue-next/dist/esm/icons/sliders-horizontal.js"
import Route from "lucide-vue-next/dist/esm/icons/route.js"
import Check from "lucide-vue-next/dist/esm/icons/check.js"
import Menu from "lucide-vue-next/dist/esm/icons/menu.js"
import LogOut from "lucide-vue-next/dist/esm/icons/log-out.js"
import Leaf from "lucide-vue-next/dist/esm/icons/leaf.js"
import Mountain from "lucide-vue-next/dist/esm/icons/mountain.js"
import Navigation from "lucide-vue-next/dist/esm/icons/navigation.js"
import Mail from "lucide-vue-next/dist/esm/icons/mail.js"
import { places as initialPlaces, categories, trails } from './data'
import TravelMap from './components/TravelMap.vue'
import BrandMark from './components/BrandMark.vue'
import PlaceContact from './components/PlaceContact.vue'
import TripNavigation from './components/TripNavigation.vue'
import Grid2X2 from 'lucide-vue-next/dist/esm/icons/grid-2x2.js'
import PlaceCommunity from './components/PlaceCommunity.vue'
import ExploreHome from './components/ExploreHome.vue'
import HomeAddressSearch from './components/HomeAddressSearch.vue'
import AdminRegions from './components/AdminRegions.vue'
const PolandRegions=defineAsyncComponent(()=>import('./components/PolandRegions.vue'))
import List from 'lucide-vue-next/dist/esm/icons/list.js'
import Sparkles from 'lucide-vue-next/dist/esm/icons/sparkles.js'
import AiPlanner from './components/AiPlanner.vue'
import PwaControls from './components/PwaControls.vue'
import AddPlaceForm from './components/AddPlaceForm.vue'
import PlacePhotos from './components/PlacePhotos.vue'
import {uploadPlacePhotos} from './placePhotos.js'
import { sanitizeCustomPoints } from './customPoints.js'
import { useRouting, buildGpx } from './useRouting.js'
import {useTripMetrics,tripDistance,tripDuration} from './useTripMetrics.js'
import {readAddress,forgetAddress} from './rememberedAddress.js'
import { distanceKm, placeFacets } from './explore.js'
import {readApiJson} from './apiResponse.js'
import {readOfflineMap} from './offlineMaps.js'
import { useGeolocation, geolocationKey } from './useGeolocation.js'
const geolocation=useGeolocation()
provide(geolocationKey,geolocation)
const {position:userLocation,loading:locating,error:locationError,locate,stop:stopGps}=geolocation
import { shortRouteName } from './routeNames.js'
import { createRouteCover } from './routeCover.js'
import { viewFromUrl, updateViewUrl } from './navigation.js'
const icons = { trees: Trees, castle: Castle, bike: Bike, footprints: Footprints, utensils: Utensils, bed: Bed }
function read(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback } catch { return fallback } }
const homeDisplay=read('perly:home-display',{})
const homeView=ref(homeDisplay?.view==='list'?'list':'tiles')
const homeTileSize=ref(['small','medium','large'].includes(homeDisplay?.size)?homeDisplay.size:'medium')
watch([homeView,homeTileSize],([view,size])=>{try{localStorage.setItem('perly:home-display',JSON.stringify({view,size}))}catch{}})
const legacyRoutePoints=sanitizeCustomPoints(read('perly-custom-places',[]))
const routePoints=ref(sanitizeCustomPoints(read('perly-route-points',legacyRoutePoints)).filter(p=>read('perly-route',[]).includes(p.id)))
const places=ref([...initialPlaces]), view=ref(viewFromUrl(window.location)), category=ref('all'), query=ref(''), selected=ref(read('perly-route',[1,5,3])), favorites=ref(read('perly-favorites',[])), saved=ref(read('perly-saved',[]).map(r=>({...r,custom_points:sanitizeCustomPoints(r.custom_points||legacyRoutePoints.filter(p=>r.place_ids.includes(p.id)))}))), modal=ref(null), detail=ref(null), toast=ref(''), menu=ref(false), onlyFavorites=ref(false), transport=ref('bike'), apiOnline=ref(false), user=ref(read('perly-user',null)), token=ref(localStorage.getItem('perly-token') || ''), authMode=ref('login'), authEmail=ref(''), authPassword=ref(''), authName=ref(''), authError=ref(''), busy=ref(false), routeName=ref('Moja lubuska przygoda')
const regions=ref([{slug:'lubuskie',name:'Lubuskie',allowed_types:['castle','palace','lake','nature','heritage','leisure','beach','stay','vineyard','food'],active:true}])
const selectedRegion=ref(typeof read('perly:region','lubuskie')==='string'?read('perly:region','lubuskie'):'lubuskie')
const regionInfo=computed(()=>selectedRegion.value==='all'?null:regions.value.find(r=>r.slug===selectedRegion.value))
const regionalPlaces=computed(()=>selectedRegion.value==='all'?places.value:places.value.filter(p=>(p.region||'lubuskie')===selectedRegion.value))
watch(selectedRegion,value=>{try{localStorage.setItem('perly:region',JSON.stringify(value))}catch{}})
async function loadRegions(){try{const data=await api('/regions');if(Array.isArray(data)&&data.length&&data.every(r=>r.slug&&Array.isArray(r.allowed_types))){regions.value=data;if(selectedRegion.value!=='all'&&!data.some(r=>r.slug===selectedRegion.value))selectedRegion.value=data[0].slug}}catch{}}
async function refreshCatalog(){places.value=await api('/places');await loadRegions()}
async function refreshAdminAccess(){if(!token.value||!user.value)return;try{const profile=await api('/auth/me');if(profile?.id===user.value.id){user.value=profile;localStorage.setItem('perly-user',JSON.stringify(profile))}}catch{if(user.value)user.value={...user.value,is_superadmin:false}}}
onMounted(()=>{loadRegions();refreshAdminAccess()})
let restoringHistory=false
updateViewUrl(view.value,{replace:true})
watch(view,target=>{if(!restoringHistory)updateViewUrl(target)},{flush:'sync'})
function restoreHistory(){restoringHistory=true;try{modal.value=null;navigate(viewFromUrl(window.location))}finally{restoringHistory=false}}
onMounted(()=>window.addEventListener('popstate',restoreHistory))
onBeforeUnmount(()=>window.removeEventListener('popstate',restoreHistory))
const routeIsPublic=ref(false)
const routeDescription=ref(''),routeDraft=ref(null),routeSaving=ref(false),routeSaveError=ref('')
const returnToAddPlace=ref(false),placeSaving=ref(false),placeSaveError=ref('')
function openCreatePlace(){
 placeSaveError.value=''
 if(!apiOnline.value){notify('Dodawanie miejsc wymaga połączenia z serwerem.');return}
 if(!user.value){returnToAddPlace.value=true;modal.value='auth';return}
 modal.value='add-place'
}
async function savePlace(data){
 if(placeSaving.value)return
 placeSaving.value=true;placeSaveError.value=''
 try{const {photos=[],...fields}=data;if(photos.length&&!fields.photo_rights_confirmed)throw new Error('Potwierdź zgodę na publikację zdjęć.');const photo_ids=await uploadPlacePhotos(photos,token.value);const result=await api('/places',{method:'POST',body:JSON.stringify({...fields,photo_ids})});places.value=[...places.value,result];modal.value=null;notify('Dodano miejsce do katalogu.');openDetail(result)}catch(e){placeSaveError.value=e.message}finally{placeSaving.value=false}
}
function updatePlacePhotos(place){const index=places.value.findIndex(p=>p.id===place.id);if(index>=0)places.value[index]={...places.value[index],...place};if(detail.value?.id===place.id)detail.value={...detail.value,...place};notify('Dodano zdjęcia miejsca.')}
const onlyMyTrips=ref(false),editingRoute=ref(null)
const routePreview=ref(false),previewRoute=ref(null),copyingTrip=ref(null)
const plannerFocus=ref(null)
const storedRoutePositions=read('perly:route-positions',[])
const pointPositions=ref(Array.isArray(storedRoutePositions)?storedRoutePositions.filter(p=>p&&selected.value.includes(p.id)&&Number.isFinite(p.lat)&&Math.abs(p.lat)<=90&&Number.isFinite(p.lng)&&Math.abs(p.lng)<=180):[])
const startPositionLocked=ref(pointPositions.value.some(p=>p.id===-9000000000001))
const navigating=ref(false),navigationReturnView=ref(null),navigationDestination=ref(null),navigationOrigin=ref(null),directTransport=ref('walk')
watch(userLocation,point=>{if(navigating.value&&navigationDestination.value&&!navigationOrigin.value&&point)navigationOrigin.value={...point}})
function openPlaceNavigation(place){detail.value=place;directTransport.value=transport.value==='bike'?'bike':'walk';modal.value='navigate-place'}
const googleNavigationUrl=computed(()=>detail.value?'https://www.google.com/maps/dir/?'+new URLSearchParams({api:'1',destination:detail.value.details?.coordinate_accuracy==='street'&&detail.value.details?.address?detail.value.details.address+', Polska':detail.value.lat+','+detail.value.lng,travelmode:directTransport.value==='bike'?'bicycling':'walking'}):'')
async function startPlaceNavigation(){
 navigationReturnView.value=view.value;navigationDestination.value={...detail.value}
 navigationOrigin.value=userLocation.value?{...userLocation.value}:null
 modal.value=null;await nextTick();navigating.value=true;if(!userLocation.value)locate();if(!apiOnline.value)loadCatalog()
}
const tripLibraryView=ref(read('perly:trip-view','list')==='tiles'?'tiles':'list')
watch(tripLibraryView,value=>{try{localStorage.setItem('perly:trip-view',JSON.stringify(value))}catch{}})
watch(view,()=>navigating.value=false)
async function startNavigation(route){navigationDestination.value=null;navigationOrigin.value=null;navigationReturnView.value=view.value;if(route)openSavedRoute(route);await nextTick();navigating.value=true;if(!userLocation.value)locate();if(!apiOnline.value)loadCatalog()}
function closeNavigation(){navigating.value=false;navigationDestination.value=null;navigationOrigin.value=null;const previous=navigationReturnView.value;navigationReturnView.value=null;if(previous&&previous!==view.value)navigate(previous)}
const plannerStartPoint=ref(null)
const plannerAddNotice=ref(false),plannerNoticeVersion=ref(0)
const gpsStartId=-9000000000001
const plannerPlaceCount=computed(()=>selected.value.filter(id=>id!==gpsStartId).length)
const plannerCountLabel=computed(()=>{const n=plannerPlaceCount.value;return n===1?'miejsce':n%10>=2&&n%10<=4&&(n%100<12||n%100>14)?'miejsca':'miejsc'})
watch([()=>plannerStartPoint.value||userLocation.value,()=>view.value,()=>selected.value[0],startPositionLocked],([point,current])=>{
 if(current!=='explore'||navigating.value||editingRoute.value||startPositionLocked.value)return
 if(!point){
  if(selected.value.includes(gpsStartId)){selected.value=selected.value.filter(id=>id!==gpsStartId);routePoints.value=routePoints.value.filter(p=>p.id!==gpsStartId)}
  return
 }
 const start=sanitizeCustomPoints([{id:gpsStartId,name:point.name?'Start: '+point.name:'Twoja pozycja GPS',lat:point.lat,lng:point.lng}])[0]
 if(!start)return
 routePoints.value=[start,...routePoints.value.filter(p=>p.id!==gpsStartId)]
 if(selected.value[0]!==gpsStartId)selected.value=[gpsStartId,...selected.value.filter(id=>id!==gpsStartId)]
 pointPositions.value=pointPositions.value.filter(p=>p.id!==gpsStartId)
},{immediate:true})

function setPlannerStart(point){if(point?.name&&point!==plannerStartPoint.value)startPositionLocked.value=false;plannerStartPoint.value=point}
watch(()=>selected.value.includes(gpsStartId),exists=>{if(!exists)startPositionLocked.value=false})
watch(pointPositions,value=>{try{localStorage.setItem('perly:route-positions',JSON.stringify(value))}catch{}},{deep:true})
function moveRoutePoint(point){
 const allowed=view.value==='explore'&&!editingRoute.value||editingRoute.value&&isOwnRoute(editingRoute.value)
 if(!allowed||!selected.value.includes(point.id)||!Number.isFinite(point.lat)||!Number.isFinite(point.lng)||Math.abs(point.lat)>90||Math.abs(point.lng)>180)return
 if(point.id===gpsStartId){startPositionLocked.value=true;routePoints.value=routePoints.value.map(p=>p.id===gpsStartId?{...p,name:'Własny punkt startowy'}:p)}
 pointPositions.value=[...pointPositions.value.filter(p=>p.id!==point.id),{id:point.id,lat:point.lat,lng:point.lng}]
}

function isOwnRoute(route){return route.local?(!route.owner_id||route.owner_id===user.value?.id):!!user.value&&serverSaved.value.some(r=>r.id===route.id)}
function editSavedRoute(route){
 if(!isOwnRoute(route))return
 openSavedRoute(route);navigate('explore')
 routeIsPublic.value=!!route.is_public
 routePoints.value=sanitizeCustomPoints(route.custom_points||[])
 pointPositions.value=(route.point_positions||[]).map(p=>({...p}))
 editingRoute.value={id:route.id,local:!!route.local,owner_id:route.owner_id}
}
async function copySavedRoute(route){
 if(!route||copyingTrip.value!==null)return
 copyingTrip.value=route.id
 try{
  const copy={name:(route.name+' — kopia').slice(0,120),description:route.description||'',transport:route.transport,place_ids:[...route.place_ids],point_positions:(route.point_positions||[]).map(p=>({...p})),custom_points:sanitizeCustomPoints(route.custom_points||[]).map(({id,name,lat,lng})=>({id,name,lat,lng})),cover_image:route.cover_image||'',is_public:false}
  const result=await persistRoute(copy)
  editSavedRoute(result)
  notify('Utworzono prywatną kopię. Możesz edytować swoją wycieczkę.')
 }catch(error){notify(error.message)}
 finally{copyingTrip.value=null}
}
function openAddRoute(){if(!selected.value.length)return;if(editingRoute.value){modal.value='save';return}routeDraft.value={name:shortRouteName(selectedPlaces.value),description:'',is_public:false,transport:transport.value==='walk'?'walk':'bike',place_ids:[...selected.value],point_positions:pointPositions.value.filter(p=>selected.value.includes(p.id)).map(p=>({...p}))};routeSaveError.value='';modal.value='add-route'}
function snapshotRoutePoints(ids){return routePoints.value.filter(p=>ids.includes(p.id)).map(({id,name,lat,lng})=>({id,name,lat,lng}))}
async function persistRoute(route){
 if(route.place_ids.some(id=>id<0))route={...route,custom_points:route.custom_points??snapshotRoutePoints(route.place_ids)}
 if(route.is_public&&(!user.value||!apiOnline.value))throw new Error('Zaloguj się, aby zapisać publiczną trasę.')
 if(user.value&&apiOnline.value&&(!route.place_ids.some(id=>id<0)||route.is_public)){const result=await api('/routes',{method:'POST',body:JSON.stringify(route)});serverSaved.value=[result,...serverSaved.value];syncPublicRoute(result);return result}
 const result={...route,id:Date.now(),...(user.value?{owner_id:user.value.id}:{})};const next=[...saved.value,result];storeLocalRoutes(next);return {...result,local:true}
}
function storeLocalRoutes(routes){try{localStorage.setItem('perly-saved',JSON.stringify(routes))}catch{throw new Error('Brak miejsca na zdjęcie trasy w przeglądarce. Usuń niepotrzebne zapisane trasy.')}saved.value=routes}
async function saveNewRoute(){
 const draft=routeDraft.value;if(!draft||routeSaving.value||!draft.name.trim())return
 routeSaving.value=true;routeSaveError.value=''
 try{
  const route={...draft,name:draft.name.trim(),description:draft.description.trim()};route.cover_image=await createRouteCover({points:route.place_ids.map(id=>(id<0?routePoints.value:places.value).find(p=>p.id===id)).filter(Boolean).map(p=>{const position=route.point_positions?.find(item=>item.id===p.id);return position?{...p,lat:position.lat,lng:position.lng}:p}),geometry:route.transport===transport.value?computedRoute.value?.geometry:null,transport:route.transport});await persistRoute(route)
  routeName.value=route.name;routeDescription.value=route.description;transport.value=route.transport;selected.value=[...route.place_ids]
  routeDraft.value=null;modal.value=null;navigate(route.transport==='walk'?'walking':'cycling');notify('Trasa została zapisana.')
 }catch(e){routeSaveError.value=e.message}
 finally{routeSaving.value=false}
}
function openSavedRoute(route){selected.value=[...route.place_ids];transport.value=route.transport;routeName.value=route.name;routeDescription.value=route.description||'';modal.value=null;navigate('planner');routeIsPublic.value=!!route.is_public;routePoints.value=sanitizeCustomPoints(route.custom_points||legacyRoutePoints.filter(p=>route.place_ids.includes(p.id)));pointPositions.value=(route.point_positions||[]).map(p=>({...p}));editingRoute.value=isOwnRoute(route)?{id:route.id,local:!!route.local,owner_id:route.owner_id}:null;routePreview.value=true;previewRoute.value=route}
const liking=ref([])
function updateSocial(data){const place=places.value.find(p=>p.id===data.id);if(place)Object.assign(place,data);if(detail.value?.id===data.id)Object.assign(detail.value,data)}
async function toggleLike(id){
 const place=places.value.find(p=>p.id===id)
 if(!place||liking.value.includes(id))return
 if(!apiOnline.value){notify('Polubienia wymagają połączenia z serwerem.');return}
 if(!user.value){detail.value=place;requestPlaceLogin();return}
 liking.value.push(id)
 try{const data=await api(`/places/${id}/like`,{method:place.liked?'DELETE':'PUT'});updateSocial({id,...data})}
 catch(e){notify(e.message)}
 finally{liking.value=liking.value.filter(value=>value!==id)}
}
let toastTimer,plannerNoticeTimer
function showPlannerAdded(){plannerAddNotice.value=true;plannerNoticeVersion.value++;clearTimeout(plannerNoticeTimer);plannerNoticeTimer=setTimeout(()=>plannerAddNotice.value=false,3200)}
onBeforeUnmount(()=>{clearTimeout(toastTimer);clearTimeout(plannerNoticeTimer)})
const publicSaved=ref([])
async function loadPublicRoutes(){try{const routes=await api('/routes/public');if(Array.isArray(routes))publicSaved.value=routes}catch{}}
function syncPublicRoute(route){publicSaved.value=publicSaved.value.filter(r=>r.id!==route.id);if(route.is_public)publicSaved.value.unshift(route)}
const serverSaved=ref([]), trailFilter=ref('all')
const returnToPlace=ref(null)
const googleMapsUrl=computed(()=>detail.value?`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(detail.value.details?.coordinate_accuracy==='street'?`${detail.value.details.address}, Polska`:`${detail.value.lat},${detail.value.lng}`)}`:'')
function requestPlaceLogin(){returnToPlace.value=detail.value;modal.value='auth'}
watch(modal,(value,previous)=>{if(previous==='auth'&&value===null){returnToPlace.value=null;returnToAddPlace.value=false}})
const canSaveOnServer=computed(()=>!!user.value&&apiOnline.value&&(editingRoute.value?(!editingRoute.value.local||routeIsPublic.value):(!selected.value.some(id=>id<0)||routeIsPublic.value)))
const libraryType=computed(()=>view.value==='walking'?'walk':view.value==='cycling'?'bike':'all')
const libraryRoutes=computed(()=>savedPlans.value.filter(route=>(libraryType.value==='all'||route.transport===libraryType.value)&&(!onlyMyTrips.value||isOwnRoute(route))))
function routeCover(route){return route.cover_image||places.value.find(p=>p.id===route.place_ids[0])?.image||'/images/custom-point.svg'}
const savedPlans=computed(()=>{const own=user.value&&apiOnline.value?serverSaved.value:[];return [...own,...publicSaved.value.filter(r=>!own.some(o=>o.id===r.id)),...saved.value.map(r=>({...r,local:true}))]})
const homeRouteGroups=computed(()=>[
 {id:'home-walking',title:'Trasy piesze',type:'walk',view:'walking',icon:Footprints},
 {id:'home-cycling',title:'Trasy rowerowe',type:'bike',view:'cycling',icon:Bike}
].map(group=>({...group,count:savedPlans.value.filter(r=>r.transport===group.type).length,routes:savedPlans.value.filter(r=>r.transport===group.type).slice(0,3)})))
watch(routePoints,value=>localStorage.setItem('perly-route-points',JSON.stringify(value)),{deep:true})
function createCustomPoint(data){
 if(routePoints.value.length>=100){notify('Możesz zapisać do 100 własnych punktów. Usuń niepotrzebny punkt, aby dodać kolejny.');return}
 let id=-Date.now();while(routePoints.value.some(p=>p.id===id))id--
 const point=sanitizeCustomPoints([{...data,id}])[0];if(!point){notify('Sprawdź nazwę i współrzędne punktu.');return}
 routePoints.value.push(point);selected.value.push(point.id);notify('Dodano punkt pomocniczy do tej trasy.')
}
function deleteCustomPoint(point){
 routePoints.value=routePoints.value.filter(p=>p.id!==point.id);selected.value=selected.value.filter(id=>id!==point.id);modal.value=null;notify('Usunięto punkt z bieżącej trasy. Zapisz trasę, aby zachować zmianę.')
}

const filtered=computed(()=>regionalPlaces.value.filter(p=>(category.value==='all'||p.category===category.value)&&(!onlyFavorites.value||favorites.value.includes(p.id))&&`${p.name} ${p.subtitle} ${p.location}`.toLocaleLowerCase('pl').includes(query.value.toLocaleLowerCase('pl'))))
const selectedPlaces=computed(()=>selected.value.map(id=>{const place=(id<0?routePoints.value:places.value).find(p=>p.id===id);const position=pointPositions.value.find(p=>p.id===id);return place&&position?{...place,lat:position.lat,lng:position.lng}:place}).filter(Boolean))
const plannerPlaces=computed(()=>routePreview.value?selectedPlaces.value:filtered.value)
function selectPlannerMarker(id){if(routePreview.value){const place=selectedPlaces.value.find(p=>p.id===id);if(place)openDetail(place)}else togglePlace(id)}
const featured=computed(()=>category.value==='all'&&!query.value&&!onlyFavorites.value? [...filtered.value].filter(p=>p.details?.kind!=='custom').sort((a,b)=>(b.popularity??0)-(a.popularity??0)).slice(0,20):filtered.value)
const straightDistance=computed(()=>selectedPlaces.value.reduce((sum,p,i,points)=>i?sum+distanceKm(points[i-1],p):0,0))
const {route:computedRoute,loading:routeLoading,error:routeError,offline:routeOffline,refresh:refreshRoute}=useRouting({ids:selected,transport,enabled:computed(()=>view.value==='planner'||view.value==='explore'),online:apiOnline,customPoints:routePoints,pointPositions})
const tripMetrics=useTripMetrics({routes:libraryRoutes,enabled:computed(()=>['trips','walking','cycling'].includes(view.value)),online:apiOnline})
watch(computedRoute,value=>{if(value)tripMetrics.remember({transport:transport.value,place_ids:selected.value,custom_points:snapshotRoutePoints(selected.value),point_positions:pointPositions.value},value)})
const plannerGeometry=computed(()=>computedRoute.value?.geometry||null)
const directIds=computed(()=>navigationDestination.value&&navigationOrigin.value?[-9000000000002,navigationDestination.value.id]:[])
const directPoints=computed(()=>navigationOrigin.value?[{id:-9000000000002,name:'Punkt startowy',lat:navigationOrigin.value.lat,lng:navigationOrigin.value.lng}]:[])
const directRoute=useRouting({ids:directIds,transport:directTransport,enabled:computed(()=>navigating.value&&!!navigationDestination.value),online:apiOnline,customPoints:directPoints})
const navigationGeometry=computed(()=>navigationDestination.value?directRoute.route.value?.geometry||null:plannerGeometry.value)
const navigationRoute=computed(()=>navigationDestination.value?directRoute.route.value:computedRoute.value)
const navigationDistance=computed(()=>navigationRoute.value?tripDistance(navigationRoute.value):'—')
const navigationDuration=computed(()=>navigationRoute.value?tripDuration(navigationRoute.value):'—')
const connectionLoading=ref(false)
const navigationLoading=computed(()=>(connectionLoading.value&&!navigationGeometry.value)||(navigationDestination.value?directRoute.loading.value:routeLoading.value))
const navigationOffline=computed(()=>navigationDestination.value?directRoute.offline.value:routeOffline.value)
const navigationPlaces=computed(()=>navigationDestination.value?[navigationDestination.value]:selectedPlaces.value)
const navigationError=computed(()=>!apiOnline.value&&!navigationGeometry.value?'Wyznaczanie nowej trasy wymaga połączenia z serwerem. Zapisana wcześniej trasa jest dostępna offline.':navigationDestination.value?directRoute.error.value:routeError.value)
async function retryNavigation(){
 if(!apiOnline.value){await loadCatalog();return}
 navigationDestination.value?directRoute.refresh():refreshRoute()
}

const distance=computed(()=>computedRoute.value?new Intl.NumberFormat('pl',{maximumFractionDigits:2}).format(computedRoute.value.distance_m/1000):transport.value==='car'?new Intl.NumberFormat('pl',{maximumFractionDigits:2}).format(straightDistance.value):'—')
const travelTime=computed(()=>{if(computedRoute.value){const minutes=Math.max(1,Math.round(computedRoute.value.duration_s/60));return minutes<60?minutes+' min':Math.floor(minutes/60)+' h '+minutes%60+' min'}return '—'})

watch(selected,v=>{localStorage.setItem('perly-route',JSON.stringify(v));routePoints.value=routePoints.value.filter(p=>v.includes(p.id));pointPositions.value=pointPositions.value.filter(p=>v.includes(p.id))},{deep:true})
watch(favorites,v=>localStorage.setItem('perly-favorites',JSON.stringify(v)),{deep:true})
watch(saved,v=>localStorage.setItem('perly-saved',JSON.stringify(v)),{deep:true})
async function api(path,options={}) {const response=await fetch(`/api${path}`,{signal:AbortSignal.timeout(8000),...options, headers:{'Content-Type':'application/json',...(token.value?{Authorization:`Bearer ${token.value}`} :{}),...options.headers}});return readApiJson(response)}
function notify(message){toast.value=message;clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.value='',4000)}
function navigate(target){catalogFacet.value='';plannerFocus.value=null;routeIsPublic.value=false;routePreview.value=false;previewRoute.value=null;editingRoute.value=null;view.value=target;menu.value=false;onlyFavorites.value=false;category.value='all';query.value='';window.scrollTo({top:0,behavior:'smooth'})}
function openProvince(slug){
 const region=regions.value.find(item=>item.slug===slug)
 if(!region)return
 forgetAddress()
 try{localStorage.setItem('perly:places-query','Województwo: '+region.name)}catch{}
 selectedRegion.value=slug;navigate('places')
}
function focusSearch(){navigate('places');nextTick(()=>document.getElementById('explore-query')?.focus())}
function chooseCategory(id){if(id==='bike'||id==='walk'){transport.value=id;trailFilter.value=trailFilter.value===id?'all':id;document.querySelector('#trails')?.scrollIntoView({behavior:'smooth'});return}category.value=category.value===id?'all':id;document.querySelector('#places')?.scrollIntoView({behavior:'smooth',block:'start'})}
async function toggleFavorite(id){const exists=favorites.value.includes(id);favorites.value=exists?favorites.value.filter(x=>x!==id):[...favorites.value,id];if(user.value&&apiOnline.value&&id>0){try{await api(`/favorites/${id}`,{method:exists?'DELETE':'PUT'})}catch(e){favorites.value=exists?[...favorites.value,id]:favorites.value.filter(x=>x!==id);notify(e.message)}}}
function addToList(place){const exists=selected.value.includes(place.id);if(!exists){selected.value.push(place.id);showPlannerAdded()}modal.value=null;if(view.value!=='explore'&&view.value!=='places'){navigate('explore');plannerFocus.value={lat:place.lat,lng:place.lng}}notify(exists?'To miejsce jest już w planerze.':'Dodano miejsce do planera.')}
function togglePlace(id){selected.value=selected.value.includes(id)?selected.value.filter(x=>x!==id):[...selected.value,id]}
function move(index,delta){const list=[...selected.value];[list[index],list[index+delta]]=[list[index+delta],list[index]];selected.value=list}
function openPlannerPlace(place){detail.value=place;modal.value='planner-place'}
function previewDescription(place){const text=(place.description||place.subtitle||'').replace(/\s+/g,' ').trim();return text.length>220?text.slice(0,220).replace(/\s+\S*$/,'')+'…':text}
function openDetail(place){detail.value=place;modal.value=place.details?.kind==='custom'?'route-point':'detail'}
function useAiProposal(plan){
 navigate('planner');routePoints.value=sanitizeCustomPoints(plan.custom_points);selected.value=[...plan.place_ids];transport.value=plan.transport;routeName.value=plan.name;routeDescription.value=[plan.description||'',...(plan.warnings||[])].filter(Boolean).join(' ');routeIsPublic.value=false;routePreview.value=true;modal.value=null;notify('Propozycja AI jest w planerze. Możesz ją sprawdzić i zapisać.')
}
function planTrail(trail){selected.value=[...trail.ids];transport.value=trail.type;navigate('planner');notify('Dodano miejsca z inspiracji. Uzupełnij swój plan.')} 
function showFavorites(){navigate('discover');onlyFavorites.value=true;setTimeout(()=>document.querySelector('#places')?.scrollIntoView({behavior:'smooth'}),50)}
const heroTab=ref('ai'),catalogFacet=ref('')
const heroCategories=computed(()=>placeFacets.map(f=>({...f,count:regionalPlaces.value.filter(f.match).length})))
function moveHeroTab(direction){const tabs=['ai','address','regions','categories'];heroTab.value=direction===-99?tabs[0]:direction===99?tabs.at(-1):tabs[(tabs.indexOf(heroTab.value)+direction+tabs.length)%tabs.length];nextTick(()=>document.getElementById('hero-tab-'+heroTab.value)?.focus())}
function openHomeCategory(id){navigate('places');catalogFacet.value=id}
const heroAiPrompt=ref(''),initialAiPrompt=ref('')
function openAi(prompt=''){if(!prompt.trim()){document.querySelector('.hero-search input')?.focus();document.querySelector('.hero-search')?.scrollIntoView({behavior:'smooth',block:'center'});return}initialAiPrompt.value=prompt.trim();modal.value='ai'}
function planFromHero(){if(heroAiPrompt.value.trim().length>=5)openAi(heroAiPrompt.value)}
function search(){if(view.value!=='discover')view.value='discover';setTimeout(()=>document.querySelector('#places')?.scrollIntoView({behavior:'smooth'}),50)}
async function saveRoute(){
 if(!selected.value.length||routeSaving.value)return
 routeSaving.value=true
 try{
  const data={name:routeName.value.trim(),description:routeDescription.value.trim(),place_ids:[...selected.value],transport:transport.value,is_public:routeIsPublic.value}
  if(pointPositions.value.length)data.point_positions=pointPositions.value.filter(p=>selected.value.includes(p.id)).map(p=>({...p}))
  if(data.place_ids.some(id=>id<0))data.custom_points=snapshotRoutePoints(data.place_ids)
  data.cover_image=await createRouteCover({points:selectedPlaces.value,geometry:computedRoute.value?.geometry,transport:transport.value})
  if(editingRoute.value){
   const target=editingRoute.value
   if(!isOwnRoute(target))throw new Error('Możesz edytować tylko swoje wycieczki.')
   if(target.local){if(!saved.value.some(r=>r.id===target.id))throw new Error('Nie znaleziono wycieczki.');if(data.is_public){await persistRoute(data);storeLocalRoutes(saved.value.filter(r=>r.id!==target.id))}else storeLocalRoutes(saved.value.map(r=>r.id===target.id?{...r,...data}:r))}
   else{const result=await api(`/routes/${target.id}`,{method:'PUT',body:JSON.stringify(data)});serverSaved.value=serverSaved.value.map(r=>r.id===target.id?result:r);syncPublicRoute(result)}
   editingRoute.value=null;modal.value=null;navigate(data.transport==='walk'?'walking':'cycling');notify('Zapisano zmiany wycieczki.')
  }else{await persistRoute(data);notify(canSaveOnServer.value?'Trasa została zapisana na koncie.':'Trasa zapisana na tym urządzeniu.');modal.value=null}
 }
 catch(e){notify(e.message)}finally{routeSaving.value=false}
}
async function deleteSaved(route){if(!isOwnRoute(route))return;if(user.value&&apiOnline.value&&!route.local){try{await api(`/routes/${route.id}`,{method:'DELETE'});serverSaved.value=serverSaved.value.filter(r=>r.id!==route.id);publicSaved.value=publicSaved.value.filter(r=>r.id!==route.id)}catch(e){notify(e.message)}}else{saved.value=saved.value.filter(r=>r.id!==route.id)}}
function exportGpx(){if(!selected.value.length||routeLoading.value)return;const xml=buildGpx(routeName.value,selectedPlaces.value,computedRoute.value);const url=URL.createObjectURL(new Blob([xml],{type:'application/gpx+xml'}));const a=document.createElement('a');a.href=url;a.download='perly-ziemi-lubuskiej.gpx';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notify(computedRoute.value?'Pobrano trasę GPX.':'Pobrano punkty GPX — bez przebiegu po drogach.')}

async function authenticate(){busy.value=true;authError.value='';try{const result=await api(`/auth/${authMode.value}`,{method:'POST',body:JSON.stringify({email:authEmail.value,password:authPassword.value,name:authName.value})});token.value=result.access_token;user.value=result.user;localStorage.setItem('perly-token',token.value);localStorage.setItem('perly-user',JSON.stringify(user.value));const [remote,routes,catalog]=await Promise.all([api('/favorites'),api('/routes'),api('/places')]);favorites.value=remote;serverSaved.value=routes;places.value=catalog;if(returnToPlace.value){detail.value=returnToPlace.value;returnToPlace.value=null;modal.value='detail'}else if(returnToAddPlace.value){returnToAddPlace.value=false;modal.value='add-place'}else{modal.value=null}authPassword.value='';notify('Witaj! Czas na kolejną przygodę.')}catch(e){authError.value=e.message}finally{busy.value=false}}
function logout(){user.value=null;token.value='';places.value.forEach(place=>place.liked=false);localStorage.removeItem('perly-user');localStorage.removeItem('perly-token');notify('Wylogowano.')}
let catalogRequest,connectionDisposed=false
function loadCatalog(){
 if(catalogRequest)return catalogRequest
 connectionLoading.value=true
 catalogRequest=(async()=>{
  try{const result=await api('/places',{signal:AbortSignal.timeout(15000)});if(!Array.isArray(result))throw new Error('Invalid catalog');if(connectionDisposed)return false;places.value=result;apiOnline.value=true;return true}
  catch{if(!connectionDisposed){apiOnline.value=false;const savedMap=await readOfflineMap();if(!connectionDisposed&&savedMap?.places?.length)places.value=savedMap.places}return false}
  finally{connectionLoading.value=false;catalogRequest=null}
 })()
 return catalogRequest
}
function reconnect(){if(!apiOnline.value&&document.visibilityState==='visible')loadCatalog()}
onMounted(async()=>{window.addEventListener('online',reconnect);document.addEventListener('visibilitychange',reconnect);loadPublicRoutes();await loadCatalog();if(!connectionDisposed&&apiOnline.value&&user.value){try{const [remote,routes]=await Promise.all([api('/favorites'),api('/routes')]);favorites.value=remote;serverSaved.value=routes}catch{logout();notify('Sesja wygasła. Zaloguj się ponownie.')}}})
onBeforeUnmount(()=>{connectionDisposed=true;window.removeEventListener('online',reconnect);document.removeEventListener('visibilitychange',reconnect)})
let previousFocus
watch(modal,async value=>{if(value){previousFocus=document.activeElement;await nextTick();document.querySelector('.modal')?.focus()}else previousFocus?.focus?.()})
function trapFocus(event){if(event.key!=='Tab')return;const items=[...document.querySelectorAll('.modal button:not([disabled]),.modal input:not([disabled]),.modal textarea:not([disabled]),.modal select:not([disabled]),.modal a[href]')];const first=items[0],last=items.at(-1);if(!first)return;if(event.shiftKey&&(document.activeElement===first||document.activeElement.classList.contains('modal'))){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}}
</script>

<style>
.start-page .hero{height:auto;min-height:545px;background-position:center 48%;isolation:isolate}.start-page .hero-shade{background:linear-gradient(90deg,#082b2ae6 0%,#103b3273 53%,#173c3340 100%),linear-gradient(0deg,#10392a5e,transparent 60%)}.start-page .hero-inner{display:grid;grid-template-columns:1fr 1.12fr;gap:60px;align-items:center;padding-top:60px;padding-bottom:65px}.start-page .hero h1{font-size:clamp(38px,4.1vw,64px);letter-spacing:-2.5px;line-height:1.12;margin:24px 0 22px}.start-page .hero-copy>p{font-size:15px;color:#e3ece3;line-height:1.85}.start-page .eyebrow{font-size:9px;letter-spacing:1.8px;color:#e5eddb}.start-page .hero-hint{margin-top:30px;font-size:11px;color:#e3eddf;gap:8px}.hero-ai-panel{background:#ffffffb8;color:#172f2b;border:1px solid #ffffff85;border-radius:22px;padding:28px;box-shadow:0 20px 70px #06251f40;min-width:0;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px)}.hero-ai-top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:23px}.hero-ai-badge{display:inline-flex;align-items:center;gap:8px;background:#d9edab;color:#245733;font-size:11px;font-weight:800;letter-spacing:1px;padding:9px 12px;border-radius:8px}.hero-ai-caption{font-size:10px;color:#7d8d7e}.hero-ai-panel h2{font-size:27px;letter-spacing:-1px;line-height:1.3}.start-page #hero-panel-ai>p{color:#748277;font-size:12px;line-height:1.8;margin:10px 0 22px;max-width:360px}.start-page .hero-search{max-width:none;height:auto;min-height:62px;gap:10px;border:1px solid #bacfb0;border-radius:12px;background:#fff;margin:0;padding:7px 7px 7px 14px;box-shadow:0 4px 14px #245c2f08;color:#19744f}.start-page .hero-search:focus-within{outline:3px solid #b7d7846b;border-color:#6d9e59}.start-page .hero-search input{font-size:12px;color:#1d3d30;width:0}.start-page .hero-search input::placeholder{color:#8a9689}.start-page .hero-search button{display:flex;justify-content:center;gap:8px;width:auto;height:44px;padding:0 13px;border-radius:8px;font-size:11px;font-weight:700;transition:background .15s}.start-page .hero-search button:disabled{opacity:1;background:#e5ecdf;color:#819377}.start-page .hero-search button:not(:disabled):hover{background:#105c3e}.hero-ai-examples{margin-top:19px}.hero-ai-examples>span{font-size:10px;color:#87917f}.hero-ai-examples>div{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px}.hero-ai-examples button{display:inline-flex;align-items:center;gap:6px;border:1px solid #dde5d4;border-radius:20px;background:#f7f9f2;padding:8px 10px;color:#506d4c;font-size:10px;line-height:1.4;transition:border-color .15s,background .15s}.hero-ai-examples button:hover{background:#eaf3dd;border-color:#adca95}.hero-ai-footnote{display:flex;align-items:center;gap:7px;padding-top:17px;margin-top:20px;border-top:1px solid #e5eadf;color:#7c8c74;font-size:10px;line-height:1.6}.start-page>.content-width{padding-top:6px}.start-page .places-section{padding-top:38px}.start-page .place-image{border-radius:12px}.start-page .section-heading h2{letter-spacing:-.9px}.start-page .home-route-empty{border-style:solid;background:#f4f7ee;border-radius:12px}.start-page .photo-credit{font-size:8px}
@media(max-width:1100px){.start-page .hero-inner{gap:30px;grid-template-columns:1fr 1.2fr;padding-top:42px;padding-bottom:45px}.hero-ai-panel{padding:22px}.hero-ai-caption{display:none}.hero-ai-panel h2{font-size:24px}.start-page .hero h1{letter-spacing:-1.5px}.start-page .hero-search button span{display:none}}
@media(max-width:760px){.start-page .hero-inner{grid-template-columns:1fr;gap:27px;padding-top:32px;padding-bottom:35px}.start-page .hero{background-position:64% center}.start-page .hero h1{font-size:40px;margin:16px 0 12px;letter-spacing:-1.5px}.start-page .hero-copy>p{font-size:12px;line-height:1.8}.start-page .hero-hint{margin-top:14px;font-size:10px}.hero-ai-panel{padding:21px;border-radius:17px}.hero-ai-top{margin-bottom:16px}.hero-ai-caption{display:block;font-size:9px}.hero-ai-panel h2{font-size:24px}.start-page #hero-panel-ai>p{margin:9px 0 18px}.start-page .hero-search input{font-size:11px}.start-page .hero-search{min-height:58px;padding-left:11px;gap:7px}.start-page .hero-search button{padding:0 12px;height:42px}.hero-ai-examples button{font-size:9px;padding:7px 9px}.hero-ai-footnote{font-size:9px;margin-top:16px;padding-top:14px}.start-page .photo-credit{display:none}.start-page .places-section{padding-top:29px}}
@media(prefers-reduced-motion:reduce){.start-page button{transition:none}}
</style>

<template>
 <header class="site-header responsive-header">
  <a href="#" class="brand" @click.prevent="navigate('explore')" aria-label="Perły Ziemi Lubuskiej — strona główna">
   <BrandMark class="brand-mark"/>
   <span class="brand-name">Perły<br>Ziemi Lubuskiej</span>
  </a>
  <nav :class="{open:menu}" class="main-navigation" aria-label="Nawigacja główna">
   <button :class="{active:view==='discover'&&!onlyFavorites}" :aria-current="view==='discover'&&!onlyFavorites?'page':undefined" @click="navigate('discover')"><House :size="19" aria-hidden="true"/>Start</button>
   <button :class="{active:view==='places'}" :aria-current="view==='places'?'page':undefined" @click="navigate('places')"><MapPin :size="19" aria-hidden="true"/>Miejsca</button>
   <button :class="{active:view==='explore','planner-just-added':plannerAddNotice}" :aria-current="view==='explore'?'page':undefined" @click="navigate('explore')" data-nav-label="Planer"><Route :size="19" aria-hidden="true"/>Planer <span :key="'count-'+plannerPlaceCount" class="planner-nav-count" :data-count="plannerPlaceCount" aria-live="polite">({{plannerPlaceCount}} {{plannerCountLabel}})</span><span v-if="plannerAddNotice" :key="'notice-'+plannerNoticeVersion" class="planner-added-bubble" role="status"><Check :size="14"/>Dodano miejsce</span></button>
   <button :class="{active:['trips','walking','cycling','planner'].includes(view)}" :aria-current="['trips','walking','cycling','planner'].includes(view)?'page':undefined" @click="navigate('trips')"><Compass :size="19" aria-hidden="true"/>Wycieczki</button>
   <button v-if="user?.is_superadmin" :class="{active:view==='admin'}" @click="navigate('admin')">Administracja</button>
  </nav>
  <div class="header-actions"><PwaControls/><button class="icon-btn search-nav" aria-label="Szukaj miejsc" @click="focusSearch"><Search :size="22"/></button><button class="icon-btn favorites-nav" aria-label="Ulubione miejsca" @click="showFavorites"><Heart :size="23"/><span v-if="favorites.length" class="count-dot">{{favorites.length}}</span></button><button v-if="!user" class="button login-btn" @click="modal='auth'">Zaloguj się <ArrowUpRight :size="15"/></button><button v-else class="button login-btn" @click="logout">{{user.name || 'Wyloguj'}} <LogOut :size="16"/></button><button class="icon-btn mobile-menu" @click="menu=!menu" aria-label="Otwórz menu"><Menu/></button></div>
 </header>
 <div v-if="locationError" class="gps-status gps-error">
  <p role="alert">{{locationError}}</p>
  <button @click="locate()">Spróbuj ponownie</button>
  <button @click="stopGps()">Zamknij</button>
 </div>

 <AdminRegions v-if="view==='admin'" :key="token" :token="token" @login="modal='auth'" @changed="refreshCatalog" @catalog="selectedRegion=$event;navigate('places')"/>
 <ExploreHome @navigate-place="openPlaceNavigation" :point-positions="pointPositions" :editing="!!editingRoute" :editable="view==='explore'&&(!editingRoute||isOwnRoute(editingRoute))" @move-point="moveRoutePoint" @navigate="startNavigation()" :route-distance="distance" :route-duration="travelTime" @preview="openPlannerPlace" @route-start="setPlannerStart" :geometry="view==='explore'?plannerGeometry:null" :route-loading="routeLoading" :route-error="routeError" :transport="transport" @transport="transport=$event" @retry-route="refreshRoute" :initial-facet="catalogFacet" :regions="regions" @region="selectedRegion=$event" :focus-location="view==='explore'?plannerFocus:null" @create-point="createCustomPoint" :selected="view==='places'?[]:selected" @add="addToList" @remove="togglePlace" @move="move" @clear="selected=[]" @planner="openAddRoute" v-if="view==='explore'||view==='places'" :key="view+selectedRegion" :catalog-only="view==='places'" @create-place="openCreatePlace" :places="view==='explore'&&editingRoute?places:regionalPlaces" :region-info="regionInfo" :route-points="view==='places'?[]:routePoints.filter(p=>selected.includes(p.id))" :favorites="favorites" :online="apiOnline" :liking="liking" @like="toggleLike" @open="openDetail" @favorite="toggleFavorite"/>
 <main v-else-if="view==='discover'" class="start-page" :data-home-view="homeView" :data-tile-size="homeTileSize">
  <section class="hero">
   <div class="hero-shade"></div>
   <div class="hero-inner content-width">
    <div class="hero-copy"><div class="eyebrow"><span></span> BLISKO NATURY. DALEKO OD NUDY.</div><h1>Od pomysłu<br><em>do przygody.</em></h1><p>Odkryj ciekawe miejsca, ułóż własną trasę<br>i ruszaj po nowe wspomnienia.</p><div class="hero-hint"><MapPin :size="15"/><span>Łagów · tu zaczyna się przygoda</span></div></div>
    <div class="hero-ai-panel">
     <div class="hero-tabs" role="tablist" aria-label="Odkrywaj i planuj"><button v-for="tab in [{id:'ai',label:'Planer AI',icon:Sparkles},{id:'address',label:'Szukaj po adresie',icon:MapPin},{id:'regions',label:'Województwa',icon:Navigation},{id:'categories',label:'Kategorie',icon:Compass}]" :key="tab.id" :id="'hero-tab-'+tab.id" role="tab" :aria-selected="heroTab===tab.id" :aria-controls="'hero-panel-'+tab.id" :tabindex="heroTab===tab.id?0:-1" @click="heroTab=tab.id" @keydown.right.prevent="moveHeroTab(1)" @keydown.left.prevent="moveHeroTab(-1)" @keydown.home.prevent="moveHeroTab(-99)" @keydown.end.prevent="moveHeroTab(99)"><component :is="tab.icon" :size="19" aria-hidden="true"/><span>{{tab.label}}</span></button></div>
     <div v-show="heroTab==='ai'" id="hero-panel-ai" role="tabpanel" aria-labelledby="hero-tab-ai">
     <div class="hero-ai-top"><span class="hero-ai-badge"><Sparkles :size="17"/>PLANER AI</span><span class="hero-ai-caption">Twój pomysł → Twoja trasa</span></div>
     <h2 id="hero-ai-title">Na co masz dziś ochotę?</h2><p>Opisz swój idealny dzień. AI dobierze miejsca i ułoży trasę na mapie.</p>
     <form class="hero-search" @submit.prevent="planFromHero"><Sparkles :size="21" aria-hidden="true"/><input ref="searchInput" v-model="heroAiPrompt" placeholder="Np. dzień w Łagowie i kolacja nad jeziorem" aria-label="Opisz wycieczkę dla AI" minlength="5" maxlength="1000" required><button type="submit" aria-label="Zaplanuj wycieczkę z AI" title="Zaplanuj z AI" :disabled="heroAiPrompt.trim().length<5"><span>Zaplanuj</span><ArrowRight :size="21"/></button></form>
     <div class="hero-ai-examples" aria-label="Pomysły na polecenie AI"><span>Spróbuj na przykład</span><div><button type="button" @click="heroAiPrompt='Zaplanuj dzień w Łagowie';$nextTick(()=>searchInput?.focus())"><Castle :size="14"/>Dzień w Łagowie</button><button type="button" @click="heroAiPrompt='Zaplanuj spacer dookoła Jeziora Łagowskiego';$nextTick(()=>searchInput?.focus())"><Footprints :size="14"/>Spacer wokół jeziora</button><button type="button" @click="heroAiPrompt='Zaplanuj trasę rowerową po pałacach w okolicy Zaboru';$nextTick(()=>searchInput?.focus())"><Bike :size="14"/>Rowerem po pałacach</button></div></div>
     </div>
     <div v-show="heroTab==='address'" id="hero-panel-address" class="hero-address-panel" role="tabpanel" aria-labelledby="hero-tab-address"><HomeAddressSearch @found="navigate('places')"/></div>
     <div v-if="heroTab==='regions'" id="hero-panel-regions" class="hero-regions-panel" role="tabpanel" aria-labelledby="hero-tab-regions"><PolandRegions list-only :regions="regions" :places="places" :routes="publicSaved" @select="openProvince"/></div>
     <div v-if="heroTab==='categories'" id="hero-panel-categories" class="hero-categories-panel" role="tabpanel" aria-labelledby="hero-tab-categories"><h2>Odkrywaj według kategorii</h2><div class="hero-category-grid"><button v-for="item in heroCategories" :key="item.id" :data-facet="item.id" :disabled="!item.count" @click="openHomeCategory(item.id)"><strong>{{item.name}}</strong><span>{{item.count}} miejsc <ArrowRight :size="15"/></span></button></div></div>
    </div>
   </div><div class="photo-credit">Wizualizacja krajobrazu Ziemi Lubuskiej</div>
  </section>
  <div class="content-width">
   <PolandRegions :regions="regions" :places="places" :routes="publicSaved" @select="openProvince"/>
   <div class="home-display-toolbar" aria-label="Wygląd strony głównej">
    <div class="home-display-group home-display-icons" role="group" aria-label="Widok strony głównej"><span>Widok</span><button aria-label="Widok listy" title="Widok listy" :aria-pressed="homeView==='list'" @click="homeView='list'"><List :size="22" aria-hidden="true"/></button><button v-for="size in [{id:'large',label:'Duże kafelki',cells:2},{id:'medium',label:'Średnie kafelki',cells:3},{id:'small',label:'Małe kafelki',cells:4}]" :key="size.id" :aria-label="size.label" :title="size.label" :aria-pressed="homeView==='tiles'&&homeTileSize===size.id" @click="homeView='tiles';homeTileSize=size.id"><svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true" focusable="false"><rect v-for="cell in size.cells*size.cells" :key="cell" :x="3+((cell-1)%size.cells)*(20/size.cells)" :y="3+Math.floor((cell-1)/size.cells)*(20/size.cells)" :width="20/size.cells-2" :height="20/size.cells-2" :rx="size.cells===2?1.4:.6"/></svg></button></div>
   </div>
   <section id="places" class="places-section"><div class="section-heading"><div><div class="section-kicker">TWOJA NASTĘPNA PRZYGODA</div><h2>{{onlyFavorites?'Twoje ulubione miejsca':category==='all'&&!query?'Miejsca TOP 20': 'Odkryj coś dla siebie'}}<span class="heading-dot">.</span></h2></div><button class="text-link" @click="navigate('explore')">Zobacz na mapie <ArrowRight :size="18"/></button></div>
    <p v-if="!onlyFavorites&&category==='all'&&!query" class="top-places-note">Najwyżej według liczby polubień i komentarzy.</p>
    <div v-if="query||category!=='all'||onlyFavorites" class="filter-bar"><span>{{filtered.length}} {{filtered.length===1?'miejsce':'miejsc'}} <template v-if="query">dla „{{query}}”</template></span><button @click="query='';category='all';onlyFavorites=false">Wyczyść filtry <X :size="14"/></button></div>
    <div v-if="featured.length" class="place-grid"><article v-for="(place,index) in featured" :key="place.id" class="place-card"><button class="place-image" @click="openDetail(place)"><img :src="place.image" @error="imageFallback" :alt="place.name" loading="lazy"><span v-if="!onlyFavorites&&category==='all'&&!query" class="top-place-position" :aria-label="`Pozycja ${index+1}`">{{index+1}}</span><span class="place-tag">{{place.category==='vineyard'?'Winnice':categories.find(c=>c.id===place.category)?.name}}</span></button><button title="Twoje prywatne ulubione" :class="['heart-btn',{liked:favorites.includes(place.id)}]" :aria-label="`${favorites.includes(place.id)?'Usuń z ulubionych':'Dodaj do ulubionych'}: ${place.name}`" :aria-pressed="favorites.includes(place.id)" @click="toggleFavorite(place.id)"><Heart :size="20" :fill="favorites.includes(place.id)?'currentColor':'none'"/></button><div class="place-info"><span class="place-location"><MapPin :size="12"/> {{place.location}}</span><button @click="openDetail(place)" class="place-title">{{place.name}}</button><p>{{place.subtitle}}</p><div v-if="place.details?.kind!=='custom'" class="place-social"><button :class="{liked:place.liked}" :aria-label="`${place.liked?'Cofnij polubienie':'Polub'}: ${place.name}`" :aria-pressed="!!place.liked" :disabled="!apiOnline||liking.includes(place.id)" @click="toggleLike(place.id)"><ThumbsUp :size="14"/><span>{{apiOnline?(place.like_count??0):'—'}}</span></button><button :aria-label="`Komentarze: ${place.name}`" @click="openDetail(place)"><MessageCircle :size="14"/><span>{{place.comment_count??0}}</span></button></div><button class="card-arrow" :aria-label="`Zobacz ${place.name}`" @click="openDetail(place)"><ArrowUpRight :size="21"/></button></div></article></div>
    <div v-else class="empty-state"><Compass :size="36"/><h3>{{onlyFavorites?'Twoje odkrycia czekają na zapisanie':'Tutaj jeszcze nic nie znaleźliśmy'}}</h3><p>{{category==='stay'?'Baza noclegów jest w przygotowaniu. Tymczasem odkryj miejsca w okolicy.':'Spróbuj innej nazwy lub wybierz serduszko przy miejscu, które Cię zachwyci.'}}</p><button class="button" @click="query='';category='all';onlyFavorites=false">Odkrywaj miejsca <ArrowRight :size="16"/></button></div>
   </section>
   <section v-for="group in homeRouteGroups" :key="group.id" :id="group.id" class="home-route-section" :aria-labelledby="group.id+'-title'">
    <div class="section-heading"><div><div class="section-kicker">TWOJE ZAPISANE TRASY</div><h2 :id="group.id+'-title'"><component :is="group.icon" :size="24"/>{{group.title}}<span class="home-route-count">{{group.count}}</span></h2></div><button class="text-link" @click="navigate(group.view)">Zobacz wszystkie<ArrowRight :size="18"/></button></div>
    <div v-if="group.routes.length" class="home-route-grid"><button v-for="route in group.routes" :key="`${route.local?'local':'account'}-${route.id}`" class="home-route-card" @click="openSavedRoute(route)"><img :class="{'route-map-cover':!!route.cover_image}" :src="routeCover(route)" :alt="route.name" loading="lazy" @error="imageFallback"><span class="home-route-card-body"><strong>{{route.name}}</strong><small><component :is="group.icon" :size="14"/>{{route.place_ids.length}} miejsc · {{route.is_public?'Publiczna':route.local?'Prywatna · na tym urządzeniu':'Prywatna · na Twoim koncie'}}</small><span v-if="route.description" class="home-route-description">{{route.description}}</span><span class="home-route-open">Otwórz trasę<ArrowUpRight :size="17"/></span></span></button></div>
    <div v-else class="home-route-empty"><component :is="group.icon" :size="28"/><div><h3>{{group.type==='walk'?'Zaplanuj swoją pierwszą trasę pieszą':'Zaplanuj swoją pierwszą trasę rowerową'}}</h3><p>Wybierz miejsca i zapisz trasę, aby pojawiła się tutaj.</p></div><button class="text-link" @click="navigate('explore')">Wybierz miejsca<ArrowRight :size="17"/></button></div>
   </section>
   <section id="trails" class="trails-section"><div class="section-heading"><div><div class="section-kicker">PO DRODZE PO WSPOMNIENIA</div><h2>Wycieczki<span class="heading-dot">.</span></h2></div><button class="text-link" @click="navigate('planner')">Zaplanuj własną trasę <ArrowRight :size="18"/></button></div><div class="trail-grid"><button v-for="trail in trails.filter(t=>trailFilter==='all'||t.type===trailFilter)" :key="trail.id" class="trail-card" @click="planTrail(trail)"><div class="trail-image"><img :src="trail.image" :alt="trail.name" loading="lazy"><span class="trail-label"><component :is="trail.type==='bike'?Bike:Footprints" :size="15"/>{{trail.type==='bike'?'Na dwóch kółkach':'Krok po kroku'}}</span></div><div class="trail-info"><h3>{{trail.name}}</h3><div class="trail-meta"><span><MapPin :size="14"/> ok. {{trail.distance}} km</span><span><Clock3 :size="14"/> {{trail.time}}</span><span><Signal :size="15"/>{{trail.difficulty}}</span></div><ArrowUpRight :size="21" class="trail-arrow"/></div></button></div><p class="small-note">Inspiracje wycieczek — orientacyjne parametry. Planer pozwala wybrać punkty do odwiedzenia.</p></section>
   <section class="journey-banner"><div class="journey-illustration"><Route :size="56" :stroke-width="1.1"/><span class="orb one"></span><span class="orb two"></span></div><div><div class="section-kicker">TWÓJ DZIEŃ. TWOJE TEMPO.</div><h2>Najpiękniejsza trasa? Twoja własna.</h2><p>Wybierz miejsca, połącz je w plan i ruszaj po swoje wspomnienia.</p></div><button class="button" @click="navigate('planner')">Zaplanuj wycieczkę <ArrowRight :size="18"/></button></section>
  </div>
 </main>

 <main v-else-if="['trips','walking','cycling'].includes(view)" class="route-library content-width">
  <div class="route-library-heading"><div><div class="section-kicker">TWOJE ZAPISANE TRASY</div><h1><component :is="libraryType==='all'?Route:libraryType==='walk'?Footprints:Bike" :size="29"/>{{libraryType==='all'?'Wycieczki':libraryType==='walk'?'Wycieczki piesze':'Wycieczki rowerowe'}}</h1><p>Zapisane trasy: {{libraryRoutes.length}}</p></div></div>
  <div class="trip-type-tabs" role="group" aria-label="Rodzaj wycieczki"><button v-for="item in [{view:'trips',type:'all',label:'Wszystkie',icon:Route},{view:'walking',type:'walk',label:'Wycieczki piesze',icon:Footprints},{view:'cycling',type:'bike',label:'Wycieczki rowerowe',icon:Bike}]" :key="item.type" :aria-pressed="libraryType===item.type" @click="navigate(item.view)"><component :is="item.icon" :size="18"/>{{item.label}}</button></div>
  <label class="my-trips-filter"><input type="checkbox" v-model="onlyMyTrips">Moje wycieczki</label>
  <p v-if="onlyMyTrips" class="my-trips-note">Twoje wycieczki z konta i zapisane na tym urządzeniu. Kliknij „Edytuj”, aby zmienić opis, rodzaj lub punkty.</p>
  <div class="trip-library-view" role="group" aria-label="Widok wycieczek"><button :aria-pressed="tripLibraryView==='list'" aria-label="Wycieczki jako lista" @click="tripLibraryView='list'"><List :size="18"/>Lista</button><button :aria-pressed="tripLibraryView==='tiles'" aria-label="Wycieczki jako kafelki" @click="tripLibraryView='tiles'"><Grid2X2 :size="18"/>Kafelki</button></div>
  <div v-if="libraryRoutes.length" class="route-library-list" :class="{'trip-library-tiles':tripLibraryView==='tiles'}"><article v-for="route in libraryRoutes" :key="`${route.local?'local':'account'}-${route.id}`" class="route-library-item"><button class="route-library-open" @click="openSavedRoute(route)"><img :class="{'route-map-cover':!!route.cover_image}" :src="routeCover(route)" :alt="route.name" loading="lazy" @error="imageFallback"><span class="route-library-info"><strong>{{route.name}}</strong><small><component :is="route.transport==='car'?Navigation:route.transport==='walk'?Footprints:Bike" :size="14"/>{{route.transport==='car'?'Samochodowa':route.transport==='walk'?'Piesza':'Rowerowa'}} · {{route.place_ids.length}} miejsc · {{route.is_public?'Publiczna':route.local?'Prywatna · na tym urządzeniu':'Prywatna · na Twoim koncie'}}</small><span v-if="tripMetrics.get(route)" class="trip-card-metrics"><span><Route :size="15"/>{{tripDistance(tripMetrics.get(route))}} km</span><span><Clock3 :size="15"/>{{tripDuration(tripMetrics.get(route))}}</span><small>bez postojów</small></span><span v-else class="trip-card-metrics trip-metrics-pending">{{tripMetrics.state(route)==='loading'?'Obliczam km i czas…':tripMetrics.state(route)==='offline'?'Km i czas wymagają połączenia z serwerem.':'Brak danych o dystansie i czasie.'}}</span><span v-if="route.description" class="route-library-description">{{route.description}}</span><span v-else class="route-library-description">Ta trasa nie ma jeszcze opisu.</span></span><ArrowUpRight :size="20"/></button><button class="trip-navigation-start" @click="startNavigation(route)" :aria-label="'Uruchom nawigację: '+route.name"><Navigation :size="17"/>Nawigacja</button><button v-if="tripMetrics.state(route)==='error'" class="trip-metrics-retry" @click="tripMetrics.retry()" :aria-label="'Oblicz kilometry i czas: '+route.name">Oblicz km i czas</button><button class="route-library-copy" :disabled="copyingTrip!==null" :aria-label="'Skopiuj wycieczkę: '+route.name" @click="copySavedRoute(route)"><Plus :size="15"/>{{copyingTrip===route.id?'Kopiuję…':'Skopiuj'}}</button><button v-if="isOwnRoute(route)" class="route-library-edit" :aria-label="`Edytuj trasę: ${route.name}`" @click="editSavedRoute(route)"><SlidersHorizontal :size="16"/>Edytuj</button><button v-if="isOwnRoute(route)" class="route-library-delete" :aria-label="`Usuń trasę: ${route.name}`" @click="deleteSaved(route)"><X :size="16"/>Usuń</button></article></div>
  <div v-else class="route-library-empty"><component :is="libraryType==='all'?Route:libraryType==='walk'?Footprints:Bike" :size="42"/><h2>{{libraryType==='all'?'Nie ma jeszcze zapisanych wycieczek':libraryType==='walk'?'Nie masz jeszcze zapisanych wycieczek pieszych':'Nie masz jeszcze zapisanych wycieczek rowerowych'}}</h2><p>Wybierz punkty w „Planerze”, kliknij „Zapisz wycieczkę” i zapisz ją z odpowiednim rodzajem.</p><button class="button outline" @click="navigate('explore')">Przejdź do miejsc<ArrowRight :size="17"/></button></div>
 </main>
 <main v-else-if="view==='planner'" class="planner-page">
  <section class="planner-heading content-width"><div><div class="section-kicker">PRZYGODA ZACZYNA SIĘ OD POMYSŁU</div><h1>{{routePreview?routeName:'Zaplanuj swoją trasę'}}<span class="heading-dot">.</span></h1><p>{{routePreview?'Zaplanowane punkty Twojej wycieczki.':'Wybierz swoje perły. Resztę zostaw ciekawości.'}}</p></div><button class="text-link" @click="modal='saved'">Zapisane plany <Heart :size="17"/></button></section>
  <section :class="['planner-layout',{'route-preview-layout':routePreview||!!editingRoute}]"><aside v-if="!routePreview&&!editingRoute" class="planner-catalog"><div v-if="!routePreview" class="catalog-search"><Search :size="18"/><input v-model="query" placeholder="Szukaj miejsc…" aria-label="Szukaj w katalogu"></div><div v-if="!routePreview" class="catalog-tabs"><button :class="{active:category==='all'}" @click="category='all'">Wszystkie</button><button v-for="c in categories.filter(c=>['nature','heritage','food'].includes(c.id))" :key="c.id" :class="{active:category===c.id}" @click="category=c.id">{{c.name}}</button></div><p class="catalog-caption">{{plannerPlaces.length}} {{routePreview?'zaplanowanych miejsc':'miejsc do odkrycia'}}</p><button v-for="place in plannerPlaces" :key="place.id" :class="['catalog-place',{selected:selected.includes(place.id)}]" @click="routePreview?openDetail(place):togglePlace(place.id)"><img :src="place.image" @error="imageFallback" :alt="place.name"><span><strong>{{place.name}}</strong><small>{{place.subtitle}}</small><em><MapPin :size="11"/>{{place.location}}</em></span><span class="checkbox"><Check v-if="selected.includes(place.id)" :size="14"/><Plus v-else :size="14"/></span></button><p v-if="!plannerPlaces.length" class="small-note">Brak wyników. Zmień wyszukiwaną nazwę.</p></aside>
   <div class="map-panel"><TravelMap :user-location="userLocation" :places="routePreview?selectedPlaces:[...selectedPlaces,...places.filter(p=>!selected.includes(p.id))]" :draggable-points="!!editingRoute&&isOwnRoute(editingRoute)" @move-point="moveRoutePoint" :selected="selected" :geometry="plannerGeometry" :fit-places="routePreview" @select="selectPlannerMarker"/><div class="map-badge"><span class="live-dot"></span> Ziemia Lubuska <span>·</span> Twój plan podróży</div><div class="map-disclaimer"><Navigation :size="14"/>{{routeLoading?'Wyznaczam trasę po drogach i ścieżkach…':computedRoute?'Trasa po drogach i ścieżkach · OpenStreetMap':routeError?'Nie udało się wyznaczyć trasy. Spróbuj ponownie.':selected.length>=2?'Wybierz tryb pieszy lub rowerowy, aby wyznaczyć trasę.':'Dodaj co najmniej dwa punkty.'}}</div></div>
   <aside class="route-panel"><div class="route-title"><h2>Twoja trasa <span>{{selected.length}}</span></h2><button @click="selected=[]" :disabled="!selected.length">Resetuj</button></div><div class="route-list"><article v-for="(place,index) in selectedPlaces" :key="place.id" class="route-stop"><span class="stop-number">{{index+1}}</span><img :src="place.image" @error="imageFallback" :alt="place.name"><div><strong>{{place.name}}</strong><small>{{place.location}}</small></div><div v-if="!routePreview||editingRoute" class="stop-actions"><button :disabled="index===0" @click="move(index,-1)" :aria-label="`Przesuń ${place.name} wyżej`"><ChevronUp :size="14"/></button><button :disabled="index===selected.length-1" @click="move(index,1)" :aria-label="`Przesuń ${place.name} niżej`"><ChevronDown :size="14"/></button><button @click="togglePlace(place.id)" :aria-label="`Usuń ${place.name} z trasy`"><X :size="13"/></button></div></article><div v-if="!selected.length" class="route-empty"><MapPin :size="32"/><p>Każda przygoda ma początek.<br>Dodaj pierwsze miejsce z katalogu.</p></div></div><div class="transport-select"><button v-for="t in [{id:'bike',label:'Rowerem',icon:Bike},{id:'walk',label:'Pieszo',icon:Footprints},{id:'car',label:'Autem',icon:Navigation}]" :key="t.id" :class="{active:transport===t.id}" @click="transport=t.id"><component :is="t.icon" :size="21"/>{{t.label}}</button></div><div class="route-stats"><span><strong>{{distance}} km</strong><small>{{computedRoute?'Dystans po drogach':transport==='car'?'W linii prostej':routeLoading?'Obliczam dystans…':'Dystans trasy'}}</small></span><span><strong>~ {{travelTime}}</strong><small>Czas bez postojów</small></span></div><div class="routing-status" role="status"><p v-if="routeLoading">Wyznaczam trasę po drogach i ścieżkach…</p><p v-else-if="routeError" class="routing-error">{{routeError}} <button @click="refreshRoute">Spróbuj ponownie</button></p><p v-else-if="computedRoute">{{transport==='bike'?'Trasa rowerowa':'Trasa piesza'}} · BRouter / OpenStreetMap. Czas jest orientacyjny, bez postojów. Sprawdź warunki w terenie.</p><p v-else-if="transport==='car'">Tryb samochodowy zapisuje punkty bez wyznaczania przebiegu dróg.</p><p v-else-if="!apiOnline">Wyznaczanie trasy wymaga połączenia z serwerem.</p><p v-else>Dodaj co najmniej dwa miejsca, aby wyznaczyć trasę.</p></div><button class="button full-width" :disabled="!selected.length||routeLoading" @click="exportGpx"><Download :size="18"/> {{computedRoute?'Pobierz trasę (GPX)':'Pobierz punkty (GPX)'}}</button><button v-if="!routePreview||editingRoute" class="button outline full-width" :disabled="!selected.length" @click="modal='save'">Zapisz trasę</button><button v-else class="button outline full-width" :disabled="copyingTrip!==null" @click="copySavedRoute(previewRoute)">Skopiuj i edytuj</button></aside>
  </section>
 </main>

 <main v-else-if="view!=='admin'" class="about-page content-width"><div class="section-kicker">DOBRZE BYĆ BLISKO</div><h1>Ziemia Lubuska.<br><em>Naturalnie niezwykła.</em></h1><img src="/images/hero.webp" alt="Jezioro i zamek otoczone lasem"><div class="about-copy"><h2>Przestrzeń na małe odkrycia</h2><p>Między jeziorami, lasami i historycznymi miasteczkami czeka region, który najlepiej poznaje się bez pośpiechu. Od Łagowa po Park Mużakowski, od podziemnych historii po rozlewiska Warty — znajdź własny powód, żeby tu wrócić.</p><p>Perły Ziemi Lubuskiej to projekt pomagający zbierać pomysły na wycieczki. Opisy i zdjęcia mają charakter inspiracyjny. Przed wyjazdem sprawdź godziny otwarcia i dostępność wybranych atrakcji.</p><button class="button" @click="navigate('discover')">Znajdź swoją perłę <ArrowRight :size="18"/></button></div></main>

 <footer class="content-width"><a class="footer-brand" href="#" @click.prevent="navigate('explore')"><BrandMark class="footer-brand-mark"/>Perły Ziemi Lubuskiej</a><span>Blisko natury. Bliżej siebie.</span><div><span :class="['connection-status',{online:apiOnline}]"></span>{{apiOnline?'Połączono z serwerem':'Tryb demonstracyjny · dane lokalne'}}</div><a href="/heritage-credits.html" target="_blank" rel="noopener noreferrer">Źródła i licencje</a><small>© {{new Date().getFullYear()}} Perły Ziemi Lubuskiej</small></footer>

 <TripNavigation v-if="navigating" :transport="navigationDestination?directTransport:transport" :gps-interval="geolocation.refreshInterval.value" :gps-high-accuracy="geolocation.highAccuracy.value" @gps-interval="geolocation.setRefreshInterval($event)" @gps-accuracy="geolocation.setHighAccuracy($event)" :route-name="navigationDestination?navigationDestination.name:routeName" :user="user" :token="token" :geometry="navigationGeometry" :places="navigationPlaces" :offline="navigationOffline" :distance="navigationDistance" :duration="navigationDuration" :position="userLocation" :locating="locating" :loading="navigationLoading" :error="navigationError" :location-error="locationError" @back="closeNavigation" @refresh="locate()" @retry="retryNavigation"/>
 <Transition name="toast"><div v-if="toast" class="toast-message" role="status"><Check :size="18"/>{{toast}}<button @click="toast=''" aria-label="Zamknij komunikat"><X :size="16"/></button></div></Transition>
 <div v-if="modal" class="modal-overlay" :class="{'planner-preview-overlay':modal==='planner-place'||modal==='navigate-place'}" @click.self="modal=null" @keydown.esc="modal=null" @keydown="trapFocus"><section class="modal" :class="{'planner-place-modal':modal==='planner-place'||modal==='navigate-place'}" role="dialog" aria-modal="true" :aria-label="modal==='detail'||modal==='planner-place'?detail.name:modal==='navigate-place'?'Nawiguj do: '+detail.name:modal==='route-point'?'Punkt trasy':modal==='add-place'?'Dodaj miejsce':modal==='ai'?'Asystent tras AI':modal==='auth'?'Konto użytkownika':modal==='add-route'?'Zapisz wycieczkę':modal==='save'?'Zapisz trasę':'Zapisane trasy'" tabindex="-1"><button class="modal-close icon-btn" @click="modal=null" aria-label="Zamknij okno"><X :size="22"/></button>
  <div v-if="modal==='planner-place'" class="planner-place-preview"><div class="planner-preview-heading"><img :src="detail.image" @error="imageFallback" :alt="detail.name"><div><span>{{detail.location}}</span><h2>{{detail.name}}</h2></div></div><p class="planner-preview-description">{{previewDescription(detail)}}</p><div class="detail-actions"><button class="button full-width" :disabled="selected.includes(detail.id)" @click="addToList(detail)"><Plus :size="17"/>{{selected.includes(detail.id)?'Na liście':'Dodaj do listy'}}</button></div><button class="planner-preview-more" @click="openDetail(detail)">Pełny opis i źródła <ArrowRight :size="14"/></button></div>
  <template v-else-if="modal==='detail'"><PlacePhotos :place="detail" :user="user" :token="token" :online="apiOnline" @updated="updatePlacePhotos"/><div class="modal-body"><div class="section-kicker">{{detail.location}}</div><h2>{{detail.details?.official_name||detail.name}}</h2><p v-if="detail.details?.map_preview?.image===detail.image" class="small-note map-preview-note"><span v-if="detail.details.map_preview.geometry_available===false">Przybliżona lokalizacja · </span>Podgląd mapy · © OpenStreetMap contributors</p><p>{{detail.description}}</p><PlaceContact :contact="detail.details?.contact" :lake-info="detail.details?.lake_info"/><div v-if="detail.details?.address||detail.details?.location_note||detail.details?.visit_note" class="place-visit-info"><p v-if="detail.details.address"><strong>Adres:</strong> {{detail.details.address}}</p><p v-if="detail.details.location_note">{{detail.details.location_note}}</p><p v-if="detail.details.visit_note">{{detail.details.visit_note}}</p></div><details v-if="detail.details?.sources?.length||detail.details?.contact" class="heritage-provenance"><summary>Źródła danych</summary><div class="provenance-content"><p v-if="detail.details?.map_preview?.image===detail.image">Podgląd mapy: <a :href="detail.details.map_preview.source_url" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">dane ODbL 1.0</a>. Wycinek zapisany na serwerze.</p><p v-if="detail.details.website&&!detail.details?.contact?.website?.value"><a :href="detail.details.website" target="_blank" rel="noopener noreferrer">Strona winnicy lub obiektu</a></p><p v-if="detail.details.location_note">{{detail.details.location_note}}</p><p v-if="detail.details.visit_note">{{detail.details.visit_note}}</p><p>Współrzędne: <a :href="detail.details.coordinate_source" target="_blank" rel="noopener noreferrer">{{detail.lat.toFixed(6)}}, {{detail.lng.toFixed(6)}}</a><span v-if="detail.details.coordinate_license"> · {{detail.details.coordinate_license}}</span></p><p v-if="detail.details.photo&&detail.details?.map_preview?.image!==detail.image">Zdjęcie{{detail.details.photo.archival?' archiwalne':''}}: {{detail.details.photo.author}} · <a :href="detail.details.photo.license_url" target="_blank" rel="noopener noreferrer">{{detail.details.photo.license}}</a> · <a :href="detail.details.photo.source_url" target="_blank" rel="noopener noreferrer">Wikimedia Commons</a>. {{detail.details.photo.transformation}}</p><p v-else-if="!detail.details.user_photos?.length">Brak potwierdzonej fotografii — ilustracja zastępcza.</p><p>Źródła opisu: <span v-for="(source,index) in detail.details.sources" :key="source.url"><span v-if="index"> · </span><a :href="source.url" target="_blank" rel="noopener noreferrer">{{source.title}}</a></span>. {{detail.details.description_license}}.</p><p v-if="detail.details.condition==='ruins'||detail.details.condition==='site'">Obiekt obejmuje ruiny lub historyczne pozostałości.</p><template v-if="detail.details.contact"><p v-for="field in ['accommodation','restaurant','phone','email','website'].filter(key=>detail.details.contact[key]?.source_url)" :key="field"><a :href="detail.details.contact[field].source_url" target="_blank" rel="noopener noreferrer">{{({accommodation:'Nocleg',restaurant:'Restauracja',phone:'Telefon',email:'E-mail',website:'Strona WWW'})[field]}} — źródło informacji</a></p><p v-if="detail.details.contact.note">{{detail.details.contact.note}}</p></template></div></details><div class="detail-actions"><button class="button" :disabled="selected.includes(detail.id)" @click="addToList(detail)"><Plus :size="18"/>{{selected.includes(detail.id)?'Na liście':'Dodaj do listy'}}</button><button v-if="view==='places'" class="button outline" @click="openPlaceNavigation(detail)"><Navigation :size="17"/>Nawiguj</button></div><a class="button outline full-width google-maps-link" :href="googleMapsUrl" target="_blank" rel="noopener noreferrer"><MapPin :size="17"/>Otwórz w Google Maps<ArrowUpRight :size="16"/></a><template v-if="detail.details?.kind==='custom'"><p class="small-note">Twój prywatny punkt · {{detail.lat.toFixed(6)}}, {{detail.lng.toFixed(6)}} · zapisany na tym urządzeniu.</p><button class="button outline full-width" @click="deleteCustomPoint(detail)"><X :size="16"/>Usuń własny punkt</button></template><PlaceCommunity v-else :favorite="favorites.includes(detail.id)" @favorite="toggleFavorite(detail.id)" :place="detail" :user="user" :token="token" :online="apiOnline" @login="requestPlaceLogin" @notify="notify" @updated="updateSocial"/></div></template>
  <div v-else-if="modal==='navigate-place'" class="place-navigation-choice"><h2>Nawiguj do miejsca</h2><p>{{detail.name}}</p><div class="place-navigation-modes" role="group" aria-label="Rodzaj nawigacji"><button :aria-pressed="directTransport==='walk'" @click="directTransport='walk'"><Footprints :size="17"/>Pieszo</button><button :aria-pressed="directTransport==='bike'" @click="directTransport='bike'"><Bike :size="17"/>Rowerem</button></div><button class="button full-width place-navigation-app" @click="startPlaceNavigation"><Navigation :size="19"/>Aplikacja</button><a class="button outline full-width place-navigation-google" :href="googleNavigationUrl" target="_blank" rel="noopener noreferrer" @click="modal=null"><MapPin :size="19"/>Mapa Google<ArrowUpRight :size="16"/></a></div>
  <div v-else-if="modal==='auth'" class="modal-body auth-body"><div class="section-kicker">TWOJE MIEJSCE NA PRZYGODY</div><h2>{{authMode==='login'?'Dobrze Cię widzieć.':'Zacznij swoją podróż.'}}</h2><p>Zapisuj ulubione miejsca i plany wycieczek na swoim koncie.</p><div v-if="!apiOnline" class="api-notice">Logowanie wymaga uruchomionego backendu. Teraz możesz odkrywać miejsca i zapisywać plany lokalnie na tym urządzeniu.</div><form @submit.prevent="authenticate"><label v-if="authMode==='register'">Twoje imię<input v-model="authName" required maxlength="80" autocomplete="given-name"></label><label>Adres e-mail<input v-model="authEmail" type="email" required autocomplete="email"></label><label>Hasło<input v-model="authPassword" type="password" required minlength="8" maxlength="128" :autocomplete="authMode==='login'?'current-password':'new-password'" placeholder="Minimum 8 znaków"></label><p v-if="authError" class="form-error" role="alert">{{authError}}</p><button class="button full-width" :disabled="busy||!apiOnline">{{busy?'Chwileczkę…':authMode==='login'?'Zaloguj się':'Utwórz konto'}}<ArrowRight :size="17"/></button></form><button class="auth-switch" @click="authMode=authMode==='login'?'register':'login';authError=''">{{authMode==='login'?'Nie masz konta? Zarejestruj się':'Masz już konto? Zaloguj się'}}</button></div>
  <div v-else-if="modal==='add-route'&&routeDraft" class="modal-body new-route-body"><div class="section-kicker">TWOJE ZAPLANOWANE MIEJSCA</div><h2>Zapisz wycieczkę</h2><form class="new-route-form" @submit.prevent="saveNewRoute"><label for="new-route-name">Nazwa trasy<input id="new-route-name" v-model="routeDraft.name" required maxlength="120" :disabled="routeSaving"></label><label for="new-route-description">Opis trasy (opcjonalnie)<textarea id="new-route-description" v-model="routeDraft.description" maxlength="2000" rows="4" placeholder="Opisz, co warto zobaczyć po drodze…" :disabled="routeSaving"></textarea></label><fieldset class="route-visibility"><legend>Widoczność trasy</legend><label><input v-model="routeDraft.is_public" type="radio" :value="false" :disabled="routeSaving">Prywatna</label><label><input v-model="routeDraft.is_public" type="radio" :value="true" :disabled="routeSaving||!user||!apiOnline">Publiczna</label><small>{{user&&apiOnline?'Publiczna trasa będzie widoczna dla wszystkich.':'Zaloguj się, aby udostępnić trasę publicznie.'}}</small></fieldset><fieldset class="new-route-type"><legend>Rodzaj trasy</legend><label :class="{selected:routeDraft.transport==='bike'}"><input v-model="routeDraft.transport" type="radio" name="new-route-type" value="bike" :disabled="routeSaving" required><Bike :size="20"/>Rowerowa</label><label :class="{selected:routeDraft.transport==='walk'}"><input v-model="routeDraft.transport" type="radio" name="new-route-type" value="walk" :disabled="routeSaving" required><Footprints :size="20"/>Piesza</label></fieldset><p>{{routeDraft.place_ids.length}} miejsc w wybranej kolejności</p><p class="small-note">{{user&&apiOnline&&(!routeDraft.place_ids.some(id=>id&lt;0)||routeDraft.is_public)?'Trasa zostanie zapisana na Twoim koncie.':'Trasa zostanie zapisana na tym urządzeniu.'}}</p><p v-if="routeSaveError" class="form-error" role="alert">{{routeSaveError}}</p><button class="button full-width" type="submit" :disabled="routeSaving||!routeDraft.name.trim()">{{routeSaving?'Zapisuję…':'Zapisz trasę'}}<Check :size="18"/></button></form></div>
  <AiPlanner v-else-if="modal==='ai'" :places="regionalPlaces" :region="selectedRegion==='all'?'':selectedRegion" :online="apiOnline" :initial-prompt="initialAiPrompt" :auto-start="!!initialAiPrompt" @use="useAiProposal"/>
  <AddPlaceForm :regions="regions" :initial-region="selectedRegion==='all'?'lubuskie':selectedRegion" v-else-if="modal==='add-place'" :busy="placeSaving" :error="placeSaveError" @submit="savePlace"/>
  <div v-else-if="modal==='route-point'" class="modal-body"><div class="section-kicker">PUNKT POMOCNICZY TRASY</div><h2>{{detail.name}}</h2><p>Ten punkt należy tylko do Twojej trasy. Nie jest miejscem w katalogu.</p><p>{{detail.lat.toFixed(6)}}, {{detail.lng.toFixed(6)}}</p><button class="button outline full-width" @click="deleteCustomPoint(detail)"><X :size="16"/>Usuń punkt z trasy</button></div>
  <div v-else-if="modal==='save'" class="modal-body"><div class="section-kicker">ZACHOWAJ TEN POMYSŁ</div><h2>{{editingRoute?'Edytuj wycieczkę':'Jeszcze tu wrócisz.'}}</h2><label>Nazwa Twojej wycieczki<input v-model="routeName" maxlength="120" placeholder="Moja lubuska przygoda"></label><fieldset class="route-visibility"><legend>Widoczność trasy</legend><label><input v-model="routeIsPublic" type="radio" :value="false" :disabled="routeSaving">Prywatna</label><label><input v-model="routeIsPublic" type="radio" :value="true" :disabled="routeSaving||!user||!apiOnline">Publiczna</label><small>{{user&&apiOnline?'Publiczna trasa będzie widoczna dla wszystkich.':'Zaloguj się, aby udostępnić trasę publicznie.'}}</small></fieldset><label>Opis wycieczki (opcjonalnie)<textarea v-model="routeDescription" maxlength="2000" rows="4"></textarea></label><p>{{selected.length}} punktów · {{distance}} km {{computedRoute?'po trasie':'w linii prostej'}}</p><p class="small-note">{{canSaveOnServer?'Plan zostanie zapisany na Twoim koncie.':'Plan zostanie zapisany w przeglądarce na tym urządzeniu.'}}</p><button class="button full-width" :disabled="!routeName.trim()||routeSaving" @click="saveRoute">Zapisz trasę</button></div>
  <div v-else-if="modal==='saved'" class="modal-body"><div class="section-kicker">POMYSŁY NA KOLEJNY WOLNY DZIEŃ</div><h2>Zapisane trasy</h2><p v-if="!savedPlans.length">Nie masz jeszcze zapisanych planów. Wybierz miejsca na mapie i zapisz swoją pierwszą wycieczkę.</p><article v-for="route in savedPlans" :key="route.id" class="saved-route"><button @click="openSavedRoute(route)"><Route :size="22"/><span><strong>{{route.name}}</strong><small>{{route.transport==='walk'?'Piesza':route.transport==='bike'?'Rowerowa':'Samochodowa'}} · {{route.place_ids.length}} miejsc<span v-if="route.local"> · na tym urządzeniu</span></small><p v-if="route.description" class="saved-route-description">{{route.description}}</p></span><ArrowRight :size="18"/></button><button v-if="isOwnRoute(route)" class="icon-btn" @click="deleteSaved(route)" aria-label="Usuń zapisany plan"><X :size="16"/></button></article></div>
 </section></div>
</template>

<style>
.heritage-provenance{background:#f3f6ee;border-radius:8px;padding:12px 15px;margin:15px 0}.heritage-provenance summary{cursor:pointer;font-size:13px;font-weight:600;padding:3px 0}.provenance-content{padding-top:8px}.place-visit-info p{font-size:13px;line-height:1.7}.heritage-provenance p{font-size:11px;line-height:1.8;margin:4px 0;overflow-wrap:anywhere}.heritage-provenance a{text-decoration:underline;color:#176e4f}.planner-catalog{max-height:800px;overflow-y:auto}
</style>

<style>
.site-header .main-navigation{gap:34px}.site-header .main-navigation button{display:inline-flex;align-items:center;gap:9px;color:#19744f;transition:color .18s,opacity .18s}.site-header .main-navigation button>svg{stroke:currentColor;stroke-width:1.8;fill:none;transition:transform .18s}.site-header .main-navigation button:hover>svg{transform:translateY(-2px)}.site-header .main-navigation button.active{font-weight:800}.site-header .main-navigation button.active>svg{stroke-width:2.3}.site-header .main-navigation.open button{justify-content:flex-start;gap:12px}
@media(prefers-reduced-motion:reduce){.site-header .main-navigation button,.site-header .main-navigation button>svg{transition:none}.site-header .main-navigation button:hover>svg{transform:none}}
.site-header .main-navigation.open{gap:0}
</style>
<style>
@media(max-width:480px){.home-route-section .section-heading{flex-wrap:wrap}}
</style>

<style>
.place-social{display:flex;align-items:center;gap:15px;margin-top:12px}.place-social button{display:inline-flex;align-items:center;gap:6px;color:#728369;font-size:11px;padding:4px 0}.place-social button:hover,.place-social button.liked{color:#19744f}.place-social button.liked svg{fill:#dcebd1}.place-like-summary{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:24px}.place-like-button{display:flex;gap:9px;align-items:center;padding:11px 15px;border:1px solid #cddbc5;border-radius:8px;color:#19744f;background:#f1f6ec;font-size:12px;font-weight:600}.place-like-button.liked{color:#fff;background:#19744f;border-color:#19744f}.place-like-button strong{border-left:1px solid currentColor;padding-left:10px}.place-like-summary>span{font-size:10px;color:#7c8876}
</style>

<style>
.site-header .main-navigation{gap:24px}.site-header .main-navigation button{white-space:nowrap}
@media(max-width:1150px){.site-header .main-navigation{gap:14px}.site-header .main-navigation button{gap:6px}}
.site-header .main-navigation.open{gap:0}
</style>

<style>
.new-route-form>label{display:block;margin:18px 0;font-size:12px;font-weight:600}.new-route-form textarea{display:block;width:100%;min-height:110px;margin-top:8px;border:1px solid #d5dfcc;border-radius:8px;padding:12px;font:inherit;font-size:12px;line-height:1.7;resize:vertical;color:#294638}.new-route-form textarea:focus{outline:2px solid #81ac8a;outline-offset:2px}.new-route-type{border:0;padding:0;margin:22px 0;display:flex;gap:10px;flex-wrap:wrap}.new-route-type legend{font-size:12px;font-weight:600;margin-bottom:10px}.new-route-type>label{display:flex;align-items:center;gap:9px;padding:12px 16px;border:1px solid #d8e2ce;border-radius:8px;font-size:12px;flex:1;cursor:pointer}.new-route-type>label.selected{color:#19744f;background:#edf4e6;border-color:#9fbd8e}.new-route-type input{width:15px;height:15px;margin:0;accent-color:#19744f}.modal-body .saved-route-description{font-size:11px;line-height:1.7;margin:7px 0 0;white-space:pre-wrap;overflow-wrap:anywhere;text-align:left}.saved-route>button>span{min-width:0}.saved-route strong{overflow-wrap:anywhere}
</style>

<style>
.route-library{padding-top:38px;padding-bottom:55px;min-height:calc(100vh - 190px)}.route-library-heading{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:28px}.route-library-heading h1{display:flex;gap:12px;align-items:center;font-size:30px;letter-spacing:-1px;color:#173c2b;margin-top:9px}.route-library-heading p{font-size:12px;color:#87937b;margin-top:10px}.route-library-heading>.button{font-size:12px}.route-library-list{display:grid;gap:16px}.route-library-item{display:flex;align-items:center;gap:14px;background:#fff;border:1px solid #e0e7d9;border-radius:12px;padding:14px;box-shadow:0 3px 15px #1c402407}.route-library-open{display:flex;align-items:center;gap:22px;min-width:0;flex:1;text-align:left;padding:0}.route-library-open>img{width:155px;height:115px;border-radius:8px;object-fit:cover;flex-shrink:0}.route-library-info{display:flex;flex-direction:column;gap:10px;min-width:0;flex:1}.route-library-info>strong{font-size:17px;line-height:1.5;overflow-wrap:anywhere}.route-library-info>small{display:flex;align-items:center;gap:6px;font-size:10px;color:#749064;line-height:1.6}.route-library-description{font-size:12px;line-height:1.8;color:#74836b;white-space:pre-wrap;overflow-wrap:anywhere}.route-library-open>svg{color:#19744f;flex-shrink:0}.route-library-delete{display:flex;align-items:center;gap:5px;font-size:10px;color:#987254;padding:10px;border-radius:7px;flex-shrink:0}.route-library-delete:hover{background:#fcf1e7}.route-library-empty{display:flex;align-items:center;justify-content:center;flex-direction:column;gap:18px;background:#f5f8ef;border:1px dashed #d4dfc9;border-radius:12px;padding:70px 25px;text-align:center;color:#19744f}.route-library-empty h2{font-size:23px;line-height:1.5;letter-spacing:-.5px}.route-library-empty p{font-size:12px;color:#829176;max-width:470px;line-height:1.9}.route-library-empty .button{font-size:12px}
@media(max-width:1100px){.site-header .main-navigation{gap:11px}.site-header .main-navigation button{font-size:11px;gap:5px}.site-header .main-navigation button>svg{width:17px;height:17px}}
@media(max-width:650px){.route-library{padding-top:26px}.route-library-heading{align-items:flex-start;flex-wrap:wrap}.route-library-heading h1{font-size:24px}.route-library-heading>.button{font-size:11px;padding:11px}.route-library-item{align-items:stretch;gap:8px;padding:11px;flex-wrap:wrap}.route-library-open{gap:12px;width:100%;flex-basis:100%}.route-library-open>img{width:86px;height:100px}.route-library-info>strong{font-size:14px}.route-library-info>small{font-size:9px;flex-wrap:wrap}.route-library-description{font-size:11px}.route-library-delete{margin-left:auto;padding:5px}.route-library-empty{padding:50px 20px}.route-library-empty h2{font-size:20px}}
</style>

<style>
.top-place-position{position:absolute;top:12px;left:12px;display:grid;place-items:center;min-width:29px;height:29px;padding:0 7px;background:#19744f;color:#fff;border:1px solid #ffffff80;border-radius:8px;font-size:12px;font-weight:800;box-shadow:0 2px 7px #173f2b25}.top-places-note{color:#8b977f;font-size:11px;line-height:1.7;margin:-9px 0 19px}.home-route-section{margin:42px 0}.home-route-section h2{display:flex;align-items:center;gap:10px}.home-route-section h2>svg{color:#19744f}.home-route-count{font-size:11px;background:#edf4e6;color:#19744f;border-radius:20px;padding:4px 8px;letter-spacing:0}.home-route-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px}.home-route-card{display:flex;flex-direction:column;overflow:hidden;border-radius:11px;background:#fff;border:1px solid #e1e8d9;text-align:left;padding:0;min-width:0;box-shadow:0 3px 15px #193b2407}.home-route-card>img{height:165px;object-fit:cover;flex-shrink:0}.home-route-card-body{display:flex;flex-direction:column;padding:17px;gap:11px;min-width:0;width:100%;flex:1}.home-route-card-body>strong{font-size:15px;line-height:1.6;overflow-wrap:anywhere}.home-route-card-body>small{font-size:10px;color:#829474;display:flex;gap:6px;align-items:center}.home-route-description{font-size:11px;line-height:1.8;color:#819076;overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.home-route-open{display:flex;align-items:center;justify-content:space-between;font-size:11px;color:#19744f;margin-top:auto;padding-top:5px}.home-route-empty{display:flex;align-items:center;gap:17px;padding:24px;background:#f2f6eb;border:1px dashed #d4dfc8;border-radius:11px;color:#749267}.home-route-empty h3{font-size:14px;line-height:1.6;color:#35553b}.home-route-empty p{font-size:11px;line-height:1.8;color:#87967b;margin-top:5px}.home-route-empty>.text-link{margin-left:auto;font-size:11px;white-space:nowrap}
@media(max-width:800px){.home-route-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.home-route-empty{flex-wrap:wrap}.home-route-section{margin:34px 0}}
@media(max-width:480px){.home-route-grid{grid-template-columns:minmax(0,1fr)}.home-route-card>img{height:170px}.home-route-section h2{font-size:20px;gap:7px}.home-route-section .section-heading{align-items:center;gap:9px}.home-route-section .section-heading>.text-link{font-size:9px;white-space:nowrap}.home-route-empty{padding:18px;gap:12px}.home-route-empty>.text-link{margin-left:0}.top-place-position{top:8px;left:8px;min-width:24px;height:24px;font-size:10px}}
</style>

<style scoped>
.my-trips-filter{display:flex;align-items:center;gap:9px;font-size:13px;color:#19744f;margin:0 0 18px;cursor:pointer;width:fit-content}.my-trips-filter input{width:17px;height:17px;accent-color:#19744f}.my-trips-note{font-size:11px;color:#74836b;line-height:1.8;margin:-6px 0 18px}.route-library-edit{display:flex;align-items:center;gap:6px;color:#19744f;padding:10px;font-size:12px;border:1px solid #d5e2cb;border-radius:7px}.modal-body textarea{display:block;width:100%;padding:12px;margin-top:8px;border:1px solid #d5e2cb;border-radius:7px;font:inherit;resize:vertical}
</style>

<style scoped>
.planner-layout.route-preview-layout{grid-template-columns:minmax(0,1fr) 330px}.route-preview-layout .map-panel{border-left:0}
@media(max-width:1200px){.planner-layout.route-preview-layout{grid-template-columns:minmax(0,1fr) 295px}.route-preview-layout .route-panel{grid-column:auto;border-top:0}.route-preview-layout .route-list{display:block}}
@media(max-width:650px){.planner-layout.route-preview-layout{display:flex}.route-preview-layout .route-panel{border-top:1px solid var(--line)}}
</style>

<style scoped>
.home-route-card img.route-map-cover,.route-library-open img.route-map-cover{object-fit:contain;background:#edf1e7}
</style>

<style scoped>
.route-visibility{border:0;margin:20px 0;padding:0;display:flex;gap:16px;flex-wrap:wrap}.route-visibility legend{font-size:12px;font-weight:600;margin-bottom:9px}.route-visibility label{display:flex;gap:7px;align-items:center;font-size:12px;margin:0}.route-visibility input{width:16px;height:16px;accent-color:#19744f;margin:0}.route-visibility small{flex-basis:100%;font-size:10px;color:#7c8e70;line-height:1.6}
</style>

<style scoped>
.new-route-body{padding:26px 24px 24px}.new-route-body>.section-kicker{display:none}.new-route-body h2{font-size:24px;margin:0 36px 16px 0}
.new-route-form{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px 16px}
.new-route-body .new-route-form>label{grid-column:1/-1;margin:0;gap:6px;font-size:11px}.new-route-body .new-route-form>label input{padding:10px 12px}
.new-route-body .new-route-form textarea{min-height:62px;height:62px;margin:0;padding:9px 11px;line-height:1.5}
.new-route-body .new-route-form fieldset{margin:0;min-width:0;gap:7px;align-content:start;align-items:center}
.new-route-body .new-route-form legend{font-size:11px;margin-bottom:7px}
.new-route-body .new-route-form fieldset label{display:flex;flex-direction:row;align-items:center;gap:5px;margin:0;font-size:11px;white-space:nowrap}
.new-route-body .new-route-type>label{padding:8px;justify-content:center;border-radius:7px;min-height:35px}
.new-route-body .new-route-type svg{width:16px;height:16px;flex-shrink:0}
.new-route-body .new-route-form fieldset input,.modal-body .route-visibility input{padding:0;width:15px;height:15px;flex:0 0 15px;margin:0}
.modal-body .route-visibility label{flex-direction:row;margin:0}
.new-route-body .route-visibility small{font-size:9px;line-height:1.5;margin-top:2px}
.new-route-body .new-route-form>p{grid-column:1/-1;margin:0;font-size:10px;line-height:1.5}
.new-route-body .new-route-form>.small-note{margin-top:-7px;font-size:9px}
.new-route-body .new-route-form>button{grid-column:1/-1;margin-top:2px;padding:12px;font-size:12px}
@media(max-width:480px){.new-route-body{padding:24px 18px 18px}.new-route-form{column-gap:12px}.new-route-body .new-route-type svg{display:none}.new-route-body .new-route-type>label{padding:7px 5px}}
@media(max-width:340px){.new-route-form{grid-template-columns:minmax(0,1fr)}}
</style>

<style scoped>
</style>

<style>
.home-display-toolbar{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:12px 24px;margin:24px 0 0;padding:12px 14px;border:1px solid #dce5d3;border-radius:10px;background:#f5f8ef}.home-display-group{display:flex;align-items:center;flex-wrap:wrap;gap:5px}.home-display-group>span{font-size:11px;color:#74846a;margin-right:6px}.home-display-group button{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-height:36px;padding:8px 11px;border:1px solid transparent;border-radius:7px;font-size:11px;color:#566e48}.home-display-group.home-display-icons button{width:40px;height:40px;min-height:40px;padding:8px;border-color:#d8e3ce;background:#fff}.home-display-icons button:hover{background:#e6f0dc;border-color:#aac294}.home-display-icons button svg{display:block;flex-shrink:0}.home-display-group button[aria-pressed=true]{background:#19744f;color:#fff;border-color:#19744f}.home-display-group button:disabled{opacity:.4;cursor:default}.home-display-group button:focus-visible{outline:2px solid #19744f;outline-offset:3px}.start-page[data-home-view=tiles]{--home-columns:4;--home-image-height:170px;--home-gap:18px}.start-page[data-tile-size=small]{--home-columns:5;--home-image-height:125px;--home-gap:13px}.start-page[data-tile-size=large]{--home-columns:3;--home-image-height:225px;--home-gap:24px}.start-page[data-home-view=tiles] :is(.place-grid,.home-route-grid,.trail-grid){display:grid;grid-template-columns:repeat(var(--home-columns),minmax(0,1fr));gap:var(--home-gap)}.start-page[data-home-view=tiles] :is(.place-image,.home-route-card>img,.trail-image){height:var(--home-image-height)}.start-page[data-home-view=tiles] .trail-card{display:block}.start-page[data-home-view=tiles] :is(.place-card,.home-route-card,.trail-card){min-width:0}.start-page[data-tile-size=small] :is(.place-title,.home-route-card-body>strong,.trail-info h3){font-size:12px;overflow-wrap:anywhere}.start-page[data-tile-size=small] :is(.home-route-card-body,.trail-info){padding:12px}.start-page[data-tile-size=small] .trail-meta{flex-wrap:wrap;gap:7px}.start-page[data-tile-size=small] .trail-arrow{display:none}.start-page[data-tile-size=small] .home-route-description{-webkit-line-clamp:2}.start-page[data-home-view=list] :is(.place-grid,.home-route-grid,.trail-grid){display:grid;grid-template-columns:minmax(0,1fr);gap:12px}.start-page[data-home-view=list] :is(.place-card,.home-route-card,.trail-card){display:grid;grid-template-columns:155px minmax(0,1fr);align-items:stretch;gap:0;text-align:left;min-width:0;overflow:hidden;border:1px solid #e1e8d9;border-radius:10px;background:#fff}.start-page[data-home-view=list] :is(.place-image,.home-route-card>img,.trail-image){width:155px;height:145px;border-radius:0;align-self:stretch;object-fit:cover}.start-page[data-home-view=list] .place-info{padding:16px 48px 14px 18px;min-width:0;align-self:center}.start-page[data-home-view=list] .place-title{overflow-wrap:anywhere}.start-page[data-home-view=list] .place-social{margin-top:9px}.start-page[data-home-view=list] .card-arrow{right:16px;top:auto;bottom:15px}.start-page[data-home-view=list] .home-route-card-body{padding:15px 18px;gap:6px}.start-page[data-home-view=list] .home-route-description{-webkit-line-clamp:2}.start-page[data-home-view=list] .trail-info{padding:20px 40px 18px 20px;align-self:center}.start-page[data-home-view=list] .trail-meta{flex-wrap:wrap}.start-page[data-home-view=list] .trail-arrow{display:none}
@media(max-width:1100px){.start-page[data-home-view=tiles]{--home-columns:3}.start-page[data-tile-size=small]{--home-columns:4}.start-page[data-tile-size=large]{--home-columns:2}}
@media(max-width:700px){.home-display-toolbar{justify-content:flex-start;gap:8px 16px;padding:10px;margin-top:18px}.start-page[data-home-view=tiles]{--home-columns:2;--home-image-height:145px;--home-gap:13px}.start-page[data-tile-size=small]{--home-columns:3;--home-image-height:95px;--home-gap:9px}.start-page[data-tile-size=large]{--home-columns:1;--home-image-height:230px}.start-page[data-tile-size=small] .place-info{padding-right:0}.start-page[data-tile-size=small] .card-arrow{display:none}.start-page[data-tile-size=small] .place-social{gap:7px}.start-page[data-tile-size=small] .place-tag{font-size:7px;max-width:85%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.start-page[data-tile-size=small] .top-place-position{min-width:22px;height:22px;font-size:9px}.start-page[data-tile-size=small] .home-route-card-body>small{flex-wrap:wrap}.start-page[data-tile-size=small] .home-route-open{font-size:10px;gap:4px}}
@media(max-width:480px){.start-page[data-tile-size=small]{--home-columns:2;--home-image-height:105px}.start-page[data-home-view=list] :is(.place-card,.home-route-card,.trail-card){grid-template-columns:100px minmax(0,1fr)}.start-page[data-home-view=list] :is(.place-image,.home-route-card>img,.trail-image){width:100px;height:145px}.start-page[data-home-view=list] .place-info{padding:12px 30px 12px 12px}.start-page[data-home-view=list] :is(.home-route-card-body,.trail-info){padding:12px}.start-page[data-home-view=list] .home-route-card-body>strong{font-size:13px}.start-page[data-home-view=list] .home-route-card-body>small{flex-wrap:wrap}.home-display-group button{padding:7px 9px}}
</style>

<style>
.hero-tabs{display:flex;gap:6px;margin:-7px 0 25px;padding:0 0 5px;border-bottom:1px solid #b9cbb0}.hero-tabs button{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;flex:1;min-width:0;min-height:70px;padding:10px 4px 13px;background:transparent;border-radius:10px 10px 0 0;color:#6a8067;font-size:10px;line-height:1.4;font-weight:600;transition:background .18s,color .18s}.hero-tabs button:hover{background:#edf4e68c;color:#19744f}.hero-tabs button[aria-selected=true]{color:#14613f;background:linear-gradient(0deg,#e2efceaa,transparent)}.hero-tabs button[aria-selected=true]:after{content:'';position:absolute;bottom:-6px;left:12px;right:12px;height:3px;border-radius:3px;background:#19744f}.hero-tabs button[aria-selected=true] svg{stroke-width:2.3}.hero-address-panel .home-address-search{margin:0;padding:8px 0 12px;border:0}.hero-address-panel .home-address-search h3{font-size:25px;letter-spacing:-.6px}.hero-address-panel .home-address-search h3>svg{display:none}.hero-address-panel .home-address-search>p{font-size:12px;margin:12px 0 22px}.hero-address-panel{min-height:250px}.hero-tabs button:focus-visible,.hero-category-grid button:focus-visible{outline:2px solid #19744f;outline-offset:3px}.hero-map-panel .poland-regions{display:block;margin:0;padding:0;border:0;background:transparent}.hero-map-panel .poland-intro{display:none}.hero-map-panel .poland-map{max-height:460px}.hero-map-panel .poland-region-list{margin-top:8px}.hero-map-panel .poland-region-rows{grid-template-columns:1fr}.hero-categories-panel h2{margin-bottom:18px}.hero-category-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.hero-category-grid button{display:flex;flex-direction:column;gap:10px;padding:14px 11px;background:#f6f9f0;border:1px solid #d5e2ca;border-radius:10px;text-align:left;color:#28573c;min-height:85px}.hero-category-grid button:hover{background:#e5efd9;border-color:#9fbd88}.hero-category-grid strong{font-size:12px;line-height:1.5}.hero-category-grid span{display:flex;align-items:center;justify-content:space-between;gap:5px;font-size:10px;color:#728468}@media(max-width:520px){.hero-category-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-tabs button{font-size:11px}}
</style>

<style>.hero-category-grid button:disabled{opacity:.5;cursor:default}</style>

<style>.trip-type-tabs{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 24px}.trip-type-tabs button{display:flex;align-items:center;gap:8px;padding:11px 16px;border:1px solid #d3dfc8;border-radius:9px;background:#fff;color:#42683c;font-size:12px}.trip-type-tabs button[aria-pressed=true]{color:white;background:#19744f;border-color:#19744f}.trip-type-tabs button:focus-visible{outline:2px solid #19744f;outline-offset:3px}</style>

<style>.planner-nav-count{display:inline-block;font-size:11px;font-weight:600;animation:planner-count-change .32s ease-out;transform-origin:center}@keyframes planner-count-change{0%{transform:scale(.88);opacity:.4}55%{transform:scale(1.1);opacity:1}100%{transform:scale(1)}}@media(prefers-reduced-motion:reduce){.planner-nav-count{animation:none}}</style>

<style>
.site-header .main-navigation button[data-nav-label=Planer]{position:relative}.site-header .main-navigation button.planner-just-added{color:#105a3a;background:#e4f1d3;border-radius:7px;box-shadow:0 0 0 7px #e4f1d3}.planner-added-bubble{position:absolute;top:calc(100% + 18px);left:50%;transform:translateX(-50%);z-index:100;display:flex;align-items:center;gap:6px;white-space:nowrap;padding:10px 13px;border:1px solid #236d42;border-radius:10px;background:#19744f;color:#fff;font-size:11px;font-weight:600;box-shadow:0 5px 18px #173d2929;pointer-events:none;animation:planner-bubble-in .24s ease-out}.planner-added-bubble:before{content:'';position:absolute;top:-5px;left:calc(50% - 5px);width:8px;height:8px;transform:rotate(45deg);background:#19744f;border-left:1px solid #236d42;border-top:1px solid #236d42}@keyframes planner-bubble-in{from{opacity:0;translate:0 -6px;scale:.94}to{opacity:1;translate:0 0;scale:1}}@media(prefers-reduced-motion:reduce){.planner-added-bubble{animation:none}}
</style>

<style>
.modal.planner-place-modal{width:420px;max-width:calc(100vw - 24px);max-height:70dvh;overflow:auto;border-radius:16px}.planner-place-preview{padding:22px}.planner-preview-heading{display:flex;gap:14px;align-items:center;padding-right:24px}.planner-preview-heading>img{width:88px;height:80px;object-fit:cover;border-radius:10px;flex-shrink:0}.planner-preview-heading>div{min-width:0}.planner-preview-heading span{font-size:10px;color:#7c8c72}.planner-preview-heading h2{font-size:17px;line-height:1.4;letter-spacing:-.3px;color:#204b33;overflow-wrap:anywhere;margin:5px 0 0}.planner-preview-description{font-size:12px;line-height:1.7;color:#657b5a;margin:17px 0}.planner-place-preview .detail-actions{margin:0}.planner-place-preview .button{min-height:44px;font-size:12px}.planner-preview-more{display:flex;gap:6px;align-items:center;margin:13px auto 0;color:#19744f;font-size:11px;min-height:32px}.planner-place-modal .modal-close{top:8px;right:8px;width:32px;height:32px}@media(max-width:600px){.modal-overlay.planner-preview-overlay{align-items:flex-end;padding:12px 12px max(12px,env(safe-area-inset-bottom))}.modal.planner-place-modal{width:100%;max-width:420px;margin:0 auto;max-height:70dvh}.planner-place-preview{padding:19px}.planner-preview-heading>img{width:76px;height:72px}.planner-preview-heading h2{font-size:16px}}
</style>

<style>.trip-card-metrics{display:flex;align-items:center;gap:15px;flex-wrap:wrap;font-size:13px;font-weight:700;color:#19744f}.trip-card-metrics>span{display:flex;align-items:center;gap:6px}.trip-card-metrics>small{font-size:9px;font-weight:400;color:#839176}.trip-metrics-pending{font-size:10px;font-weight:400;color:#839176}.trip-metrics-retry{font-size:10px;color:#19744f;text-decoration:underline;padding:8px;flex-shrink:0}@media(max-width:700px){.trip-card-metrics{font-size:12px;gap:9px}.trip-card-metrics>small{width:100%}.trip-metrics-retry{margin-left:auto}}</style>

<style>.trip-library-view{display:flex;justify-content:flex-end;gap:4px;margin:0 0 17px}.trip-library-view button{display:flex;gap:7px;align-items:center;padding:9px 13px;font-size:11px;color:#69805a;border:1px solid #d6e1cc;background:#fff;border-radius:7px}.trip-library-view button[aria-pressed=true]{background:#19744f;border-color:#19744f;color:#fff}.trip-navigation-start{display:flex;align-items:center;justify-content:center;gap:7px;min-height:42px;padding:10px 13px;border:1px solid #c8dcbc;border-radius:8px;background:#edf5e5;color:#19744f;font-size:11px;flex-shrink:0}.trip-library-tiles{grid-template-columns:repeat(3,minmax(0,1fr));align-items:stretch}.trip-library-tiles .route-library-item{flex-wrap:wrap;align-content:flex-start;gap:10px;padding:12px;min-width:0}.trip-library-tiles .route-library-open{flex-basis:100%;width:100%;display:flex;flex-direction:column;align-items:stretch;gap:14px}.trip-library-tiles .route-library-open>img{width:100%;height:170px}.trip-library-tiles .route-library-info>strong{font-size:15px}.trip-library-tiles .route-library-open>svg{display:none}.trip-library-tiles .route-library-info>small{flex-wrap:wrap}.trip-library-tiles .trip-navigation-start{margin-top:auto;flex:1}.trip-library-tiles .route-library-delete{margin-left:auto}@media(max-width:1050px){.trip-library-tiles{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:650px){.trip-library-tiles{grid-template-columns:1fr}.trip-library-tiles .route-library-open>img{height:180px}.trip-library-view{justify-content:flex-start}.route-library-item{flex-wrap:wrap}.route-library-open{flex-basis:100%;width:100%}}
</style>

<style>.route-library-copy{display:flex;align-items:center;justify-content:center;gap:6px;min-height:40px;padding:10px;color:#19744f;border:1px solid #d5e2cb;border-radius:7px;font-size:11px;flex-shrink:0}.route-library-copy:disabled{opacity:.5;cursor:wait}</style>

<style>.place-navigation-choice{padding:28px 23px 23px}.place-navigation-choice h2{font-size:22px;color:#245039;line-height:1.4;padding-right:22px}.place-navigation-choice>p{font-size:12px;line-height:1.7;color:#718568;margin:12px 0 18px}.place-navigation-choice>.button{min-height:48px;margin-top:10px;font-size:13px}.place-navigation-modes{display:flex;gap:8px;margin-bottom:20px}.place-navigation-modes button{display:flex;align-items:center;gap:7px;justify-content:center;flex:1;padding:10px;border:1px solid #d3dfc8;border-radius:8px;font-size:12px;color:#527448}.place-navigation-modes button[aria-pressed=true]{background:#e5f0d8;border-color:#8cac75;color:#19744f}.place-navigation-choice .button:focus-visible{outline:2px solid #19744f;outline-offset:3px}.detail-actions{flex-wrap:wrap}</style>

<style>.footer-brand-mark{width:34px;height:30px;flex-shrink:0}@media(max-width:720px){.site-header .brand-name{display:none}.site-header .brand{gap:0;flex-shrink:0}.site-header .brand-mark{width:50px;height:48px}}</style>

<style>
@media(max-width:720px){
 .site-header.responsive-header{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:5px 12px;height:auto;min-height:108px;padding:7px 12px 0;position:relative}
 .site-header.responsive-header .brand{grid-column:1;grid-row:1;justify-self:start}
 .site-header.responsive-header .brand-mark{width:44px;height:42px}
 .site-header.responsive-header .header-actions{grid-column:2;grid-row:1;justify-self:end;margin:0;gap:0}
 .site-header.responsive-header .header-actions .login-btn{display:inline-flex;min-height:36px;max-width:190px;overflow:hidden;white-space:nowrap;padding:8px 12px;font-size:11px}
 .site-header.responsive-header .search-nav,.site-header.responsive-header .favorites-nav,.site-header.responsive-header .header-actions .pwa-controls .pwa-install,.site-header.responsive-header .mobile-menu{display:none}
 .site-header.responsive-header .pwa-controls{display:contents}
 .site-header.responsive-header .pwa-messages{top:auto;bottom:16px;left:12px;right:12px;width:auto;max-width:none}
 .site-header.responsive-header .main-navigation,.site-header.responsive-header .main-navigation.open{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));grid-column:1/-1;grid-row:2;position:static;width:100%;height:auto;gap:0;padding:0;background:transparent;box-shadow:none;align-items:stretch}
 .site-header.responsive-header .main-navigation button,.site-header.responsive-header .main-navigation.open button{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;min-width:0;min-height:54px;height:auto;padding:7px 2px 9px;font-size:11px;line-height:1.2;text-align:center}
 .site-header.responsive-header .main-navigation button>svg{width:18px;height:18px}
 .site-header.responsive-header .main-navigation button.active:after{display:block;bottom:0;left:8px;right:8px;height:3px}
 .site-header.responsive-header .main-navigation button:nth-child(n+5){grid-column:1/-1;flex-direction:row;min-height:36px}
 .site-header.responsive-header .planner-nav-count{position:absolute;top:3px;right:calc(50% - 24px);width:16px;height:16px;font-size:0;line-height:0}
 .site-header.responsive-header .planner-nav-count:after{content:attr(data-count);display:block;width:16px;height:16px;border-radius:50%;background:#e4f0d6;color:#19744f;font-size:9px;line-height:16px;text-align:center}
 .site-header.responsive-header .planner-added-bubble{top:calc(100% + 8px)}
}
</style>

<style>.brand-mark,.footer-brand-mark{object-fit:contain}</style>
