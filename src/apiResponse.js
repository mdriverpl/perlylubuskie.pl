export async function readApiJson(response,message='Serwer jest chwilowo niedostępny. Spróbuj ponownie.'){
 if(response.ok&&response.status===204)return null
 let data
 try{data=await response.json()}
 catch(error){
  if(error.name==='AbortError'||error.name==='TimeoutError')throw error
  throw new Error(message)
 }
 if(!response.ok)throw new Error(typeof data?.detail==='string'?data.detail:message)
 if(data===null||typeof data!=='object')throw new Error(message)
 return data
}
