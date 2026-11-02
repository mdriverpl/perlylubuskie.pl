import assert from 'node:assert/strict'
import {pointClusters} from '../src/mapClusters.js'
const points=[...Array.from({length:30},(_,i)=>({id:i+1,name:'A '+i,lat:52.33+i*.00001,lng:15.29})),{id:100,name:'Toruń',lat:53.01,lng:18.6},{id:-1,name:'Własny punkt',lat:52.33,lng:15.29,details:{kind:'custom'}},{id:200,name:'Błędny punkt',lat:NaN,lng:15}]
const original=JSON.stringify(points)
const index=pointClusters(points,[1,2,-1])
const clusters=index.getClusters([-180,-85,180,85],8)
const group=clusters.find(p=>p.properties.cluster)
assert.equal(group.properties.point_count,28)
assert.equal(clusters.some(p=>p.properties.placeId===100),true)
const leaves=index.getLeaves(group.properties.cluster_id,Infinity)
assert.equal(leaves.length,28)
assert.equal(leaves.some(p=>[1,2,-1,200].includes(p.properties.placeId)),false,'Selected, custom and invalid points never join clusters')
assert.ok(index.getClusterExpansionZoom(group.properties.cluster_id)>8)
assert.equal(JSON.stringify(points),original,'Clustering never changes catalog or route order')
assert.deepEqual(pointClusters([]).getClusters([-180,-85,180,85],8),[])
console.log('PASS: geographic clustering, count, expansion, leaves, selected/custom exclusions and immutable catalog')
