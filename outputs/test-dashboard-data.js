#!/usr/bin/env node
/* 대시보드 교차검증 하니스 (2026-09-14, semantic-recount-remediation).
 *
 * 무엇을 무엇과 대조하는가 — 수치는 semantic_keyword_recount.py 한 실행에서만 태어나고
 * (docs/03-analysis/data/semantic_summary.json = docs/semantic_recount_data.js), 발표면은 그것을 인용만 한다.
 * 하드코딩 값끼리의 단언은 두지 않는다 (CLAUDE.md "never asserted against themselves").
 *
 *   S1 렌더러       data.js → .ctn 렌더 (섹션 순서·등급 열·공통 렌더러 연결)
 *   S2 data≡summary semantic_recount_data.js 의 JSON ≡ semantic_summary.json, 가드 통과 실행(expected true, force false)
 *   S3 summary 정합 등급 합 == total, 미확정 0, 키워드·그룹 합 == corpus total, 후보 100, 문서 86/9, 절대 경로·본문 없음
 *   S4 이전 기준     meta.previous_basis ≡ reseg_summary.json (옛 D13 계보), marker_offset.moved 0 (옛 D13q)
 *   S5 정적 화면     index.html·textbook.html 의 .ctn 초기값·<template> 값 == summary/reseg, 브리지 절, 구 수치 0회
 *   S6 분리 분석     keyword-analysis.html·결과 HTML 2건 == summary (총 건수·기준 파일·교재 수)
 *   S7 README        핵심 수치 == summary, "이전 기준" == reseg, 85개 0회, 정본 명령
 *   S8 CLAUDE.md     출현건수 분모 예외 문단, data_source 트랩
 *   S9 인용 수      README·CLAUDE.md 가 적은 이 하니스의 단언 수 == 실제 (옛 D14)
 */
const fs = require('fs'), vm = require('vm'), path = require('path');
const ROOT = path.join(__dirname, '..');
const read = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');
let pass = 0, fail = 0, warned = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; console.log('  ✗ ' + name + (extra !== undefined ? ' — ' + String(extra).slice(0, 300) : '')); }
}
// 알려진 결함 — 고치지 않은 채 문서화만 하는 단언. 실패해도 스위트를 깨지 않고 ⚠ 로 찍는다. 고치면 check() 로 승격.
// (CLAUDE.md "Testing" 의 known() 규약. 2026-09-14 현재 0건.)
function known(name, cond, extra) {
  if (cond) { pass++; console.log('  ✓ ' + name + ' (known issue: resolved — promote to check)'); }
  else { warned++; pass++; console.log('  ⚠ KNOWN ISSUE ' + name + (extra !== undefined ? ' — ' + String(extra).slice(0, 300) : '')); }
}
const fmt = (n) => Number(n).toLocaleString('ko-KR');
const pct = (a, b) => (a / b * 100).toFixed(1);
const gsum = (g) => g['1'] + g['2'] + g['3'];

// ---------------------------------------------------------------- 입력
const dataJs = read('docs/semantic_recount_data.js');
const renderer = read('docs/semantic_grade_dashboard.js');
const ncsPage = read('docs/index.html');
const schoolPage = read('docs/textbook.html');
const S = JSON.parse(read('docs/03-analysis/data/semantic_summary.json'));
const R = JSON.parse(read('docs/03-analysis/data/reseg_summary.json'));
const N = S.corpora.NCS, T = S.corpora['교과서'];

