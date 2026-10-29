import sharp from 'sharp'
import { mkdir, writeFile } from 'node:fs/promises'
import { places } from '../src/data.js'
const reference = process.argv[2]
if (!reference) throw new Error('Podaj ścieżkę do załączonej wizualizacji strony głównej.')
await mkdir('public/images', { recursive: true })
const areas = {
 hero: [650,80,650,350], lagow: [94,609,324,138], park: [438,609,320,138],
 tunnel: [779,609,320,138], food: [1120,609,319,138],
 bike: [94,874,429,73], 'park-trail': [557,874,422,73], warta: [1014,874,425,73], lake: [680,98,300,290],
}
for(const [name,[left,top,width,height]] of Object.entries(areas)) {
 await sharp(reference).extract({left,top,width,height}).resize({width:name==='hero'?1600:900}).webp({quality:90}).toFile(`public/images/${name}.webp`)
}
await writeFile('backend/seed.json', JSON.stringify(places,null,2))
console.log('Przygotowano 9 zdjęć i dane początkowe.')
