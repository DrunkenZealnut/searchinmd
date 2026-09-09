#!/usr/bin/env node
/* Regression checks for the occurrence-grade dashboards. */
const fs=require('fs'),vm=require('vm'),path=require('path');
const root=path.join(__dirname,'..');
const data=fs.readFileSync(path.join(root,'docs/semantic_recount_data.js'),'utf8');
const renderer=fs.readFileSync(path.join(root,'docs/semantic_grade_dashboard.js'),'utf8');
const ncsPage=fs.readFileSync(path.join(root,'docs/index.html'),'utf8');
const schoolPage=fs.readFileSync(path.join(root,'docs/textbook.html'),'utf8');
const els={};
function make(id){return els[id]||(els[id]={id,innerHTML:'',textContent:'',style:{},dataset:{},classList:{add(){},remove(){},toggle(){},contains(){return false}},setAttribute(){},getAttribute(){return null},closest(){return null},appendChild(){},replaceChild(){},click(){},parentNode:{replaceChild(){}}})}
const ctn=make('ctn');
const document={documentElement:{className:'theme-light'},body:make('body'),getElementById:make,createElement:make,querySelector(s){return s==='.ctn'?ctn:make('q')},querySelectorAll(){return []},addEventListener(){}};
function Chart(){} Chart.getChart=()=>null;
const ctx={document,console:{log(){},warn(){},error(...a){throw Error(a.join(' '))}},window:null,globalThis:null,JSON,Math,Object,Array,String,Number,Date,RegExp,Intl,parseInt,parseFloat,isNaN,setTimeout,clearTimeout,getComputedStyle(){return {getPropertyValue(){return '#000'}}},Chart};
ctx.window=ctx;ctx.globalThis=ctx;vm.createContext(ctx);vm.runInContext(data,ctx);vm.runInContext(renderer,ctx,{filename:'docs/semantic_grade_dashboard.js'});
const D=ctx.SEMANTIC_RECOUNT;
function ok(name,condition){if(!condition)throw Error('FAIL: '+name);console.log('✓ '+name)}
function headings(html){return [...html.matchAll(/<h2>([^<]+)<\/h2>/g)].map(m=>m[1])}
function render(corpus){ctn.innerHTML='';ctx.renderSemanticGradeDashboard(corpus);return ctn.innerHTML}
function visibleSource(html){return html.replace(/<template id="legacy-dashboard">[\s\S]*?<\/template>/,'')}

ok('출현건수가 등급 분모',D.meta.denominator==='occurrences');
ok('30개 독립 키워드',D.keywords.length===30);
ok('최종 의미 출현 합계 14,168건',D.corpora.NCS.total+D.corpora['교과서'].total===14168);
ok('NCS 등급 출현 정합성',JSON.stringify(D.corpora.NCS.grades)===JSON.stringify({'1':4869,'2':4713,'3':2480,unpaged:813}));
ok('교과서 등급 출현 정합성',JSON.stringify(D.corpora['교과서'].grades)===JSON.stringify({'1':705,'2':468,'3':120,unpaged:0}));
ok('후보 판정 합계 100개',Object.values(D.status).reduce((a,b)=>a+b,0)===100);

const ncs=render('NCS'), school=render('교과서');
const common=['전체 등급 분포','키워드별 상세','문제점과 시사점','NCS 교재 vs 교과서 비교','개선 권고안'];
ok('NCS가 교과서 등급1~3 흐름 사용',common.every(x=>headings(ncs).includes(x))&&ncs.includes('NCS 영역별 현황'));
ok('교과서도 같은 분석 흐름 사용',common.every(x=>headings(school).includes(x))&&school.includes('교과서별 현황'));
ok('두 페이지 섹션 순서 일치',common.every((x,i)=>headings(ncs).indexOf(x)===headings(school).indexOf(x)));
ok('NCS 출현건수 KPI',ncs.includes('4,869')&&ncs.includes('4,713')&&ncs.includes('2,480')&&ncs.includes('813'));
ok('교과서 출현건수 KPI',school.includes('705')&&school.includes('468')&&school.includes('120'));
ok('페이지 분모 문구 제거',!ncs.includes('단위: 쪽')&&!school.includes('단위: 쪽')&&!school.includes('전체 2,055쪽 기준'));
ok('키워드 상세에 등급 열 표시',ncs.includes('등급1')&&ncs.includes('등급2')&&ncs.includes('등급3')&&school.includes('등급1'));
ok('확장 표현 표시',ncs.includes('화학 물질')&&ncs.includes('개인 보호 장비'));
ok('NCS 페이지에 공통 렌더러 연결',ncsPage.includes("SEMANTIC_DASHBOARD_CORPUS='NCS'")&&ncsPage.includes('semantic_grade_dashboard.js'));
ok('교과서 페이지에 공통 렌더러 연결',schoolPage.includes("SEMANTIC_DASHBOARD_CORPUS='교과서'")&&schoolPage.includes('semantic_recount_data.js')&&schoolPage.includes('semantic_grade_dashboard.js'));
ok('정적 대체 화면도 출현건수 기준',visibleSource(ncsPage).includes('12,875')&&visibleSource(schoolPage).includes('1,293')&&!visibleSource(schoolPage).includes('전체 2,055쪽 기준'));
ok('기존 페이지 화면은 실행되지 않는 템플릿으로 격리',ncsPage.includes('<template id="legacy-dashboard">')&&schoolPage.includes('<template id="legacy-dashboard">'));
console.log('PASS 18 checks');