// ---------------------------------------------------------------- 렌더 샌드박스
const els = {};
function make(id) { return els[id] || (els[id] = { id, innerHTML: '', textContent: '', style: {}, dataset: {}, classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } }, setAttribute() {}, getAttribute() { return null; }, closest() { return null; }, appendChild() {}, replaceChild() {}, click() {}, parentNode: { replaceChild() {} } }); }
const ctn = make('ctn');
const document = { documentElement: { className: 'theme-light' }, body: make('body'), getElementById: make, createElement: make, querySelector(s) { return s === '.ctn' ? ctn : make('q'); }, querySelectorAll() { return []; }, addEventListener() {} };
function Chart() {} Chart.getChart = () => null;
const ctx = { document, console: { log() {}, warn() {}, error(...a) { throw Error(a.join(' ')); } }, window: null, globalThis: null, JSON, Math, Object, Array, String, Number, Date, RegExp, Intl, parseInt, parseFloat, isNaN, setTimeout, clearTimeout, getComputedStyle() { return { getPropertyValue() { return '#000'; } }; }, Chart };
ctx.window = ctx; ctx.globalThis = ctx; vm.createContext(ctx);
vm.runInContext(dataJs, ctx); vm.runInContext(renderer, ctx, { filename: 'docs/semantic_grade_dashboard.js' });
const D = ctx.SEMANTIC_RECOUNT;
const headings = (html) => [...html.matchAll(/<h2>([^<]+)<\/h2>/g)].map((m) => m[1]);
const render = (corpus) => { ctn.innerHTML = ''; ctx.renderSemanticGradeDashboard(corpus); return ctn.innerHTML; };
const visible = (html) => html.replace(/<template id="legacy-dashboard">[\s\S]*?<\/template>/, '');
const templateOf = (html) => (html.match(/<template id="legacy-dashboard">([\s\S]*?)<\/template>/) || ['', ''])[1];

// ================================================================ S1 렌더러
console.log('\n[S1] 렌더러 — data.js → .ctn');
const ncs = render('NCS'), school = render('교과서');
const common = ['전체 등급 분포', '키워드별 상세', '문제점과 시사점', 'NCS 교재 vs 교과서 비교', '개선 권고안'];
check('S1a 출현건수가 등급 분모', D.meta.denominator === 'occurrences');
check('S1b 30개 독립 키워드', D.keywords.length === 30);
check('S1c NCS 가 교과서와 같은 등급1~3 흐름', common.every((x) => headings(ncs).includes(x)) && ncs.includes('NCS 영역별 현황'));
check('S1f 브리지 절이 실제 쪽 기준·결속(공유 쪽 등급 일치)을 말한다 (occurrence-real-pages)', D.meta.page_basis.NCS === 'real' && ncs.includes('같은 실제 PDF 쪽') && ncs.includes('공유 쪽 ' + fmt(S.meta.run.reseg_agreement.pages) + '개의 등급 일치 ' + fmt(S.meta.run.reseg_agreement.agree) + '개'));
check('S1d 교과서도 같은 분석 흐름', common.every((x) => headings(school).includes(x)) && school.includes('교과서별 현황'));
check('S1e 공통 섹션의 상대 순서 일치 (NCS 만 브리지 절을 더 가진다)', JSON.stringify(headings(ncs).filter((h) => common.includes(h))) === JSON.stringify(headings(school).filter((h) => common.includes(h))), headings(ncs).join(' | '));
check('S1f NCS 출현건수 KPI == summary', [N.grades['1'], N.grades['2'], N.grades['3']].every((v) => ncs.includes(fmt(v))));
check('S1g 교과서 출현건수 KPI == summary', [T.grades['1'], T.grades['2'], T.grades['3']].every((v) => school.includes(fmt(v))));
check('S1h 페이지 분모 문구 없음', !ncs.includes('단위: 쪽') && !school.includes('단위: 쪽') && !school.includes('전체 2,055쪽 기준'));
check('S1i 키워드 상세에 등급 열', ncs.includes('등급1') && ncs.includes('등급2') && ncs.includes('등급3') && school.includes('등급1'));
check('S1j 확장 표현 표시', ncs.includes('화학 물질') && ncs.includes('개인 보호 장비'));
check('S1k NCS 페이지에 공통 렌더러 연결', ncsPage.includes("SEMANTIC_DASHBOARD_CORPUS='NCS'") && ncsPage.includes('semantic_grade_dashboard.js'));
check('S1l 교과서 페이지에 공통 렌더러 연결', schoolPage.includes("SEMANTIC_DASHBOARD_CORPUS='교과서'") && schoolPage.includes('semantic_recount_data.js') && schoolPage.includes('semantic_grade_dashboard.js'));
check('S1m 기존 페이지 화면은 실행되지 않는 템플릿으로 격리', ncsPage.includes('<template id="legacy-dashboard">') && schoolPage.includes('<template id="legacy-dashboard">'));
check('S1n 헤더 데이터 문구가 정본 xlsx·commit 을 인용', ncs.includes(D.meta.run.xlsx) && ncs.includes(D.meta.run.git_commit) && !ncs.includes('20260909'));
check('S1o 총계는 "레코드 합계(고유 문장·쪽 수 아님)" 로 명명 (m1)', ncs.includes('고유 문장·쪽 수') && school.includes('고유 문장·쪽 수'));
check('S1s 브리지 절의 해석 문단은 각주(.ts)가 아니라 본문 서체', /<p class="bridge-note"[^>]*>2026-09-13 부터/.test(ncs) && /<p class="bridge-note"[^>]*><strong>두 값의 차이/.test(ncs));
check('S1p NCS 에 브리지 절 — 이전 기준(페이지 단위) 표와 고정 문장', ncs.includes('이전 기준') && ncs.includes(fmt(R.pages) + '쪽') && ncs.includes(fmt(R.page_g['3'])) && ncs.includes('가중 방식의 차이') && ncs.includes(pct(R.page_g['3'], R.pages) + '%'));
check('S1q 교과서에는 NCS 브리지 표를 그리지 않는다', !school.includes('가중 방식의 차이'));
{ // S1r 렌더러 방어 분기 — previous_basis·run 이 없는 payload(--previous-basis 없이 만든 data.js)도 렌더된다
  const ctx2 = { document, console: ctx.console, JSON, Math, Object, Array, String, Number, Date, RegExp, Intl, parseInt, parseFloat, isNaN, setTimeout, clearTimeout, getComputedStyle: ctx.getComputedStyle, Chart };
  ctx2.window = ctx2; ctx2.globalThis = ctx2; vm.createContext(ctx2);
  const D2 = JSON.parse(JSON.stringify(D)); delete D2.meta.previous_basis; delete D2.meta.run; ctx2.SEMANTIC_RECOUNT = D2;
  vm.runInContext(renderer, ctx2, { filename: 'docs/semantic_grade_dashboard.js' });
  ctn.innerHTML = ''; ctx2.renderSemanticGradeDashboard('NCS'); const bare = ctn.innerHTML;
  check('S1r previous_basis·run 없는 payload — 브리지 절·데이터 문구·이전 기준 안내 없이 렌더', !bare.includes('이전 기준과의 관계') && !bare.includes('<strong>데이터</strong>') && !bare.includes('브리지 표를 보십시오') && bare.includes('전체 등급 분포'));
  ctn.innerHTML = '';
}

