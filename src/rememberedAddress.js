const key='perly:search-address'

export function readAddress(){
 try{
  const value=JSON.parse(localStorage.getItem(key))
  const point=value?.location
  if(typeof value?.query!=='string'||value.query.length>200||typeof point?.name!=='string'||point.name.length>500||!Number.isFinite(point.lat)||Math.abs(point.lat)>90||!Number.isFinite(point.lng)||Math.abs(point.lng)>180)return null
  return value
 }catch{return null}
}

export function rememberAddress(query,location){
 try{localStorage.setItem(key,JSON.stringify({query:query.slice(0,200),location:{id:location.id,name:location.name,lat:location.lat,lng:location.lng}}))}catch{}
}

export function forgetAddress(){try{localStorage.removeItem(key)}catch{}}
