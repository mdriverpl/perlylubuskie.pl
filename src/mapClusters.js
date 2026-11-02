import Supercluster from 'supercluster'
export function validMapPoint(point){return Number.isFinite(point?.lat)&&Math.abs(point.lat)<=85.051129&&Number.isFinite(point?.lng)&&Math.abs(point.lng)<=180}
export function pointClusters(places,selected=[]){
 const chosen=new Set(selected)
 return new Supercluster({radius:55,maxZoom:16}).load(places.filter(p=>validMapPoint(p)&&!chosen.has(p.id)&&p.details?.kind!=='custom').map(p=>({type:'Feature',id:p.id,geometry:{type:'Point',coordinates:[p.lng,p.lat]},properties:{placeId:p.id}})))
}