// ================================================================ S2 data ≡ summary
console.log('\n[S2] semantic_recount_data.js ≡ semantic_summary.json');
check('S2a JSON deep-equal', JSON.stringify(D) === JSON.stringify(S), 'data.js 와 summary.json 이 다르다 — 같은 실행에서 다시 생성할 것');
check('S2b 가드 통과 실행 (meta.run.expected true, force false, mismatch 없음)', S.meta.run.expected === true && S.meta.run.force === false && S.meta.run.expected_mismatch.length === 0, JSON.stringify(S.meta.run.expected_mismatch));
check('S2c data.js 첫 줄이 실행 manifest 를 인용하고 옛 파일명을 안 쓴다', dataJs.split('\n')[0].includes(S.meta.run.git_commit) && !dataJs.includes('20260909'));
check('S2d 실제 쪽 실행 — page_maps 84권 지문, reseg_agreement 100%, NCS 등급 출처 전부 real-page', S.meta.run.page_maps && S.meta.run.page_maps.files === 84 && /^[0-9a-f]{64}$/.test(S.meta.run.page_maps.sha256) && S.meta.run.reseg_agreement.pages > 2000 && S.meta.run.reseg_agreement.agree === S.meta.run.reseg_agreement.pages && N.grade_sources['real-page'] === N.total && N.grade_sources.existing === 0 && N.grade_sources.new === 0 && !dataJs.includes('/Users/'), JSON.stringify(S.meta.run.reseg_agreement));

