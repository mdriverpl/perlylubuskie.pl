export function sanitizeCustomPoints(value){
 if(!Array.isArray(value))return []
 const found=new Set()
 return value.filter(p=>p&&Number.isSafeInteger(p.id)&&p.id<0&&!found.has(p.id)&&found.add(p.id)&&typeof p.name==='string'&&p.name.trim()&&Number.isFinite(p.lat)&&p.lat>=-90&&p.lat<=90&&Number.isFinite(p.lng)&&p.lng>=-180&&p.lng<=180).slice(0,100).map(p=>({id:p.id,name:p.name.trim().slice(0,80),subtitle:'Punkt pomocniczy trasy',category:'custom',image:'/images/custom-point.svg',lat:p.lat,lng:p.lng,rating:0,location:'Punkt trasy',description:'Punkt pomocniczy należący wyłącznie do tej trasy.',details:{kind:'custom'}}))
}
