import fs from 'node:fs/promises'
const records=JSON.parse(await fs.readFile('data/heritage/source-records.json','utf8'))
const coverage=JSON.parse(await fs.readFile('data/heritage/coverage.json','utf8'))
coverage.local_photos=records.filter(r=>r.photo?.local_path).length
coverage.external_photos=records.filter(r=>r.photo&&!r.photo.local_path).length
coverage.without_verified_photo=records.filter(r=>!r.photo).length
await fs.writeFile('data/heritage/coverage.json',JSON.stringify(coverage,null,2)+'\n')
const canonical=url=>{const u=new URL(url);u.search='';return u.href}
const catalog=records.map(r=>({
 id:r.aliases.includes('Q16618861')?1:1000000+Number(r.key.slice(1)),
 name:r.aliases.includes('Q16618861')?'Łagów':r.name,
 subtitle:`${r.kind==='castle'?'Zamek':'Pałac'} · ${r.location}`,
 category:'heritage',image:r.photo?(r.photo.local_path||canonical(r.photo.download_url)):'/images/heritage-placeholder.svg',
 lat:r.lat,lng:r.lng,rating:0,location:r.location,description:r.description,
 details:{kind:r.kind,official_name:r.name,wikidata:r.key,coordinate_source:r.coordinate_source,description_license:r.description_license,sources:r.sources,registry:r.registry,condition:r.condition,checked_at:r.checked_at,
 photo:r.photo?{author:r.photo.author,license:r.photo.license,license_url:r.photo.license_url,source_url:r.photo.source_url,archival:r.photo.archival,transformation:r.photo.local_path?r.photo.transformation:'Oryginalny plik Wikimedia Commons; miniatura wyświetlana w aplikacji.'}:null}
}))
await fs.mkdir('src/catalog',{recursive:true})
await fs.writeFile('src/catalog/heritage.json',JSON.stringify(catalog,null,2)+'\n')
const {places}=await import('../src/data.js?build='+Date.now())
await fs.writeFile('backend/seed.json',JSON.stringify(places,null,2)+'\n')
const esc=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))
const link=(url,label)=>`<a href="${esc(url)}">${esc(label)}</a>`
await fs.writeFile('public/heritage-credits.html',`<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Źródła katalogu — Perły Ziemi Lubuskiej</title><style>body{font:16px/1.7 system-ui;max-width:900px;margin:40px auto;padding:20px;color:#234333}article{border-bottom:1px solid #ddd;padding:18px 0}a{color:#176e4f}</style><h1>Źródła opisów i fotografii</h1><p><a href="/hospitality-credits.html">Łagów — noclegi i gastronomia</a></p><p><a href="/lagow-credits.html">Łagów i okolice — źródła atrakcji</a></p><p><a href="/wineries-credits.html">Winnice — osobny katalog i źródła</a></p><p>Katalog ${records.length} obiektów województwa lubuskiego. Stan źródeł: 30.10.2026. Katalog nie stanowi pełnego rejestru zabytków. Obejmuje także ruiny i pozostałości. Lokalizacja nie oznacza możliwości wejścia na teren prywatny.</p><p>Fakty Wikidata: CC0. Fragmenty opisów Wikipedii: CC BY-SA 4.0 (autorzy w historii artykułu). Fotografie na indywidualnych licencjach poniżej. Brak zdjęcia oznaczono ilustracją zastępczą.</p>${catalog.map(p=>`<article><h2>${esc(p.details.official_name)}</h2><p>${p.details.sources.map(s=>link(s.url,s.title)).join(' · ')}. Opis: ${esc(p.details.description_license)}.</p>${p.details.photo?`<p>Zdjęcie: ${esc(p.details.photo.author)} · ${link(p.details.photo.license_url,p.details.photo.license)} · ${link(p.details.photo.source_url,'Plik i historia autorstwa')}. ${esc(p.details.photo.transformation)}${p.details.photo.archival?' Fotografia archiwalna.':''}</p>`:'<p>Brak potwierdzonego zdjęcia.</p>'}</article>`).join('')}</html>`)
console.log(`${catalog.length} heritage records; ${places.length} total places; ${records.filter(r=>r.photo?.local_path).length} local photos`)