// ================================================================ S3 summary 자체 정합
console.log('\n[S3] semantic_summary.json 자체 정합');
for (const [name, c] of [['NCS', N], ['교과서', T]]) {
  check('S3a ' + name + ' 등급 합 + 미확정 == total, graded == 등급 합', gsum(c.grades) + c.grades.unpaged === c.total && c.graded === gsum(c.grades), JSON.stringify(c.grades));
  check('S3b ' + name + ' 미확정 0 (연구책임자 결정 2026-09-13)', c.grades.unpaged === 0, c.grades.unpaged);
  check('S3c ' + name + ' 키워드 합 == corpus total', S.keywords.reduce((a, k) => a + k.corpora[name].total, 0) === c.total);
  check('S3d ' + name + ' 그룹 합 == corpus total, 그룹 문서 합 == documents', c.groups.reduce((a, g) => a + g.total, 0) === c.total && c.groups.reduce((a, g) => a + g.documents, 0) === c.documents);
}
check('S3e 문서 수 NCS 86 / 교과서 9', N.documents === 86 && T.documents === 9, N.documents + '/' + T.documents);
check('S3f 후보 판정 합 100, 포함 73 / 보류 21 (사전 v2: 방진화·케미컬 보류 전환)', Object.values(S.status).reduce((a, b) => a + b, 0) === 100 && S.status.included === 73 && S.status.held === 21, JSON.stringify(S.status));
check('S3g 등급 출처(existing/new/unpaged-*) 합 == total, 강제 배정 ≤ 5건', [N, T].every((c) => Object.values(c.grade_sources).reduce((a, b) => a + b, 0) === c.total && (c.grade_sources['unpaged-context'] + c.grade_sources['unpaged-fallback']) <= 5), JSON.stringify([N.grade_sources, T.grade_sources]));
// hwpx-ncs-section-refresh D1·D2 — 키워드×그룹 합 == 키워드 총계·등급, 그룹 pages(마커 최대값 합): 교과서 9권 합 == recount summary.json 의 total_pages
const RC = JSON.parse(read('docs/03-analysis/data/summary.json'));
const kwGroupErrors = [];
for (const k of S.keywords) for (const corpus of ['NCS', '교과서']) {
  const c = k.corpora[corpus]; const names = S.corpora[corpus].groups.map(g => g.name);
  if (!c.groups || c.groups.map(g => g.name).join('|') !== names.join('|')) { kwGroupErrors.push(k.name + ' ' + corpus + ' groups'); continue; }
  if (c.groups.reduce((a, g) => a + g.total, 0) !== c.total) kwGroupErrors.push(k.name + ' ' + corpus + ' total');
  for (const g of ['1', '2', '3', 'unpaged']) if (c.groups.reduce((a, x) => a + x.grades[g], 0) !== c.grades[g]) kwGroupErrors.push(k.name + ' ' + corpus + ' g' + g);
}
check('S3l 키워드×그룹 합 == 키워드 총계·등급 (NCS 4그룹 · 교과서 9그룹)', kwGroupErrors.length === 0, kwGroupErrors.slice(0, 3).join('; '));
check('S3m 그룹 pages: NCS 4그룹 > 0, 교과서 9그룹 합 == recount total_pages (2,055)', N.groups.every(g => g.pages > 0) && T.groups.reduce((a, g) => a + g.pages, 0) === RC.textbook.total_pages, T.groups.reduce((a, g) => a + g.pages, 0) + ' vs ' + RC.textbook.total_pages);
check('S3n NCS 그룹 pages 합 == reseg per_book.pdf_pages 합(84권) + 대응 없는 2권의 표식 최댓값 (D4)', N.groups.reduce((a, g) => a + g.pages, 0) === Object.values(R.per_book).reduce((a, b) => a + (b.pdf_pages || 0), 0) + 239 && S.meta.page_basis.NCS === 'real' && S.meta.page_basis['교과서'] === 'marker', N.groups.reduce((a, g) => a + g.pages, 0));
check('S3h 중복 제거 1건 기록 (LM1903060205)', S.meta.run.dedup.length === 1 && S.meta.run.dedup[0].code === 'LM1903060205' && S.meta.run.dedup[0].dropped.length === 1);
check('S3i 절대 경로·홈·본문 필드 없음', !/\/Users\/|\/home\/|relative_path|"context"/.test(JSON.stringify(S)));
check('S3j manifest 4종 해시 + 입력 6종(워크북 3·마크다운 2·이전 기준) sha256, 비단조 마커 경고는 레거시 1권뿐', ['source_sha256', 'rule_sha256', 'detail_sha256', 'summary_sha256'].every((k) => /^[0-9a-f]{64}$/.test(S.meta.manifest[k])) && S.meta.run.inputs.length === 6 && S.meta.run.inputs.some((i) => i.kind === '이전 기준') && S.meta.run.inputs.every((i) => /^[0-9a-f]{64}$/.test(i.sha256)) && S.meta.run.marker_nonmonotone.length === 1 && S.meta.run.marker_nonmonotone[0].includes('LM1903060113'), JSON.stringify(S.meta.run.marker_nonmonotone));
check('S3k 명령이 data_source 를 원본으로 쓰고 키워드 워크북이 20260402_재판정_20260414', S.meta.run.command.includes('--ncs-root data_source/markdown/ncs') && S.meta.run.command.includes('20260402_재판정_20260414.xlsx'));

