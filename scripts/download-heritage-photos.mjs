import fs from 'node:fs/promises'
import crypto from 'node:crypto'
import sharp from 'sharp'
const path='data/heritage/source-records.json'
const records=JSON.parse(await fs.readFile(path,'utf8'))
await fs.mkdir('public/images/heritage',{recursive:true})
let cursor=0,done=0,failed=0,rateLimited=false
async function worker(){
 while(cursor<records.length&&!rateLimited){
  const record=records[cursor++];if(!record.photo)continue
  if(!/^Q\d+$/.test(record.key))throw Error('Invalid source identifier')
  const destination=`public/images/heritage/${record.key.toLowerCase()}.webp`
  try{await fs.access(destination);record.photo.local_path='/'+destination.replace(/^public\//,'');continue}catch{}
  let error
  for(const url of [...new Set([record.photo.download_url,record.photo.original_url])]){
   try{
    const parsed=new URL(url);if(!['upload.wikimedia.org','thumb.wikimedia.org'].includes(parsed.hostname)||parsed.protocol!=='https:')throw Error('Untrusted image source')
    parsed.search=''
    const response=await fetch(parsed,{headers:{'User-Agent':'PerlyLubuskieCatalog/1.0 (https://github.com/mdriverpl/perlylubuskie.pl)'},signal:AbortSignal.timeout(35000)})
    if(response.status===429){rateLimited=true;console.log('Rate limit; stopping. Retry-After:',response.headers.get('retry-after'));break}
    if(!response.ok)throw Error(`HTTP ${response.status}`)
    if(Number(response.headers.get('content-length'))>30_000_000)throw Error('Original too large')
    const buffer=Buffer.from(await response.arrayBuffer());if(buffer.length>30_000_000)throw Error('Image too large')
    await sharp(buffer,{limitInputPixels:100_000_000,sequentialRead:true}).rotate().resize({width:1200,withoutEnlargement:true}).webp({quality:82}).toFile(destination)
    record.photo.local_path='/'+destination.replace(/^public\//,'')
    record.photo.source_sha256=crypto.createHash('sha256').update(buffer).digest('hex')
    record.photo.checked_at='2026-10-30'
    delete record.photo_issue;error=null;done++;break
   }catch(e){error=e.message}
  }
  if(error){record.photo_issue='Nie udało się pobrać licencjonowanego zdjęcia: '+error;failed++}
  if((done+failed)%10===0)console.log('Photos downloaded',done,'failed',failed)
  if(!rateLimited)await new Promise(r=>setTimeout(r,2000))
 }
}
await worker()
await fs.writeFile(path,JSON.stringify(records,null,2)+'\n')
console.log('Completed:',records.filter(r=>r.photo?.local_path).length,'local photos;',failed,'download failures')
