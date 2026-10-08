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
test('save immediately shows progress, rejects double click, and survives closing the dialog',async()=>{
 const report=fs.readFileSync(new URL('../reports_web/2026/2026-10-08/index.html',import.meta.url),'utf8');
 const handler=report.slice(report.indexOf('window.confirmSave ='),report.indexOf('// 新标签输入'));
 const button={disabled:false,textContent:'确认收藏',setAttribute(){},removeAttribute(){}};
 let resolveRequest,calls=0,messages=[];
 const context={window:{},pendingMeta:{repo:'test/project'},saveApi:'https://example.invalid',saveHeaders:()=>({}),document:{getElementById:id=>id==='dlgOk'?button:{value:'keep note'}},fetch:()=>{calls++;return new Promise(resolve=>resolveRequest=resolve)},AbortSignal,sessionStorage:{removeItem(){}},toast:message=>messages.push(message),closeDlg(){context.pendingMeta=null},savedSet:new Set(),refreshSavedStates(){}};
 vm.runInNewContext(handler,context);
 const saving=context.window.confirmSave();assert.equal(button.textContent,'保存中…');assert.equal(button.disabled,true);
 await context.window.confirmSave();assert.equal(calls,1);
 context.pendingMeta=null;
 resolveRequest({ok:true,status:200,json:async()=>({ok:true,removed:false})});await saving;
 assert.equal(context.savedSet.has('test/project'),true);assert.equal(button.disabled,false);assert.equal(button.textContent,'确认收藏');assert.deepEqual(messages,['已收藏到「我的精选」']);
});

test('manual import shows queued state, blocks duplicate clicks, and confirms only completed success',async()=>{
 const savedPage=fs.readFileSync(new URL('../reports_web/saved.html',import.meta.url),'utf8');
 const scripts=[...savedPage.matchAll(/<script>([\s\S]*?)<\/script>/g)];
 const importScript=scripts.find(match=>match[1].includes('window.submitImport'))[1];
 const elements=Object.fromEntries(['import-status','import-submit','import-url','list','count','tagBar','search','sort'].map(id=>[id,{textContent:'',innerHTML:'',value:id==='import-url'?'https://github.com/a/b':id==='sort'?'stars':'',appendChild(){}}]));
 const storage=new Map([['trending-save-key','password']]);let calls=0,finishSubmit,timer;
 const context={window:{addEventListener(){}},document:{getElementById:id=>elements[id],createElement:()=>({})},sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},location:{reload(){}},AbortSignal,URL,JSON,setTimeout:fn=>timer=fn,
 fetch:async(url,options)=>{
  if(options?.method==='POST'){calls++;return new Promise(resolve=>finishSubmit=resolve)}
  if(url.includes('/imports/'))return{ok:true,json:async()=>({status:'queued',url:'https://github.com/job'})};
  return{ok:true,json:async()=>({ok:true,items:[{repo:'a/b',desc:'中文介绍',saved_at:'2026-10-08'}]})};
 }};
 vm.runInNewContext(importScript,context);
 const pending=context.window.submitImport({preventDefault(){}});
 assert.equal(elements['import-submit'].disabled,true);
 await context.window.submitImport({preventDefault(){}});assert.equal(calls,1);
 finishSubmit({ok:true,json:async()=>({id:'job-id'})});await pending;
 assert.equal(storage.get('trending-import-id'),'job-id');assert.match(elements['import-status'].textContent,/排队/);
 assert.doesNotMatch(elements['import-status'].textContent,/已处理完成/);
 context.fetch=async(url)=>({ok:true,json:async()=>url.includes('/imports/')?{status:'completed',conclusion:'success'}:{ok:true,items:[{repo:'a/b',desc:'中文介绍',saved_at:'2026-10-08'}]}});
 await timer();assert.equal(storage.has('trending-import-id'),false);assert.equal(elements['import-submit'].disabled,false);
 assert.match(elements['import-status'].textContent,/已处理完成/);assert.match(elements.list.innerHTML,/中文介绍/);
});
