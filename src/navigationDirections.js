const radians=degrees=>degrees*Math.PI/180
const degrees=radians=>radians*180/Math.PI
const angle=value=>(value%360+360)%360
export function movementDirection(anchor,point,heading,speed){
 if(Number.isFinite(heading)&&heading>=0&&heading<360&&speed!==0)return {heading,anchor:{...point,heading}}
 if(!anchor)return {heading:null,anchor:{...point,heading:null}}
 const lat=radians(point.lat-anchor.lat),lng=radians(point.lng-anchor.lng)
 const a=Math.sin(lat/2)**2+Math.cos(radians(anchor.lat))*Math.cos(radians(point.lat))*Math.sin(lng/2)**2
 const distance=6371000*2*Math.atan2(Math.sqrt(a),Math.sqrt(Math.max(0,1-a)))
 // Accumulate movement from the last reliable point; ignore stationary GPS jitter.
 const threshold=Math.max(3,Math.min(20,Math.max(point.accuracy||0,anchor.accuracy||0)/2))
 if(distance<threshold)return {heading:anchor.heading,anchor}
 const y=Math.sin(lng)*Math.cos(radians(point.lat))
 const x=Math.cos(radians(anchor.lat))*Math.sin(radians(point.lat))-Math.sin(radians(anchor.lat))*Math.cos(radians(point.lat))*Math.cos(lng)
 const direction=angle(degrees(Math.atan2(y,x)))
 return {heading:direction,anchor:{...point,heading:direction}}
}

function visibleInterval(a,b,width,height){
 const dx=b.x-a.x,dy=b.y-a.y
 let first=0,last=1
 for(const [p,q] of [[-dx,a.x+16],[dx,width+16-a.x],[-dy,a.y+16],[dy,height+16-a.y]]){
  if(p===0){if(q<0)return null;continue}
  const t=q/p
  if(p<0)first=Math.max(first,t);else last=Math.min(last,t)
  if(first>last)return null
 }
 return [first,last]
}

export function routeDirectionArrows(coordinates,project,{width,height,spacing=85,max=100}){
 const arrows=[]
 let travelled=0,previous=null
 for(const coordinate of coordinates||[]){
  if(!Array.isArray(coordinate)||!Number.isFinite(coordinate[0])||!Number.isFinite(coordinate[1])){previous=null;continue}
  const point=project(coordinate)
  if(previous){
   const dx=point.x-previous.x,dy=point.y-previous.y,length=Math.hypot(dx,dy)
   if(length>0){
    const visible=visibleInterval(previous,point,width,height)
    if(visible){
     const start=travelled+visible[0]*length,end=travelled+visible[1]*length
     for(let distance=Math.max(spacing/2,Math.ceil((start-spacing/2)/spacing)*spacing+spacing/2);distance<=end;distance+=spacing){
      const ratio=(distance-travelled)/length
      arrows.push({x:previous.x+dx*ratio,y:previous.y+dy*ratio,heading:angle(degrees(Math.atan2(dx,-dy)))})
      if(arrows.length>=max)return arrows
     }
    }
    travelled+=length
   }
  }
  previous=point
 }
 return arrows
}
