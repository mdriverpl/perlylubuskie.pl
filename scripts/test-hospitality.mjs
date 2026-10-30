import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import {places} from '../src/data.js'
import {filterPlaces} from '../src/explore.js'
const records=JSON.parse(await fs.readFile('data/hospitality/source-records.json','utf8'))
const generated=JSON.parse(await fs.readFile('src/catalog/hospitality.json','utf8'))
const coverage=JSON.parse(await fs.readFile('data/hospitality/coverage.json','utf8'))
assert.deepEqual(generated,records)
assert.deepEqual(JSON.parse(await fs.readFile('backend/seed.json','utf8')),places)
assert.equal(places.length,351)
assert.equal(new Set(places.map(p=>p.id)).size,places.length)
assert.equal(coverage.registry_mapping.length,108)
assert.equal(new Set(coverage.registry_mapping.map(r=>r.row)).size,108)
assert.equal(new Set(coverage.registry_mapping.map(r=>r.place_id)).size,106)
assert.equal(records.filter(p=>p.id!==1).length,133)
for(const row of coverage.registry_mapping)assert.ok(records.find(p=>p.id===row.place_id)?.details.address)
for(const p of records){
 assert.equal(p.location,'Łagów')
 assert.ok(p.lat>52.318&&p.lat<52.35&&p.lng>15.263&&p.lng<15.319,p.name)
 assert.ok(p.details.sources.length&&p.details.sources.every(s=>/^https?:\/\//.test(s.url)),p.name)
 assert.ok(['address','street','poi',undefined].includes(p.details.coordinate_accuracy))
 if(p.details.coordinate_accuracy==='street'){
  assert.match(p.details.visit_note,/przybliżona do ulicy/)
  assert.ok(p.details.address)
 }
 if(p.id!==1){assert.equal(p.rating,0);await fs.access('public'+p.image)}
}
const stay=filterPlaces(places,'Lubuskie','Łagów',['stays'])
const food=filterPlaces(places,'Lubuskie','Łagów',['restaurants'])
assert.equal(stay.length,115)
assert.equal(food.length,24)
for(const name of ['Laura Spa','Pensjonat SAGE','Leśnik','Na Skarpie']){
 const p=records.find(p=>p.name===name);assert.ok(stay.some(s=>s.id===p.id));assert.ok(food.some(s=>s.id===p.id))
}
assert.ok(stay.some(p=>p.id===1)&&food.some(p=>p.id===1))
assert.ok(!food.some(p=>p.id===4),'Culinary inspiration is not a real restaurant')
assert.equal(places.find(p=>p.id===1).details.kind,'castle')
assert.equal(places.find(p=>p.id===1).image,'/images/heritage/q16618861.webp')
assert.equal(filterPlaces(places,'Lubuskie','Restauracja Laura',[]).length,1)
assert.equal(filterPlaces(places,'Lubuskie','Chopina 20N/3',[]).length,1)
assert.equal(records.filter(p=>p.details.aliases.some(a=>a==='Forte Studio')).length,1)
console.log('PASS: 133 new Łagów services, 108 registry rows accounted for, deduplication, multi-role filters, address/alias search, marked approximate positions, stable IDs and seed parity')
