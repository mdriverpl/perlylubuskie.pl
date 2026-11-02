export const osmTileUrl='https://tile.openstreetmap.org/{z}/{x}/{y}.png'
export function preferredMap(){try{return window.localStorage.getItem('perly:map-provider')==='here'?'here':'osm'}catch{return 'osm'}}
export function rememberMap(provider){try{window.localStorage.setItem('perly:map-provider',provider)}catch{}}
