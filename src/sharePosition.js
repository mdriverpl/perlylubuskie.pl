export function positionShare(position){
 if(!Number.isFinite(position?.lat)||!Number.isFinite(position?.lng)||Math.abs(position.lat)>90||Math.abs(position.lng)>180)return null
 const coordinates=position.lat.toFixed(6)+', '+position.lng.toFixed(6)
 const url='https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(position.lat.toFixed(6)+','+position.lng.toFixed(6))
 const text='Moja aktualna pozycja GPS: '+coordinates+'\n'+url
 const ios=/iPad|iPhone|iPod/.test(navigator.userAgent)
 return {coordinates,url,text,sms:'sms:'+(ios?'&':'?')+'body='+encodeURIComponent(text),whatsapp:'https://wa.me/?text='+encodeURIComponent(text)}
}
