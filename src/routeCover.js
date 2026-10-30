import * as L from 'leaflet/dist/leaflet-src.esm.js'

// Render a separate map so creating the cover never changes the user's viewport.
export async function createRouteCover({points,geometry,transport}){
 if(!points.length)throw new Error('Dodaj punkty, aby utworzyć zdjęcie trasy.')
 const request=async(url,options={})=>{
  const response=await fetch(url,{signal:AbortSignal.timeout(45000),...options})
  const data=await response.json()
  if(!response.ok)throw new Error(data.detail||'Nie udało się przygotować zdjęcia trasy.')
  return data
 }
 if(!geometry&&points.length>1&&transport!=='car'){
  const payload={place_ids:points.map(p=>p.id),transport,custom_points:points.filter(p=>p.id<0).map(({id,name,lat,lng})=>({id,name,lat,lng})),point_positions:points.map(({id,lat,lng})=>({id,lat,lng}))}
  geometry=(await request('/api/routing',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})).geometry
 }
 const config=await request('/api/maps/config')
 const here=config.provider==='here'
 const host=document.createElement('div')
 Object.assign(host.style,{position:'fixed',left:'-10000px',top:'0',width:'960px',height:'600px',pointerEvents:'none'})
 host.setAttribute('aria-hidden','true');document.body.append(host)
 let map
 try{
  map=L.map(host,{zoomControl:false,attributionControl:false,zoomAnimation:false,fadeAnimation:false}).setView([points[0].lat,points[0].lng],13)
  const line=geometry?.coordinates?.map(p=>[p[1],p[0]])||[]
  map.fitBounds([...line,...points.map(p=>[p.lat,p.lng])],{padding:[55,65],maxZoom:15,animate:false})
  const tiles=L.tileLayer(here?'/api/maps/tiles/terrain/{z}/{x}/{y}':'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{crossOrigin:true,maxZoom:here?20:18})
  await new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>{cleanup();reject(new Error('Mapa nie wczytała się do zdjęcia. Spróbuj ponownie.'))},15000)
   const cleanup=()=>{clearTimeout(timer);tiles.off('load',loaded);tiles.off('tileerror',failed)}
   const loaded=()=>{cleanup();resolve()}
   const failed=()=>{cleanup();reject(new Error('Nie udało się pobrać mapy do zdjęcia. Spróbuj ponownie.'))}
   tiles.on('load',loaded).on('tileerror',failed).addTo(map)
  })
  const canvas=document.createElement('canvas');canvas.width=960;canvas.height=600
  const ctx=canvas.getContext('2d');ctx.fillStyle='#edf1e7';ctx.fillRect(0,0,960,600)
  const bounds=host.getBoundingClientRect()
  for(const tile of host.querySelectorAll('img.leaflet-tile-loaded')){
   const rect=tile.getBoundingClientRect();ctx.drawImage(tile,rect.left-bounds.left,rect.top-bounds.top,rect.width,rect.height)
  }
  if(line.length>1){
   ctx.lineCap='round';ctx.lineJoin='round';ctx.beginPath()
   line.forEach((p,i)=>{const pixel=map.latLngToContainerPoint(p);i?ctx.lineTo(pixel.x,pixel.y):ctx.moveTo(pixel.x,pixel.y)})
   ctx.strokeStyle='#fff';ctx.lineWidth=9;ctx.stroke();ctx.strokeStyle='#1685d2';ctx.lineWidth=5;ctx.stroke()
  }
  points.forEach((p,i)=>{
   const pixel=map.latLngToContainerPoint([p.lat,p.lng]);ctx.beginPath();ctx.arc(pixel.x,pixel.y,16,0,Math.PI*2);ctx.fillStyle='#19744f';ctx.fill();ctx.lineWidth=3;ctx.strokeStyle='#fff';ctx.stroke()
   ctx.fillStyle='#fff';ctx.font='bold 14px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(String(i+1),pixel.x,pixel.y)
  })
  const labels=here?(config.copyrights?.terrain||[]).filter(n=>map.getZoom()>=(n.minLevel??0)&&map.getZoom()<=(n.maxLevel??20)&&(!n.boxes?.length||n.boxes.some(b=>map.getBounds().intersects([[b[0],b[1]],[b[2],b[3]]])))).map(n=>n.label):[]
  const credit=`© OpenStreetMap contributors${here?` · © ${new Date().getFullYear()} HERE`:''}${labels.length?' · '+[...new Set(labels)].join(', '):''}`
  ctx.fillStyle='#fffffff0';ctx.fillRect(0,576,960,24);ctx.fillStyle='#244637';ctx.font='11px sans-serif';ctx.textAlign='right';ctx.textBaseline='middle';ctx.fillText(credit,950,588,940)
  return canvas.toDataURL('image/webp',.78)
 }finally{map?.remove();host.remove()}
}
