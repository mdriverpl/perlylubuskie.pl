import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import {places} from '../src/data.js'
import {filterPlaces} from '../src/explore.js'
const lagow=JSON.parse(await fs.readFile('src/catalog/lagow.json','utf8'))
const records=JSON.parse(await fs.readFile('data/lagow/source-records.json','utf8'))
const seed=JSON.parse(await fs.readFile('backend/seed.json','utf8'))
assert.deepEqual(lagow,records)
assert.deepEqual(seed,places)
assert.equal(places.length,351)
assert.equal(new Set(places.map(p=>p.id)).size,351)
assert.equal(lagow.filter(p=>p.id!==5).length,8)
assert.equal(places.filter(p=>p.id===1).length,1)
assert.equal(places.filter(p=>p.id===5).length,1)
assert.equal(filterPlaces(places,'Lubuskie','Ciecz',[]).find(p=>p.id===5).name,'Jezioro Trześniowskie')
assert.deepEqual(filterPlaces(places,'Lubuskie','',['family']).map(p=>p.id),[910005,910008])
assert.ok(filterPlaces(places,'Lubuskie','Łagów',['history']).some(p=>p.id===910002))
assert.equal(places.find(p=>p.id===910005).location,'Kownaty')
assert.equal(places.find(p=>p.id===910008).location,'Mostki')
for(const place of lagow){
 assert.ok(Number.isFinite(place.lat)&&Number.isFinite(place.lng))
 assert.ok(place.lat>52.2&&place.lat<52.4&&place.lng>15&&place.lng<15.4)
 assert.ok(place.description.length>20&&place.description.length<300)
 assert.ok(place.details.sources.some(s=>s.url==='https://www.polskieszlaki.pl/lagow-atrakcje/'))
 assert.ok(place.details.coordinate_source.startsWith('https://www.openstreetmap.org/'))
 assert.ok(place.details.sources.every(s=>new URL(s.url).protocol==='https:'))
 assert.equal(place.details.kind==='custom',false)
 await fs.access('public'+place.image)
}
assert.match(places.find(p=>p.id===910006).details.visit_note,/tablicę/)
assert.match(places.find(p=>p.id===910004).details.visit_note,/poligon/)
console.log('PASS: 8 sourced Łagów attractions, stable existing IDs, lake alias, correct nearby towns, family filter, coordinates, sources, placeholders and seed parity')
