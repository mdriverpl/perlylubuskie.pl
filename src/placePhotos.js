import {readApiJson} from './apiResponse.js'
const uploaded=new WeakMap()
export async function uploadPlacePhotos(files,token){
 const ids=[]
 for(const file of files){
  const cached=uploaded.get(file)
  if(cached?.token===token){ids.push(cached.id);continue}
  const response=await fetch('/api/place-photos',{method:'POST',body:file,headers:{Authorization:`Bearer ${token}`,'Content-Type':file.type||'application/octet-stream'},signal:AbortSignal.timeout(60000)})
  const data=await readApiJson(response,'Nie udało się przesłać zdjęcia. Spróbuj ponownie.')
  uploaded.set(file,{token,id:data.id});ids.push(data.id)
 }
 return ids
}
