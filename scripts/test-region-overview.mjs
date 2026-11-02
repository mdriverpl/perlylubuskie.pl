import assert from 'node:assert/strict'
import {regionAtPoint,regionOverview} from '../src/regionOverview.js'
import contours from '../src/catalog/poland-regions.json' with {type:'json'}
import {provinceSlug} from '../src/explore.js'
assert.equal(provinceSlug('  województwo ŁÓDZKIE  '),'lodzkie')
assert.equal(provinceSlug('Kujawsko pomorskie'),'kujawsko-pomorskie')
assert.equal(provinceSlug('woj. warmińsko-mazurskie'),'warminsko-mazurskie')
assert.equal(provinceSlug('Łódź'),null,'A city must not be mistaken for a province')
assert.equal(provinceSlug('Śląska 20, Poznań'),null)
const capitals=[['dolnoslaskie',51.107,17.038],['kujawsko-pomorskie',53.01,18.6],['lubelskie',51.247,22.566],['lubuskie',52.732,15.237],['lodzkie',51.759,19.456],['malopolskie',50.061,19.938],['mazowieckie',52.23,21.01],['opolskie',50.675,17.922],['podkarpackie',50.041,21.999],['podlaskie',53.132,23.168],['pomorskie',54.352,18.646],['slaskie',50.259,19.021],['swietokrzyskie',50.866,20.628],['warminsko-mazurskie',53.778,20.481],['wielkopolskie',52.407,16.925],['zachodniopomorskie',53.429,14.553]]
assert.equal(contours.length,16);assert.equal(new Set(contours.map(r=>r.slug)).size,16)
for(const [slug,lat,lng] of capitals)assert.equal(regionAtPoint({lat,lng}),slug)
for(const point of [null,{lat:NaN,lng:18},{lat:0,lng:0},{lat:52,lng:13.4}])assert.equal(regionAtPoint(point),null)
const regions=[{slug:'lubuskie',place_count:351,active:true},{slug:'dolnoslaskie',place_count:506,active:true},{slug:'kujawsko-pomorskie',place_count:255,active:false}]
const places=[{id:1,region:'lubuskie'},{id:2,region:'dolnoslaskie'},{id:3,region:'lubuskie'}]
const routes=[{id:1,is_public:true,transport:'walk',place_ids:[1,3,2]},{id:2,is_public:true,transport:'bike',place_ids:[1,1]},{id:3,is_public:false,transport:'walk',place_ids:[1]},{id:4,is_public:true,transport:'car',place_ids:[1]},{id:5,is_public:true,transport:'walk',place_ids:[-1],custom_points:[{id:-1,lat:53.01,lng:18.6}]},{id:6,is_public:true,transport:'bike',place_ids:[1],point_positions:[{id:1,lat:52.23,lng:21.01}]},{id:7,is_public:true,transport:'walk',place_ids:[99999]},{id:8,transport:'walk',place_ids:[1]},{id:1,is_public:true,transport:'walk',place_ids:[1]}]
const overview=regionOverview(regions,places,routes);const bySlug=Object.fromEntries(overview.map(r=>[r.slug,r]))
assert.equal(bySlug.lubuskie.places,351);assert.equal(bySlug.dolnoslaskie.places,506);assert.equal(bySlug['kujawsko-pomorskie'].places,0,'Draft place counts are never public')
assert.equal(bySlug.lubuskie.walking,1,'Repeated stops and duplicate route IDs count once')
assert.equal(bySlug.dolnoslaskie.walking,1,'A cross-region route counts in both regions')
assert.equal(bySlug.lubuskie.cycling,1);assert.equal(bySlug.mazowieckie.cycling,1,'Moved route points use their actual coordinates')
assert.equal(bySlug['kujawsko-pomorskie'].walking,1,'Public custom route points can lie in a region without a published catalog')
assert.equal(regionOverview([{slug:'lubuskie',active:true}],[{id:1},{id:-1,details:{kind:'custom'}}],[]).find(r=>r.slug==='lubuskie').places,1)
console.log('PASS: all 16 geographic regions, real place totals, no draft/private/car counts, route deduplication, cross-region/custom/moved points and legacy fallback')