// ================================================================ S4 이전 기준 계보 (옛 D13)
console.log('\n[S4] meta.previous_basis ≡ reseg_summary.json');
const P = S.meta.previous_basis;
check('S4a previous_basis (pages, page_g, books, cases_pages) == reseg', P && P.pages === R.pages && JSON.stringify(P.page_g) === JSON.stringify(R.page_g) && P.books === R.books && P.cases_pages === R.cases_pages, JSON.stringify(P));
check('S4b previous_basis.source 가 추적 파일을 가리킨다', P && P.source === 'docs/03-analysis/data/reseg_summary.json' && P.unit === 'pages');
check('S4c reseg 자체 정합 — 등급 합 == 쪽 수, meta.expected 있음, 교재 86', gsum(R.page_g) === R.pages && !!(R.meta && R.meta.expected) && R.books === 86);
check('S4d reseg.marker_offset 은 진단만 (moved 0, blocked 0, meta.marker_correct null) — 옛 D13q', R.marker_offset.moved === 0 && R.marker_offset.blocked === 0 && R.meta.marker_correct === null);

// ================================================================ S5 정적 화면
console.log('\n[S5] index.html · textbook.html 정적 화면');
const OLD = ['12,875', '4,869', '4,713', '2,480', '813건', '89개', '85개', '14,168', '20260909', '20260910', '20260911'];
const vNcs = visible(ncsPage), vSch = visible(schoolPage), tNcs = templateOf(ncsPage), tSch = templateOf(schoolPage);
check('S5a index.html .ctn 초기값 == summary (총계·등급1/2/3·미확정)', [N.total, N.grades['1'], N.grades['2'], N.grades['3']].every((v) => vNcs.includes('<div class="hs-v">' + fmt(v) + '</div>')) && vNcs.includes('<div class="hs-v">' + fmt(N.grades.unpaged) + '</div>'));
check('S5b textbook.html .ctn 초기값 == summary', [T.total, T.grades['1'], T.grades['2'], T.grades['3']].every((v) => vSch.includes('<div class="hs-v">' + fmt(v) + '</div>')));
check('S5c index.html 템플릿의 페이지 기준 KPI == reseg 이고 "이전 기준" 라벨', [R.page_g['1'], R.page_g['2'], R.page_g['3']].every((v, i) => tNcs.includes('>' + fmt(v) + '</div><div class="kpi-l">등급' + (i + 1))) && tNcs.includes(pct(R.page_g['3'], R.pages) + '% of ' + fmt(R.pages) + '쪽') && tNcs.includes('이전 기준'));
check('S5d index.html 템플릿의 출현 총계 == summary', tNcs.includes('id="hero-total">' + fmt(N.total + T.total) + '<') && tNcs.includes('>' + fmt(N.total) + '</div><div class="hs-l">NCS') && tNcs.includes('>' + fmt(T.total) + '</div><div class="hs-l">교과서') && tNcs.includes('>' + (N.documents + T.documents) + '</div><div class="hs-l">분석 문서'));
check('S5e textbook.html 템플릿 비교표 NCS 열 == reseg (이전 기준)', tSch.includes(fmt(R.pages) + '쪽') && tSch.includes(fmt(R.page_g['3']) + '쪽 (' + pct(R.page_g['3'], R.pages) + '%)') && tSch.includes('이전 기준'));
for (const [name, html] of [['index.html', ncsPage], ['textbook.html', schoolPage]]) {
  const hits = OLD.filter((s) => html.includes(s));
  check('S5f ' + name + ' 에 구 수치·구 파일명 0회', hits.length === 0, hits.join(' '));
  check('S5g ' + name + ' 문서 수 "86권"·"9권"', html.includes('86권') && html.includes('9권'));
}
check('S5h 옛 의미 렌더러 없음 — index.html 의 dead script, 참조 없는 docs/ncs_semantic_dashboard.js', !/D\.areas|semanticKb|NCS 89개/.test(ncsPage) && !fs.existsSync(path.join(ROOT, 'docs/ncs_semantic_dashboard.js')) && fs.readdirSync(path.join(ROOT, 'docs')).filter((f) => f.endsWith('.js')).sort().join(',') === 'semantic_grade_dashboard.js,semantic_recount_data.js', fs.readdirSync(path.join(ROOT, 'docs')).filter((f) => f.endsWith('.js')).join(','));

