export const placeFacets = [
 { id:'castles', name:'Zamki', icon:'castle', match:p=>p.category==='heritage'&&/zamek|zamki|castle/i.test(`${p.name} ${p.subtitle}`) },
 { id:'restaurants', name:'Restauracje', icon:'utensils', match:p=>p.category==='food' },
 { id:'lakes', name:'Jeziora', icon:'waves', match:p=>p.category==='nature'&&/jezior/i.test(`${p.name} ${p.subtitle}`) },
 { id:'nature', name:'Parki i przyroda', icon:'trees', match:p=>p.category==='nature'||/park/i.test(p.name) },
 { id:'history', name:'Zabytki i historia', icon:'landmark', match:p=>p.category==='heritage' },
 { id:'stays', name:'Noclegi', icon:'bed', match:p=>p.category==='stay' },
]
export function normalizeRegion(value){return value.trim().toLocaleLowerCase('pl').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ł/g,'l').replace(/^woj(?:ewodztwo)?\.?\s*/,'').trim()}
export function matchesRegion(value){return ['lubuskie','ziemia lubuska'].includes(normalizeRegion(value))}
export function filterPlaces(places,region,query,facets){
 if(!matchesRegion(region))return []
 const needle=query.trim().toLocaleLowerCase('pl')
 return places.filter(p=>(!needle||`${p.name} ${p.subtitle} ${p.location}`.toLocaleLowerCase('pl').includes(needle))&&(!facets.length||placeFacets.some(f=>facets.includes(f.id)&&f.match(p))))
}
