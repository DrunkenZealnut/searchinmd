#!/usr/bin/env node
/* Regression checks for the semantic recount dashboard. */
const fs=require('fs'),vm=require('vm'),path=require('path');
const root=path.join(__dirname,'..'), html=fs.readFileSync(path.join(root,'docs/index.html'),'utf8');
const data=fs.readFileSync(path.join(root,'docs/semantic_recount_data.js'),'utf8');
const ncsFrame=fs.readFileSync(path.join(root,'docs/ncs_semantic_dashboard.js'),'utf8');
const inline=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
const els={}; const make=(id)=>els[id]||(els[id]={id,innerHTML:'',textContent:'',style:{},dataset:{},classList:{add(){},remove(){},toggle(){},contains(){return false}},setAttribute(){},getAttribute(){return null},closest(){return null},appendChild(){},replaceChild(){},click(){},parentNode:{replaceChild(){}}});
const ctn=make('ctn');
const document={documentElement:{className:'theme-light'},body:make('body'),getElementById:make,createElement:make,querySelector(s){return s==='.ctn'?ctn:make('q')},querySelectorAll(){return []},addEventListener(){}};
const ctx={document,console:{log(){},warn(){},error(...a){throw Error(a.join(' '))}},window:null,globalThis:null,JSON,Math,Object,Array,String,Number,Date,RegExp,Intl,parseInt,parseFloat,isNaN,setTimeout,clearTimeout,performance:{now(){return 0}},requestAnimationFrame(){},localStorage:{getItem(){return null},setItem(){}},matchMedia(){return {matches:false}},getComputedStyle(){return {getPropertyValue(){return '#000'}}},htmlToImage:{toPng(){return Promise.resolve('')}},Chart:{defaults:{animation:false}}};
ctx.window=ctx;ctx.globalThis=ctx;vm.createContext(ctx);vm.runInContext(data,ctx);vm.runInContext(inline,ctx,{filename:'docs/index.html'});vm.runInContext(ncsFrame,ctx,{filename:'docs/ncs_semantic_dashboard.js'});
const D=ctx.SEMANTIC_RECOUNT, K=D.keywords;
function ok(name,condition){if(!condition)throw Error('FAIL: '+name);console.log('✓ '+name)}
ok('30개 독립 키워드',K.length===30);
ok('최종 의미 출현 합계 14,168건',K.reduce((s,r)=>s+r[1]+r[2],0)===14168);
ok('후보 판정 합계 100개',D.status.included+D.status.held+D.status.excluded+D.status.notFound===100);
ok('표에 30개 키워드 렌더',(els.semanticKb.innerHTML.match(/<tr>/g)||[]).length===30);
ok('확장 표현 표시',els.semanticKb.innerHTML.includes('화학 물질')&&els.semanticKb.innerHTML.includes('개인 보호 장비'));
ok('기존 등급·사고사례 본문 미노출',!ctn.innerHTML.includes('등급3')&&!ctn.innerHTML.includes('사고사례 판정'));
ok('NCS가 교과서 분석 틀을 사용',ctn.innerHTML.includes('반도체고 교과서 분석 틀 적용')&&ctn.innerHTML.includes('NCS 영역 목록'));
console.log('PASS 7 checks');
