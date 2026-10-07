import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const page=fs.readFileSync(new URL('../reports_web/index.html',import.meta.url),'utf8');
const script=page.match(/<script>([\s\S]*?)<\/script>/)[1];
async function entrance(cached=null,status=200){
 const elements=Object.fromEntries(['page-access','page-content','access-form','access-password','access-submit','access-error'].map(id=>[id,{hidden:id==='page-content',inert:id==='page-content',value:'',focus(){},addEventListener(name,handler){this[name]=handler}}]));
 let stored=cached,calls=[],events=[];
 const context={document:{getElementById:id=>elements[id]},sessionStorage:{getItem:()=>stored,setItem:(k,v)=>stored=v,removeItem:()=>stored=null},window:{dispatchEvent:event=>events.push(event.type)},Event,AbortSignal,fetch:async(url,options)=>{calls.push({url,options});return{status,ok:status===200,json:async()=>({ok:status===200})}}};
 vm.runInNewContext(script,context);await new Promise(resolve=>setImmediate(resolve));
 return{elements,calls,events,get stored(){return stored}};
}
test('page starts locked; no password is embedded and no account field exists',async()=>{
 const state=await entrance();assert.equal(state.elements['page-content'].hidden,true);assert.equal(state.calls.length,0);
 assert.match(page,/<input[^>]+type="password"/);assert.doesNotMatch(page,/type="(?:email|text)"/);
});
test('wrong password leaves content locked and clears invalid session',async()=>{
 const state=await entrance(null,401);state.elements['access-password'].value='wrong';
 state.elements['access-form'].submit({preventDefault(){}}); await new Promise(resolve=>setImmediate(resolve));
 assert.equal(state.elements['page-content'].hidden,true);assert.equal(state.stored,null);assert.match(state.elements['access-error'].textContent,/密码不正确/);
});
test('correct password reveals page and supplies the same session for favorites',async()=>{
 const state=await entrance();state.elements['access-password'].value='test-password';
 state.elements['access-form'].submit({preventDefault(){}}); await new Promise(resolve=>setImmediate(resolve));
 assert.equal(state.elements['page-content'].hidden,false);assert.equal(state.elements['page-content'].inert,false);assert.equal(state.elements['page-access'].hidden,true);
 assert.equal(state.stored,'test-password');assert.equal(state.calls[0].options.headers.Authorization,'Bearer test-password');assert.deepEqual(state.events,['trending-unlocked']);
});
test('navigation revalidates existing session without another password prompt',async()=>{
 const state=await entrance('test-password');assert.equal(state.elements['page-content'].hidden,false);assert.equal(state.calls.length,1);
});
test('service failure never unlocks the page',async()=>{
 const state=await entrance('test-password',503);assert.equal(state.elements['page-content'].hidden,true);assert.match(state.elements['access-error'].textContent,/暂时不可用/);
});