// ================================================================ S6 분리 분석 페이지
console.log('\n[S6] keyword-analysis.html · 결과 HTML 2건');
const ka = read('docs/keyword-analysis.html'), kn = read('docs/NCS_키워드검색결과.html'), kt = read('docs/교과서_키워드검색결과.html');
check('S6a 목차가 날짜 없는 결과 페이지 2건과 대시보드 2건에 링크', ka.includes('href="NCS_키워드검색결과.html"') && ka.includes('href="교과서_키워드검색결과.html"') && ka.includes('href="index.html"') && ka.includes('href="textbook.html"'));
check('S6b 목차 기준 파일·commit·교재 수 == manifest', ka.includes(S.meta.run.xlsx) && ka.includes(S.meta.run.git_commit) && ka.includes('NCS 교재 ' + N.documents + '권') && ka.includes('교과서 ' + T.documents + '권'));
check('S6c NCS 결과 페이지 총 건수 == summary', kn.includes('검색결과 전체: <strong>' + fmt(N.total) + '건</strong>'));
check('S6d 교과서 결과 페이지 총 건수 == summary', kt.includes('검색결과 전체: <strong>' + fmt(T.total) + '건</strong>'));
check('S6e 구 파일명·report 제외 문구 없음, 옛 날짜 파일 삭제됨', !/report제외|all_graded|20260911/.test(ka + kn.slice(0, 3000)) && !fs.existsSync(path.join(ROOT, 'docs/NCS_키워드검색결과_report제외_20260911.html')) && !fs.existsSync(path.join(ROOT, 'docs/교과서_키워드검색결과_20260911.html')) && !fs.existsSync(path.join(ROOT, 'docs/semantic_recount_data_20260910_all_graded.js')));

