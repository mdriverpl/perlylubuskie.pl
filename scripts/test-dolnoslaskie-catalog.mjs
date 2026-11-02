import assert from 'node:assert/strict'
import {readFile,stat} from 'node:fs/promises'
import sharp from 'sharp'
const catalog=JSON.parse(await readFile('backend/region-catalogs/dolnoslaskie.json','utf8'))
assert.equal(catalog.region,'dolnoslaskie');assert.equal(catalog.coverage.complete_official_register,false)
assert.ok(catalog.places.length>=500)
const keys=new Set(),kinds=new Set(),images=new Set();let photos=0
for(const p of catalog.places){
 assert.equal(p.region,catalog.region);assert.match(p.research_key,/^wd:Q[1-9]\d*$/);assert.ok(!keys.has(p.research_key));keys.add(p.research_key)
 assert.equal(p.details.wikidata,p.research_key.slice(3));assert.ok(p.name&&p.description&&p.location)
 assert.ok(p.description.length<=2000&&p.name.length<=200&&p.subtitle.length<=250)
 assert.ok(p.lat>=49.8&&p.lat<=52&&p.lng>=14.7&&p.lng<=18)
 assert.ok(['castle','palace','lake','nature','heritage','leisure'].includes(p.details.kind));kinds.add(p.details.kind)
 assert.ok(p.details.sources.length>=2&&p.details.sources.every(s=>s.url.startsWith('https://')))
 assert.equal(p.details.coordinate_source,'https://www.wikidata.org/wiki/'+p.details.wikidata)
 assert.equal(p.details.coordinate_license,'Wikidata CC0 1.0')
 const photo=p.details.photo
 if(photo){
  photos++;assert.ok(photo.author);assert.match(photo.license,/^(CC BY(?:-SA)? \d|CC0|Public domain|PD\b)/i)
  assert.ok(photo.license_url.startsWith('https://'));assert.ok(photo.source_url.startsWith('https://commons.wikimedia.org/'))
  assert.match(p.image,/^\/images\/dolnoslaskie\/[a-f0-9]{64}\.webp$/);images.add(p.image)
 }else assert.equal(p.image,'/images/heritage-placeholder.svg')
}
assert.equal(kinds.size,6);assert.equal(photos,catalog.coverage.photos)
for(const path of images){const file='public'+path;assert.ok((await stat(file)).size>0);const meta=await sharp(file).metadata();assert.equal(meta.format,'webp');assert.ok(meta.width<=1280&&meta.height<=1280)}
const credits=await readFile('public/dolnoslaskie-credits.html','utf8');assert.ok(credits.includes(String(keys.size)))
assert.ok((await readFile('public/heritage-credits.html','utf8')).includes('/dolnoslaskie-credits.html'))
console.log(`PASS: ${keys.size} sourced Dolnośląskie places, six categories, unique identities, coordinates, ${photos} licensed photos and credit page`)
