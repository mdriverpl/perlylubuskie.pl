import assert from 'node:assert/strict'
import {readApiJson} from '../src/apiResponse.js'
for(const status of [200,500,502]){
 for(const body of ['', '<html>Bad gateway</html>', '{"broken":', 'null']){
  await assert.rejects(readApiJson(new Response(body,{status})),error=>error.message==='Serwer jest chwilowo niedostępny. Spróbuj ponownie.'&&error.name!=='SyntaxError')
 }
}
assert.equal(await readApiJson(new Response(null,{status:204})),null)
assert.deepEqual(await readApiJson(new Response('{"value":1}')),{value:1})
assert.deepEqual(await readApiJson(new Response('[]')),[])
await assert.rejects(readApiJson(new Response('{"detail":"Brak zgody."}',{status:403})),/Brak zgody/)
await assert.rejects(readApiJson({json:async()=>{throw new DOMException('Aborted','AbortError')}}),error=>error.name==='AbortError')
console.log('PASS: empty/truncated/HTML/null API responses, server messages, successful JSON, 204 and abort handling')