// ================================================================ S7 README
console.log('\n[S7] README.md');
const readme = read('README.md');
check('S7a 핵심 수치 == summary (등급3 출현 비율 NCS·교과서, 분모)', readme.includes('NCS ' + pct(N.grades['3'], N.graded) + '%') && readme.includes('교과서 ' + pct(T.grades['3'], T.graded) + '%') && readme.includes(fmt(N.grades['3']) + '/' + fmt(N.graded)) && readme.includes(fmt(T.grades['3']) + '/' + fmt(T.graded)));
check('S7b "이전 기준" 문장 == reseg (145/2,189, 6.6%)', readme.includes('이전 기준') && readme.includes(R.page_g['3'] + '/' + fmt(R.pages)) && readme.includes(pct(R.page_g['3'], R.pages) + '%'));
check('S7c 구 문구 없음 (85개 자료, report 제외) · 교재 86권', !readme.includes('85개') && !readme.includes('report 자료') && readme.includes('86권'));
check('S7d 재생성 절에 정본 명령·shift_page_markers·data_source', readme.includes('semantic_keyword_recount.py') && readme.includes('--ncs-root data_source/markdown/ncs') && readme.includes('shift_page_markers.py') && readme.includes('data_source'));
check('S7e 의미 출현 총계 == summary', readme.includes(fmt(N.total) + '건') && readme.includes(fmt(T.total) + '건'));
const readLine = readme.split('\n').find((l) => l.startsWith('그래서 ') && l.includes('이렇게까지만')) || '';
check('S7g "이렇게까지만 읽어야" 문장의 등급3 비율 == summary·reseg (구 20.8% 아님)', readLine.includes(pct(N.grades['3'], N.graded) + '%(이전 기준 ' + pct(R.page_g['3'], R.pages) + '%)') && !readme.includes('20.8%(이전 기준'));
// 추적 분석 문서의 말뭉치별 키워드 순위표 — 30행 × 2, 순위·출현·정확/동등/구체·등급1/2/3 전부 summary.keywords 와 같아야 한다
const skr = read('docs/03-analysis/semantic-keyword-recount.analysis.md');
const rankBlock = skr.split('## Keyword ranking by corpus')[1] || '';
const rankErrors = [];
for (const corpus of ['NCS', '교과서']) {
  const part = (rankBlock.split('### ' + corpus)[1] || '').split('### ')[0];
  const rows = part.split('\n').filter(l => /^\| \d+ \| `/.test(l)).map(l => l.split('|').map(c => c.trim()));
  const want = S.keywords.map(k => ({ name: k.name, c: k.corpora[corpus] })).sort((a, b) => b.c.total - a.c.total || S.keywords.findIndex(k => k.name === a.name) - S.keywords.findIndex(k => k.name === b.name));
  if (rows.length !== want.length) rankErrors.push(corpus + ' rows ' + rows.length);
  rows.forEach((r, i) => {
    const w = want[i]; if (!w) return;
    const got = [r[1], r[2].replace(/`/g, ''), r[3], r[6], r[7], r[8], r[9], r[10], r[11]].join('|');
    const exp = [String(i + 1), w.name, fmt(w.c.total), fmt(w.c.exact), fmt(w.c.equivalent), fmt(w.c.specific), fmt(w.c.grades['1']), fmt(w.c.grades['2']), fmt(w.c.grades['3'])].join('|');
    if (got !== exp) rankErrors.push(corpus + ' ' + got + ' != ' + exp);
  });
  const total = part.match(/\| 합계 \| \| ([\d,]+) \|/);
  if (!total || total[1] !== fmt(S.corpora[corpus].total)) rankErrors.push(corpus + ' 합계 ' + (total && total[1]));
}
check('S7f semantic-keyword-recount.analysis.md 키워드 순위표 (NCS·교과서 30행) == summary.keywords', rankErrors.length === 0, rankErrors.slice(0, 3).join('; '));

// ================================================================ S8 CLAUDE.md
console.log('\n[S8] CLAUDE.md');
const claude = read('CLAUDE.md');
check('S8a 출현건수 분모 예외 문단 (연구책임자 2026-09-13) — 예시 수치 == summary', claude.includes('occurrence count') && claude.includes('2026-09-13') && claude.includes('previous basis') && claude.includes(pct(N.grades['3'], N.graded) + '% of graded occurrences') && claude.includes(fmt(N.grades['3']) + '/' + fmt(N.graded)), pct(N.grades['3'], N.graded));
check('S8b data_source 트랩 · semantic_keyword_recount.py 절 · shift_page_markers.py', claude.includes('data_source') && claude.includes('semantic_keyword_recount.py') && claude.includes('shift_page_markers.py') && claude.includes('semantic_summary.json'));

// ================================================================ S9 인용 단언 수 (옛 D14)
console.log('\n[S9] 문서가 인용한 단언 수');
{
  const total = pass + fail + 1;
  const cited = [...(readme + claude).matchAll(/test-dashboard-data\.js\s+# (\d+)/g)].map((m) => +m[1]);
  check('S9 README·CLAUDE.md 의 test-dashboard-data.js 단언 수 == ' + total, cited.length === 2 && cited.every((n) => n === total), cited.join('/'));
}

console.log(`\n결과: ${pass}/${pass + fail} PASS${fail ? `, ${fail} FAIL` : ''}${warned ? `, ${warned} KNOWN ISSUE` : ''}`);
process.exit(fail ? 1 : 0);
