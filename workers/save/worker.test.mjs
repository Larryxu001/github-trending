import test from 'node:test';
import assert from 'node:assert/strict';
import worker from './worker.js';
const env={GH_PAT:'fake',SAVE_KEY:'test-password',FEISHU_WEBHOOK:'https://example.invalid'};
const request=(meta,auth=true)=>new Request('https://example.invalid',{method:'POST',headers:{'Content-Type':'application/json',...(auth?{Authorization:'Bearer test-password'}:{})},body:JSON.stringify(meta)});
const stored=(items,sha='sha')=>new Response(JSON.stringify({sha,content:Buffer.from(JSON.stringify({items})).toString('base64')}));

test('anonymous writes and foreign origins are rejected without upstream requests',async()=>{
 globalThis.fetch=()=>{throw new Error('upstream must not be called')};
 assert.equal((await worker.fetch(request({repo:'test/project'},false),env)).status,401);
 assert.equal((await worker.fetch(new Request('https://example.invalid',{headers:{Origin:'https://evil.invalid'}}),env)).status,403);
});
test('corrupt or missing saved data never causes replacement',async()=>{
 for(const response of [new Response(JSON.stringify({sha:'sha',content:Buffer.from('corrupt').toString('base64')})),new Response('',{status:404})]){
  let writes=0; globalThis.fetch=async(url,options)=>{if(options?.method==='PUT')writes++;return response};
  assert.equal((await worker.fetch(request({repo:'test/project'}),env)).status,500);assert.equal(writes,0);
 }
});
test('reject executable links, wrong field types and oversized requests before writing',async()=>{
 globalThis.fetch=()=>{throw new Error('upstream must not be called')};
 for(const meta of [{repo:'test/project',site:'javascript:alert(1)'},{repo:'test/project',url:'data:text/html,bad'},{repo:'test/project',tags:[{}]},{repo:'test/project',stars:'many'},{repo:'../../bad'}]) assert.equal((await worker.fetch(request(meta),env)).status,400);
 assert.equal((await worker.fetch(request({repo:'test/project',desc:'x'.repeat(21000)}),env)).status,413);
});
test('conflict re-read preserves another concurrent save and existing notes',async()=>{
 let reads=0,writes=[];
 const original={repo:'test/project',note:'keep note',tags:['keep'],saved_at:'2026-10-01'};
 globalThis.fetch=async(url,options)=>{
  if(options?.method==='PUT'){
   writes.push(JSON.parse(options.body));
   return writes.length===1?new Response('{"message":"conflict"}',{status:409}):new Response('{}');
  }
  reads++;return stored(reads===1?[original]:[original,{repo:'other/project'}],String(reads));
 };
 const response=await worker.fetch(request({repo:'test/project',desc:'updated'}),env);
 assert.equal(response.status,200);const d=await response.json();assert.equal(d.items.length,2);assert.equal(d.items[0].note,'keep note');assert.deepEqual(d.items[0].tags,['keep']);assert.equal(writes[1].sha,'2');
});
test('health catches missing credentials and validates readable saved data',async()=>{
 globalThis.fetch=async()=>stored([]);
 assert.equal((await worker.fetch(new Request('https://example.invalid/health'),env)).status,200);
 assert.equal((await worker.fetch(new Request('https://example.invalid/health'),{GH_PAT:'fake'})).status,503);
});
test('page entrance validates password without account or upstream writes',async()=>{
 globalThis.fetch=()=>{throw new Error('upstream must not be called')};
 for(const [password,status] of [['',401],['wrong',401],['test-password',200]]){
  const response=await worker.fetch(new Request('https://example.invalid/auth',{headers:{Authorization:'Bearer '+password}}),env);
  assert.equal(response.status,status);if(status===200)assert.deepEqual(await response.json(),{ok:true});
 }
 assert.equal((await worker.fetch(new Request('https://example.invalid/auth'),{})).status,503);
});
test('collection cron dispatches scheduled collection, health cron stays separate',async()=>{
 for(const [cron,workflow] of [['0 1-23/3 * * *','collect.yml'],['20 3 * * *','health.yml']]){
  let dispatched;
  globalThis.fetch=async(url,options)=>{dispatched={url,body:JSON.parse(options.body)};return new Response(null,{status:204})};
  await worker.scheduled({cron},env,{});assert.ok(dispatched.url.endsWith('/'+workflow+'/dispatches'));
  assert.deepEqual(dispatched.body,cron==='20 3 * * *'?{ref:'main'}:{ref:'main',inputs:{mode:'scheduled'}});
 }
});
function memoryCache(){
 const entries=new Map();
 return{async match(key){return entries.get(key)?.clone()},async put(key,response){entries.set(key,response.clone())},async delete(key){entries.delete(key)}};
}
test('recent page read removes the extra GitHub read and subsequent saves keep new SHA',async()=>{
 globalThis.caches={default:memoryCache()};let reads=0,writes=[];
 globalThis.fetch=async(url,options)=>{
  if(options?.method==='PUT'){writes.push(JSON.parse(options.body));return new Response(JSON.stringify({content:{sha:'updated-'+writes.length}}))}
  reads++;return stored([],'initial');
 };
 try{
  await worker.fetch(new Request('https://example.invalid'),env);
  assert.equal((await worker.fetch(request({repo:'first/project'}),env)).status,200);
  assert.equal((await worker.fetch(request({repo:'second/project'}),env)).status,200);
  assert.equal(reads,1);assert.equal(writes.length,2);assert.equal(writes[1].sha,'updated-1');
  assert.equal(JSON.parse(Buffer.from(writes[1].content,'base64')).items.length,2);
 }finally{delete globalThis.caches}
});
test('stale cached SHA falls back to fresh read and preserves concurrently saved project',async()=>{
 globalThis.caches={default:memoryCache()};let reads=0,writes=[];
 globalThis.fetch=async(url,options)=>{
  if(options?.method==='PUT'){writes.push(JSON.parse(options.body));return writes.length===1?new Response('{"message":"conflict"}',{status:409}):new Response(JSON.stringify({content:{sha:'latest'}}))}
  reads++;return stored(reads===1?[]:[{repo:'other/project'}],reads===1?'old':'fresh');
 };
 try{
  await worker.fetch(new Request('https://example.invalid'),env);
  assert.equal((await worker.fetch(request({repo:'my/project'}),env)).status,200);
  assert.equal(reads,2);assert.equal(writes[1].sha,'fresh');assert.equal(JSON.parse(Buffer.from(writes[1].content,'base64')).items.length,2);
 }finally{delete globalThis.caches}
});
test('cache failure falls back to GitHub and never rejects a confirmed save',async()=>{
 globalThis.caches={default:{async match(){throw Error('cache unavailable')},async put(){throw Error('cache unavailable')}}};
 globalThis.fetch=async(url,options)=>options?.method==='PUT'?new Response(JSON.stringify({content:{sha:'new'}})):stored([]);
 try{assert.equal((await worker.fetch(request({repo:'my/project'}),env)).status,200)}finally{delete globalThis.caches}
});
