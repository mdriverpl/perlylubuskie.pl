export function routeShareLinks(plan, points){
 const available=points.filter(p=>Number.isFinite(p.lat)&&Number.isFinite(p.lng))
 if(!plan||available.length<2)return null
 const coordinate=p=>`${p.lat},${p.lng}`
 const map=new URL('https://www.google.com/maps/dir/')
 map.searchParams.set('api','1')
 map.searchParams.set('origin',coordinate(available[0]))
 map.searchParams.set('destination',coordinate(available.at(-1)))
 map.searchParams.set('travelmode',plan.transport==='bike'?'bicycling':'walking')
 if(available.length>2)map.searchParams.set('waypoints',available.slice(1,-1).map(coordinate).join('|'))
 const distance=(plan.distance_m/1000).toLocaleString('pl-PL',{maximumFractionDigits:1})
 const text=[plan.name,`${plan.transport==='bike'?'Rowerem':'Pieszo'} · ${distance} km`,plan.description||'',...available.map((p,i)=>`${i+1}. ${p.name}`),...(plan.warnings||[]),'Punkty trasy w Google Maps (przebieg może się różnić):',map.href].filter(Boolean).join('\n')
 return {sms:`sms:?body=${encodeURIComponent(text)}`,email:`mailto:?subject=${encodeURIComponent(plan.name)}&body=${encodeURIComponent(text)}`}
}
