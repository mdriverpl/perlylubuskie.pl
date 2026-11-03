export const osmTileUrl='https://tile.openstreetmap.org/{z}/{x}/{y}.png'
export function preferredMap(){try{return window.localStorage.getItem('perly:map-provider')==='here'?'here':'osm'}catch{return 'osm'}}
export function rememberMap(provider){try{window.localStorage.setItem('perly:map-provider',provider)}catch{}}
export function preferredOsmTone(){try{return window.localStorage.getItem('perly:osm-tone')==='standard'?'standard':'light'}catch{return 'light'}}
export function rememberOsmTone(tone){try{window.localStorage.setItem('perly:osm-tone',tone)}catch{}window.dispatchEvent(new Event('perly:osm-tone-changed'))}
