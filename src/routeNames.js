export function shortRouteName(points){
 return points[0]?.name?.trim().slice(0,120)||'Moja trasa'
}
