export const viewPaths={discover:'/start',places:'/miejsca',explore:'/planer',walking:'/wycieczki-piesze',cycling:'/wycieczki-rowerowe',planner:'/trasa',about:'/o-regionie'}
export function viewFromUrl(value){
 const url=new URL(value.href||value,'http://localhost')
 const path=url.pathname.replace(/\/+$/,'')||'/'
 const matched=Object.entries(viewPaths).find(([,pathname])=>pathname===path)
 if(matched)return matched[0]
 const legacy=url.searchParams.get('view')
 return path==='/'&&Object.hasOwn(viewPaths,legacy)?legacy:'discover'
}
export function updateViewUrl(view,{replace=false}={}){
 const url=new URL(window.location.href)
 url.pathname=viewPaths[view]||viewPaths.discover
 url.searchParams.delete('view')
 url.hash=''
 if(url.href!==window.location.href)window.history[replace?'replaceState':'pushState'](null,'',url)
}
