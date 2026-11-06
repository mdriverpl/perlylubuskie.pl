export function personTransport(value){return value==='bike'?'bike':'walk'}
export function personMarkerHtml(value,{directional=false}={}){
 const bike=personTransport(value)==='bike'
 const symbol=bike?'<circle cx="5.5" cy="17.5" r="3.5"/><circle cx="18.5" cy="17.5" r="3.5"/><path d="m15 6-4 5 5 3 2.5 3.5M11 11l-4 6.5M10 4h3l2 2h4"/>':'<circle cx="13" cy="4" r="2"/><path d="m7 21 3-6m6 6-3-7 1-6m-6 5 3-5 3 1 4 4"/>'
 return `<span class="map-person-symbol" data-transport="${bike?'bike':'walk'}"><svg class="map-travel-symbol" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="${bike?'Rower':'Pieszo'}">${symbol}</svg><span class="gps-exact-cross" aria-label="Dokładna pozycja"></span>${directional?'<svg class="gps-direction-pointer" width="10" height="12" viewBox="0 0 10 12" aria-hidden="true"><path d="M5 1 9 10 5 8 1 10 Z" fill="#1876d2" stroke="white" stroke-width="1"/></svg>':''}</span>`
}
