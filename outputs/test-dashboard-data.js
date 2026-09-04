#!/usr/bin/env node
/**
 * 대시보드 데이터 정합성 + 표 렌더/정렬 회귀 테스트 — grade-recount-unify
 *
 * docs/index.html · docs/textbook.html 의 실제 <script> 를 Node vm + DOM mock 으로
 * 로드해(수동 복사 부채 0) 다음을 검증한다.
 *
 *   실행: node outputs/test-dashboard-data.js
 *   PASS 시 exit 0, FAIL 시 exit 1 (CI 친화)
 *
 * 커버:
 *   D1 KW 합계 == 페이지 내 exp (브라우저 IIFE 를 하드 assert 로 승격)
 *   D2 KW 합계 == recount_grades.py 산출물(summary.json) 교차검증
 *   D3 pg(검출쪽) 필드 무결성 — 신규 컬럼, IIFE 미검증 구간
 *   D4 차트 하드코딩 수치 == summary.json
 *   D5 rKT() 렌더 — 신규 검출쪽 컬럼 출력/셀 수
 *   D6 sK() 정렬 토글 — pg 포함 전 컬럼 × 오름/내림
 *   D7 fK() 필터 (high / case / detected)
 *   D8 CSV 산출물 == summary.json (행수·등급분포)
 */
const fs = require('fs'), vm = require('vm'), path = require('path');

const ROOT = path.join(__dirname, '..');
let pass = 0, fail = 0;
let warned = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; console.log('  ✗ ' + name + (extra ? ' — ' + extra : '')); }
}
// 기지(旣知) 결함: 고치기 전까지 exit code 를 막지 않되 매 실행마다 크게 노출한다
function known(name, cond, note) {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { warned++; console.log('  ⚠ KNOWN ISSUE ' + name + '\n      → ' + note); }
}

// ---------- DOM/Chart mock 위에서 대시보드 <script> 실행 ----------
function loadDash(file) {
  const html = fs.readFileSync(file, 'utf8');
  const js = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
  const els = {};                       // id -> {innerHTML, ...}
  const mkEl = (id) => {
    const el = {
      id, innerHTML: '', textContent: '', style: {}, dataset: {},
      classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
      getAttribute() { return null; }, setAttribute() {}, appendChild() {}, replaceChild() {},
      addEventListener() {}, closest() { return null; }, click() {}
    };
    // canvas 교체(RC)용 부모 스텁 — 순환 참조를 피해 지연 생성
    let parent = null;
    Object.defineProperty(el, 'parentNode', {
      get() { return parent || (parent = { replaceChild() {}, appendChild() {} }); }
    });
    return el;
  };
  const getEl = (id) => (els[id] || (els[id] = mkEl(id)));
  const errors = [];
  const document = {
    documentElement: { className: '', style: {} },
    getElementById: getEl, querySelector: () => mkEl('q'), querySelectorAll: () => [],
    createElement: (t) => mkEl('new-' + t), addEventListener: () => {}, body: mkEl('body')
  };
  // 정렬 헤더 스텁 — 열 목록을 손으로 적지 않고 마크업의 data-k 에서 뽑는다.
  // 페이지에 열이 늘면 스텁도 따라 늘어나므로 사본을 유지할 필요가 없다.
  const sortThs = [...html.matchAll(/<th data-k="([^"]+)"/g)].map((m) => {
    const attrs = {};
    return {
      dataset: { k: m[1] },
      setAttribute(n, v) { attrs[n] = v; },
      getAttribute(n) { return n in attrs ? attrs[n] : null; },
    };
  });
  document.querySelectorAll = (sel) => (sel === '.tbl.sortable th[data-k]' ? sortThs : []);
  const ctx = {
    document, JSON, Math, Object, Array, String, Number, Date, RegExp, Intl,
    parseInt, parseFloat, isNaN, setTimeout, clearTimeout, performance: { now: () => 0 },
    requestAnimationFrame: () => {}, localStorage: { getItem: () => null, setItem: () => {} },
    // Chart 를 mock 하면 buildCharts() 가 실제로 실행되어 데이터셋을 캡처할 수 있다
    charts: [],
    console: { log: () => {}, error: (...a) => errors.push(a.join(' ')), warn: () => {} },
    getComputedStyle: () => ({ getPropertyValue: () => '#000' }),
    matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
    htmlToImage: { toPng: () => Promise.resolve('') }
  };
  ctx.destroyed = [];
  ctx.Chart = function (el, cfg) { ctx.charts.push(cfg); ctx.live[el && el.id] = { destroy() { ctx.destroyed.push(el.id); } }; };
  ctx.Chart.defaults = { animation: false };
  ctx.live = {};
  // Chart.js v4 API — buildCharts 가 재빌드 전 기존 인스턴스를 destroy 하는지 검증하기 위해 필요
  ctx.Chart.getChart = (id) => ctx.live[id];
  ctx.window = ctx; ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(js, ctx, { filename: file });
  ctx.__els = els; ctx.__errors = errors; ctx.__sortThs = sortThs;
  return ctx;
}

const sum = (arr, f) => arr.reduce((a, b) => a + (b[f] || 0), 0);
const cells = (html) => (html.match(/<td/g) || []).length;
const rows = (html) => (html.match(/<tr>/g) || []).length;
// rKT() 가 만든 <tbody> 에서 키워드 순서 추출
const order = (html) => [...html.matchAll(/<strong>([^<]+)<\/strong>/g)].map(m => m[1]);

const summary = JSON.parse(fs.readFileSync(path.join(ROOT, 'docs/03-analysis/data/summary.json'), 'utf8'));

// =====================================================================
// docs/index.html (NCS)
// =====================================================================
console.log('\n[NCS] docs/index.html');
const N = loadDash(path.join(ROOT, 'docs/index.html'));
const NKW = N.KW;

check('D1a KW 30개 키워드', NKW.length === 30, 'got ' + NKW.length);
check('D1b 로드 시 검증 IIFE 가 콘솔 에러 0건', N.__errors.length === 0, N.__errors.join(' | '));
['t', 'g1', 'g2', 'g3', 'dev', 'mfg', 'eq', 'mat', 'cs'].forEach(f => {
  check('D1c 합계 필드 ' + f + ' 존재/숫자', NKW.every(r => typeof r[f] === 'number'));
});
check('D1d 등급합 == 총건수', sum(NKW, 'g1') + sum(NKW, 'g2') + sum(NKW, 'g3') === sum(NKW, 't'));
check('D1e 영역합 == 총건수', sum(NKW, 'dev') + sum(NKW, 'mfg') + sum(NKW, 'eq') + sum(NKW, 'mat') === sum(NKW, 't'));

check('D2a 총건수 == summary.ncs.rows(7,769)', sum(NKW, 't') === summary.ncs.rows, sum(NKW, 't'));
check('D2b 등급1 행수 == summary.ncs.row_g[1]', sum(NKW, 'g1') === summary.ncs.row_g['1']);
check('D2c 등급2 행수 == summary.ncs.row_g[2]', sum(NKW, 'g2') === summary.ncs.row_g['2']);
check('D2d 등급3 행수 == summary.ncs.row_g[3]', sum(NKW, 'g3') === summary.ncs.row_g['3']);
check('D2e 사고사례 행수 == summary.ncs.cases_rows(28)', sum(NKW, 'cs') === summary.ncs.cases_rows);

// D3 — 신규 pg 컬럼: IIFE 가 검증하지 않는 구간
check('D3a 전 키워드가 pg 보유(숫자)', NKW.every(r => typeof r.pg === 'number'), 'rKT 가 r.pg.toLocaleString() 를 무가드 호출');
check('D3b pg <= t (검출쪽은 검출건수를 넘을 수 없음)', NKW.every(r => r.pg <= r.t), NKW.filter(r => r.pg > r.t).map(r => r.k).join(','));
check('D3c t>0 이면 pg>0', NKW.every(r => r.t === 0 || r.pg > 0));
check('D3d 최대 pg <= 고유 검출쪽 총계(1,847)', Math.max(...NKW.map(r => r.pg)) <= summary.ncs.pages);
check('D3e pg 합 >= 고유쪽수 (키워드 중복 계수)', sum(NKW, 'pg') >= summary.ncs.pages);
check('D3e2 키워드별 pg == summary.ncs.kw_pages (독립 대조)',
  NKW.every(r => r.pg === (summary.ncs.kw_pages[r.k] || 0)),
  NKW.filter(r => r.pg !== (summary.ncs.kw_pages[r.k] || 0)).map(r => r.k + ':' + r.pg).join(','));

// D4 — 차트 하드코딩 수치
N.buildCharts();
const chartsAfterFirst = N.charts.length;
N.buildCharts();                                   // 테마 전환 시뮬레이션
check('D10 테마 재빌드 시 기존 Chart 인스턴스를 destroy (누수 방지)',
  N.destroyed.length === chartsAfterFirst,
  'destroyed=' + N.destroyed.length + ' / 기대=' + chartsAfterFirst);
N.charts.length = chartsAfterFirst;                // 이후 어서션은 1회분 기준
const nDough = N.charts.find(c => c.type === 'doughnut');
check('D4a 등급 도넛 == summary.ncs.page_g [1267,472,108]',
  JSON.stringify(nDough.data.datasets[0].data) === JSON.stringify([summary.ncs.page_g['1'], summary.ncs.page_g['2'], summary.ncs.page_g['3']]),
  JSON.stringify(nDough.data.datasets[0].data));
check('D4b 도넛 합계 == summary.ncs.pages(1,847)',
  nDough.data.datasets[0].data.reduce((a, b) => a + b, 0) === summary.ncs.pages);

// c3 = 영역별 등급 스택(개발/제조/장비/재료) — 영역 단위 하드코딩 수치의 유일한 기계 검증점
const c3 = N.charts.find(c => c.type === 'bar' && /등급1/.test(c.data.datasets[0].label));
const c3d = c3.data.datasets.map(d => d.data);
check('D4e c3 영역별 등급1 합 == page_g[1](1,267)',
  c3d[0].reduce((a, b) => a + b, 0) === summary.ncs.page_g['1'], c3d[0].reduce((a, b) => a + b, 0));
check('D4f c3 영역별 등급2 합 == page_g[2](472)',
  c3d[1].reduce((a, b) => a + b, 0) === summary.ncs.page_g['2'], c3d[1].reduce((a, b) => a + b, 0));
check('D4g c3 영역별 등급3 합 == page_g[3](108)',
  c3d[2].reduce((a, b) => a + b, 0) === summary.ncs.page_g['3'], c3d[2].reduce((a, b) => a + b, 0));
const areaPages = c3d[0].map((_, i) => c3d[0][i] + c3d[1][i] + c3d[2][i]);   // 개발,제조,장비,재료
check('D4h 영역 페이지 합 == summary.ncs.pages(1,847)',
  areaPages.reduce((a, b) => a + b, 0) === summary.ncs.pages, areaPages.join('/'));

// c1 = 안전관련(등급2+3) 비율 — 라벨 순서가 c3 와 반대(재료/제조/장비/개발)
const c1 = N.charts.find(c => c.type === 'bar' && /안전관련/.test(c.data.datasets[0].label));
const idxOf = { 개발: 0, 제조: 1, 장비: 2, 재료: 3 };
check('D4i c1 비율 == (등급2+등급3)/영역쪽수 (소수 1자리)',
  c1.data.labels.every((lb, i) => {
    const j = idxOf[lb.replace('반도체', '')];
    return Math.abs(c1.data.datasets[0].data[i] - (c3d[1][j] + c3d[2][j]) / areaPages[j] * 100) < 0.05;
  }), JSON.stringify(c1.data.datasets[0].data));

// 영역 카드(HTML 하드코딩) ↔ KW 영역 합계
const idxHtml = fs.readFileSync(path.join(ROOT, 'docs/index.html'), 'utf8');
const cardHits = [...idxHtml.matchAll(/<h3>반도체(개발|제조|장비|재료)<\/h3>[\s\S]*?검출 ([\d,]+)쪽\(([\d,]+)건\)/g)]
  .map(m => ({ a: m[1], pg: +m[2].replace(/,/g, ''), t: +m[3].replace(/,/g, '') }));
check('D4j 영역 카드 4장 파싱', cardHits.length === 4, cardHits.length);
check('D4k 영역 카드 검출쪽 == c3 영역 합계',
  cardHits.every(h => h.pg === areaPages[idxOf[h.a]]),
  JSON.stringify(cardHits.map(h => h.pg)) + ' vs ' + JSON.stringify(areaPages));
const kwArea = { 개발: sum(NKW, 'dev'), 제조: sum(NKW, 'mfg'), 장비: sum(NKW, 'eq'), 재료: sum(NKW, 'mat') };
check('D4l 영역 카드 검출건수 == KW 영역별 합계',
  cardHits.every(h => h.t === kwArea[h.a]),
  JSON.stringify(cardHits.map(h => h.a + ':' + h.t)) + ' vs ' + JSON.stringify(kwArea));

// D5/D6/D7 — rKT / sK / fK
N.rKT();
let kb = N.__els['kb'].innerHTML;
check('D5a rKT 30행 렌더', rows(kb) === 30, rows(kb));
check('D5b 행당 9셀 (검출쪽 컬럼 추가 후)', cells(kb) === 30 * 9, cells(kb) / 30);
check('D5c 첫 행에 검출쪽 1,308 출력', /<td>3,405<\/td><td>1,308<\/td>/.test(kb));
check('D5d 예외 없이 전 키워드 렌더', order(kb).length === 30);

const before = order(kb);
N.sK('pg');                                     // 신규 컬럼 첫 클릭 → 내림차순
let pgDesc = order(N.__els['kb'].innerHTML);
check('D6a sK("pg") 내림차순', pgDesc.every((k, i, a) => i === 0 ||
  NKW.find(r => r.k === a[i - 1]).pg >= NKW.find(r => r.k === k).pg), pgDesc.slice(0, 3).join(','));
N.sK('pg');                                     // 재클릭 → 오름차순 토글
let pgAsc = order(N.__els['kb'].innerHTML);
check('D6b sK("pg") 재클릭 시 오름차순 토글', pgAsc.every((k, i, a) => i === 0 ||
  NKW.find(r => r.k === a[i - 1]).pg <= NKW.find(r => r.k === k).pg));
check('D6c 토글 결과가 서로 역순', pgDesc[0] === pgAsc[pgAsc.length - 1]);
['t', 'dev', 'mfg', 'eq', 'mat', 'g3', 'cs'].forEach(col => {
  N.sK(col);
  const o = order(N.__els['kb'].innerHTML);
  check('D6d sK("' + col + '") 30행 유지 + 정렬 단조',
    o.length === 30 && o.every((k, i, a) => i === 0 ||
      (NKW.find(r => r.k === a[i - 1])[col] || 0) >= (NKW.find(r => r.k === k)[col] || 0)));
});
N.sK('k');
check('D6e sK("k") 키워드 문자열 정렬', order(N.__els['kb'].innerHTML).length === 30);

// D6f-D6i — aria-sort 가 실제 정렬 상태와 일치하는지.
// 헤더의 화살표 글리프는 CSS 가 aria-sort 만 보고 그리므로, 이 속성이 어긋나면
// 화면과 스크린리더가 서로 다른 말을 하게 된다. 선언만 보지 않고 렌더된 행
// 순서까지 대조해야 "descending 이라고 써 놓고 오름차순으로 그리는" 경우를 잡는다.
const ariaOf = (ctx, key) => {
  const th = ctx.__sortThs.find(t => t.dataset.k === key);
  return th ? th.getAttribute('aria-sort') : null;
};
check('D6s1 정렬 헤더 스텁을 마크업에서 뽑았다', N.__sortThs.length === 9, N.__sortThs.length);
N.sK('pg');
check('D6s2 sK("pg") 활성 열 aria-sort=descending', ariaOf(N, 'pg') === 'descending', ariaOf(N, 'pg'));
check('D6s3 비활성 열은 전부 aria-sort=none',
  N.__sortThs.filter(t => t.dataset.k !== 'pg').every(t => t.getAttribute('aria-sort') === 'none'));
// 렌더된 행에서 실제 방향을 되읽어, 선언된 aria-sort 와 대조한다. 정렬 순서만
// 보는 어서션은 라벨이 뒤집혀도 통과하므로(뮤테이션으로 확인) 대조가 필요하다.
const dirOf = (keys, field) => {
  const v = keys.map(k => NKW.find(r => r.k === k)[field]);
  const nonInc = v.every((x, i) => i === 0 || v[i - 1] >= x);
  const nonDec = v.every((x, i) => i === 0 || v[i - 1] <= x);
  if (nonInc && nonDec) return 'flat';        // 값이 전부 같으면 방향을 못 읽는다
  return nonInc ? 'descending' : nonDec ? 'ascending' : 'unsorted';
};
const nDesc = order(N.__els['kb'].innerHTML);
check('D6s4 내림차순 선언이 렌더된 행 방향과 일치',
  ariaOf(N, 'pg') === dirOf(nDesc, 'pg'), ariaOf(N, 'pg') + ' vs 실제 ' + dirOf(nDesc, 'pg'));
N.sK('pg');                                   // 같은 열 재클릭 → 토글
check('D6s5 같은 열 재클릭 시 aria-sort=ascending', ariaOf(N, 'pg') === 'ascending', ariaOf(N, 'pg'));
const nAsc = order(N.__els['kb'].innerHTML);
check('D6s6 오름차순 선언이 렌더된 행 방향과 일치',
  ariaOf(N, 'pg') === dirOf(nAsc, 'pg'), ariaOf(N, 'pg') + ' vs 실제 ' + dirOf(nAsc, 'pg'));

// fK 는 눌린 버튼에 aria-pressed 를 쓴다. 스텁이 attrs 에 받아 둬야
// 그 호출이 실제로 일어났는지 확인할 수 있다.
const fakeBtn = {
  attrs: {},
  classList: { add() {}, remove() {} },
  setAttribute(k, v) { this.attrs[k] = v; },
};
N.fK('case', fakeBtn);
const caseOnly = order(N.__els['kb'].innerHTML);
check('D7a fK("case") cs>0 만 노출', caseOnly.length === NKW.filter(r => r.cs > 0).length, caseOnly.length);
N.fK('high', fakeBtn);
check('D7b fK("high") 상위 15개', order(N.__els['kb'].innerHTML).length === 15);
N.fK('all', fakeBtn);
check('D7c fK("all") 전체 복귀', order(N.__els['kb'].innerHTML).length === 30);
check('D7f fK() 가 누른 버튼에 aria-pressed=true', fakeBtn.attrs['aria-pressed'] === 'true', fakeBtn.attrs['aria-pressed']);

// =====================================================================
// docs/textbook.html (교과서)
// =====================================================================
console.log('\n[교과서] docs/textbook.html');
const T = loadDash(path.join(ROOT, 'docs/textbook.html'));
const TKW = T.KW;

check('D1f 로드 시 검증 IIFE 가 콘솔 에러 0건', T.__errors.length === 0, T.__errors.join(' | '));
check('D1g 등급합 == 총건수', sum(TKW, 'g1') + sum(TKW, 'g2') + sum(TKW, 'g3') === sum(TKW, 't'));
check('D2f 총건수 == summary.textbook.rows(981)', sum(TKW, 't') === summary.textbook.rows, sum(TKW, 't'));
check('D2g 등급1 == row_g[1](557)', sum(TKW, 'g1') === summary.textbook.row_g['1']);
check('D2h 등급2 == row_g[2](360)', sum(TKW, 'g2') === summary.textbook.row_g['2']);
check('D2i 등급3 == row_g[3](64)', sum(TKW, 'g3') === summary.textbook.row_g['3']);
check('D2j 사고사례 0건 == cases_rows', sum(TKW, 'cs') === summary.textbook.cases_rows);

check('D3f 전 키워드가 pg 보유(숫자)', TKW.every(r => typeof r.pg === 'number'));
check('D3g pg <= t', TKW.every(r => r.pg <= r.t), TKW.filter(r => r.pg > r.t).map(r => r.k).join(','));
check('D3h t==0 이면 pg==0', TKW.every(r => r.t !== 0 || r.pg === 0));
check('D3i 최대 pg <= 검출쪽 총계(362)', Math.max(...TKW.map(r => r.pg)) <= summary.textbook.pages);
check('D3i2 키워드별 pg == summary.textbook.kw_pages (독립 대조)',
  TKW.every(r => r.pg === (summary.textbook.kw_pages[r.k] || 0)),
  TKW.filter(r => r.pg !== (summary.textbook.kw_pages[r.k] || 0)).map(r => r.k + ':' + r.pg).join(','));

T.buildCharts();
const tDough = T.charts.find(c => c.type === 'doughnut');
check('D4c 등급 도넛 == page_g + 미검출 [309,45,8,1693]',
  JSON.stringify(tDough.data.datasets[0].data) === JSON.stringify([
    summary.textbook.page_g['1'], summary.textbook.page_g['2'], summary.textbook.page_g['3'],
    summary.textbook.undetected_pages]),
  JSON.stringify(tDough.data.datasets[0].data));
check('D4d 도넛 합계 == 전체 2,055쪽',
  tDough.data.datasets[0].data.reduce((a, b) => a + b, 0) === summary.textbook.total_pages);

T.rKT();
kb = T.__els['kb'].innerHTML;
check('D5e rKT 30행 렌더', rows(kb) === 30);
check('D5f 행당 8셀 (검출쪽 컬럼 추가 후)', cells(kb) === 30 * 8, cells(kb) / 30);
check('D5g 검출쪽 비율이 pg 기준(209/2055=10.2%)', /<td>408<\/td><td>209<\/td>/.test(kb) && /10\.2%/.test(kb));

T.sK('tp');   // 검출쪽 비율 정렬 = pg 정렬과 동치여야 함 (첫 클릭 → 내림차순)
const tpOrder = order(T.__els['kb'].innerHTML);
T.sK('pg');   // kS 가 바뀌므로 역시 첫 클릭 = 내림차순
const pgOrder = order(T.__els['kb'].innerHTML);
check('D6f sK("tp") 는 pg 정렬과 동치(tp = pg/2055 단조)',
  JSON.stringify(tpOrder.map(k => TKW.find(r => r.k === k).pg)) ===
  JSON.stringify(pgOrder.map(k => TKW.find(r => r.k === k).pg)));
T.fK('detected', fakeBtn);
check('D7d fK("detected") t>0 만 노출',
  order(T.__els['kb'].innerHTML).length === TKW.filter(r => r.t > 0).length);
T.fK('all', fakeBtn);
check('D7e fK("all") 전체 복귀', order(T.__els['kb'].innerHTML).length === 30);

// =====================================================================
// D8 — CSV 산출물 ↔ summary.json
// =====================================================================
console.log('\n[산출물] docs/03-analysis/data/*.csv');
function readCsv(p) {
  const txt = fs.readFileSync(path.join(ROOT, p), 'utf8').replace(/^﻿/, '');
  // 등급사유에 콤마/따옴표가 있어 간이 파서 사용
  const out = []; let row = [], cur = '', q = false;
  for (let i = 0; i < txt.length; i++) {
    const c = txt[i];
    if (q) { if (c === '"' && txt[i + 1] === '"') { cur += '"'; i++; } else if (c === '"') q = false; else cur += c; }
    else if (c === '"') q = true;
    else if (c === ',') { row.push(cur); cur = ''; }
    else if (c === '\n') { row.push(cur); out.push(row); row = []; cur = ''; }
    else if (c !== '\r') cur += c;
  }
  if (cur || row.length) { row.push(cur); out.push(row); }
  return out.filter(r => r.length > 1);
}
const ncsCsv = readCsv('docs/03-analysis/data/ncs_pages.csv');
const txtCsv = readCsv('docs/03-analysis/data/txt_pages.csv');
const gradeCol = (csv, i) => csv.slice(1).reduce((m, r) => (m[r[i]] = (m[r[i]] || 0) + 1, m), {});

check('D8a ncs_pages.csv 행수 == summary.ncs.pages(1,847)', ncsCsv.length - 1 === summary.ncs.pages, ncsCsv.length - 1);
const ng = gradeCol(ncsCsv, 3);
check('D8b ncs_pages.csv 등급 분포 == page_g',
  +ng['1'] === summary.ncs.page_g['1'] && +ng['2'] === summary.ncs.page_g['2'] && +ng['3'] === summary.ncs.page_g['3'],
  JSON.stringify(ng));
check('D8c ncs_pages.csv 사고사례 == cases_pages(8)',
  ncsCsv.slice(1).filter(r => r[5] === '예').length === summary.ncs.cases_pages,
  'CSV 사고사례 "예" ' + ncsCsv.slice(1).filter(r => r[5] === '예').length + '행 vs summary ' + summary.ncs.cases_pages + '쪽. '
  + 'recount_grades.aggregate() 의 by_page[(fn,page)]=x 가 페이지별 "마지막 행"만 남겨 '
  + '사고사례·등급·등급사유가 그 행 값으로 덮인다(쪽당 평균 4.2행). '
  + '대시보드가 강조하는 "사고사례 8쪽"을 CSV 로 재현할 수 없음.');
check('D8d ncs_pages.csv 교재 수 == books(86)',
  new Set(ncsCsv.slice(1).map(r => r[1])).size === summary.ncs.books);
check('D8e ncs_pages.csv 영역 4종', new Set(ncsCsv.slice(1).map(r => r[0])).size === 4);
check('D8f ncs_pages.csv (교재,페이지) 유일', new Set(ncsCsv.slice(1).map(r => r[1] + '#' + r[2])).size === summary.ncs.pages);

check('D8g txt_pages.csv 행수 == summary.textbook.pages(362)', txtCsv.length - 1 === summary.textbook.pages, txtCsv.length - 1);
const tg = gradeCol(txtCsv, 2);
check('D8h txt_pages.csv 등급 분포 == page_g',
  +tg['1'] === summary.textbook.page_g['1'] && +tg['2'] === summary.textbook.page_g['2'] && +tg['3'] === summary.textbook.page_g['3'],
  JSON.stringify(tg));
check('D8i txt_pages.csv 교재 수 == books(9)', new Set(txtCsv.slice(1).map(r => r[0])).size === summary.textbook.books);
check('D8j txt_pages.csv 에 NCS 잔여행(LM…) 없음', txtCsv.slice(1).every(r => !/^LM\d/.test(r[0])));
check('D8k 미검출쪽 == 2,055 - 362', summary.textbook.total_pages - summary.textbook.pages === summary.textbook.undetected_pages);

// 절단 열은 커밋된 CSV 와 summary.json 을 서로 묶어 둔다. 한쪽만 재생성되거나
// page_record() 의 OR 접기가 깨지면 CSV 는 전부 '아니오' 인데 summary 는 16 을
// 주장하는 상태가 되는데, 이 대조가 없으면 CI 전체가 그대로 통과한다.
const cutCol = (csv) => csv.slice(1).filter(r => r[r.length - 1] === '예');
const ncsCut = cutCol(ncsCsv), txtCut = cutCol(txtCsv);
check('D8l ncs_pages.csv 절단 열 == summary.ncs.truncated_pages(16)',
  ncsCut.length === summary.ncs.truncated_pages,
  'CSV ' + ncsCut.length + '쪽 vs summary ' + summary.ncs.truncated_pages + '쪽');
check('D8m ncs_pages.csv 절단쪽 등급 분포 == truncated_page_g',
  [1, 2, 3].every(g => ncsCut.filter(r => +r[3] === g).length === summary.ncs.truncated_page_g[g]),
  JSON.stringify([1, 2, 3].map(g => ncsCut.filter(r => +r[3] === g).length)));
check('D8n 절단은 등급3 에 몰려 있다 (등급1 은 0쪽) — 무작위가 아니라는 근거',
  summary.ncs.truncated_page_g['1'] === 0 && summary.ncs.truncated_page_g['3'] === 12);
check('D8o txt_pages.csv 절단 0쪽 (교과서 워크북에는 셀 한도 절단이 없다)',
  txtCut.length === 0 && summary.textbook.truncated_pages === 0, txtCut.length);
check('D8p 절단 열 값은 예/아니오 뿐',
  ncsCsv.slice(1).concat(txtCsv.slice(1)).every(r => ['예', '아니오'].includes(r[r.length - 1])));

// =====================================================================
// D9 — docs/osha.html 본문 인용 수치 (텍스트 전용 diff, 썩기 쉬운 구간)
// =====================================================================
console.log('\n[인용] docs/osha.html');
const osha = fs.readFileSync(path.join(ROOT, 'docs/osha.html'), 'utf8');
const num = (n) => n.toLocaleString('en-US');
[
  ['NCS 검출쪽 1,847', num(summary.ncs.pages) + '쪽'],
  ['NCS 검출건수 7,769', num(summary.ncs.rows) + '건'],
  ['교과서 검출쪽 362', num(summary.textbook.pages) + '쪽'],
  ['교과서 검출건수 981', num(summary.textbook.rows) + '건'],
  ['NCS 등급3 108쪽', '108쪽'],
].forEach(([label, needle]) => {
  check('D9 osha.html 이 ' + label + ' 인용', osha.includes(needle), needle);
});
check('D9 osha.html 에 구(舊) 사고사례 "7건" 잔존 없음', !/사고사례[^<]{0,12}7건/.test(osha));
check('D9 osha.html 에 구(舊) 교과서 "982건" 잔존 없음', !osha.includes('982건'));
check('D9a index.html 이 등급3 108쪽 인용', idxHtml.includes('108'));

// =====================================================================
// D11 — 가로 스크롤 영역의 구조 회귀
//
// .scroll-x 를 .card 와 같은 요소에 얹으면 스타일시트에서 뒤에 오는 .card 의
// background 가(특이도 동률) 그라데이션을 통째로 덮어 어포던스가 사라진다.
// 실제로 그렇게 짰다가 실측 backgroundImage 레이어 0 으로 잡혔고, 그때 이
// 하니스는 아무 것도 눈치채지 못했다. 구조 자체를 고정한다.
// =====================================================================
console.log('\n[구조] 가로 스크롤 영역');
const PAGES = ['docs/index.html', 'docs/textbook.html', 'docs/osha.html']
  .map(rel => [rel, fs.readFileSync(path.join(ROOT, rel), 'utf8')]);
PAGES.forEach(([name, html]) => {
  const classAttrs = [...html.matchAll(/class="([^"]*)"/g)].map(m => m[1].split(/\s+/));
  const both = classAttrs.filter(c => c.includes('card') && c.includes('scroll-x'));
  check(`D11a ${name} — .card 와 .scroll-x 를 같은 요소에 얹지 않음`,
    both.length === 0, both.map(c => c.join(' ')).join(' | '));

  // 넓은 표는 전부 스크롤 영역 안에 있어야 한다. 바깥에 있으면 좁은 화면에서
  // 페이지가 통째로 가로로 밀린다.
  const tables = (html.match(/<table\b/g) || []).length;
  const wrapped = (html.match(/<div class="scroll-x"[^>]*>\s*<table\b/g) || []).length;
  check(`D11b ${name} — 표 ${tables}개가 전부 .scroll-x 래퍼 안`,
    wrapped === tables, `wrapped=${wrapped} / tables=${tables}`);

  // 스크롤 가능 영역은 키보드로 도달할 수 있어야 하고 이름이 있어야 한다.
  const regions = [...html.matchAll(/<div class="scroll-x"([^>]*)>/g)].map(m => m[1]);
  check(`D11c ${name} — 스크롤 영역 ${regions.length}개 전부 tabindex+role+aria-label`,
    regions.length > 0 && regions.every(a =>
      /tabindex="0"/.test(a) && /role="region"/.test(a) && /aria-label="[^"]+"/.test(a)),
    regions.filter(a => !/aria-label="[^"]+"/.test(a)).length + '개 누락');
});

// =====================================================================
// D12 — 헤드라인이 첫 페인트에 보인다
//
// 예전에는 .ani{animation:fadeInUp .6s both} 에 .1/.2/.3초 스태거가 붙어
// KPI 와 영역 카드가 ~0.9초 동안 opacity:0 이었다(실측: t=91ms 에 0).
// 데이터 대시보드에서 3초 첫인상 창의 1/3 을 헤드라인 없이 보내는 셈이고,
// 인쇄·PNG 내보내기도 타이밍에 따라 빈 화면을 잡았다.
//
// 상호작용 트랜지션(hover, 테마 전환, 메뉴 열기)은 대상이 아니다 — 사용자
// 입력에 대한 피드백이라 첫 페인트를 막지 않는다.
// =====================================================================
console.log('\n[첫 페인트] 지연 진입 애니메이션');
PAGES.forEach(([name, html]) => {
  const style = (html.match(/<style>([\s\S]*?)<\/style>/) || [])[1] || '';
  // 시작 프레임(from / 0%)의 선언만 모은다. 그룹 선택자(`from,0%{...}`)와
  // 뒤집힌 순서(`to{...}from{...}`) 양쪽을 처리한다 — 둘 다 정규식 하나로는
  // 새어 나간다(CodeRabbit 지적).
  //
  // 규칙 간 조합(예: `.ani{...both}` + `.d1{animation-delay}`)은 일부러 보지
  // 않는다. 원래 결함이 정확히 그 모양 — 서로 다른 두 규칙을 두 클래스로 한
  // 요소에 얹은 것 — 이라 "같은 규칙 안" 으로 좁히면 잡아야 할 버그를 놓치고,
  // 스타일시트 전체를 보면 무관한 규칙끼리 엮여 오탐이 난다. 대신 해로운 결과
  // 자체(시작 프레임이 숨기거나 밀어냄)를 본다. 시작 프레임이 멀쩡하면
  // fill 이나 지연이 무엇이든 첫 페인트를 막지 못한다.
  const startFrames = [];
  for (const kf of style.matchAll(/@keyframes[^{]*\{((?:[^{}]*\{[^{}]*\})*)\s*\}/g))
    for (const blk of kf[1].matchAll(/([^{}]*)\{([^{}]*)\}/g))
      if (/(^|,)\s*(?:from|0%)\s*(?:,|$)/.test(blk[1].trim())) startFrames.push(blk[2]);

  check(`D12a ${name} — 시작 프레임이 transform 으로 콘텐츠를 밀어내지 않음`,
    !startFrames.some(d => /\btransform\s*:[^;}]*\b(?:translate|scale)/.test(d)),
    startFrames.filter(d => /\btransform\s*:[^;}]*\b(?:translate|scale)/.test(d)).join(' | '));
  check(`D12b ${name} — 시작 프레임이 opacity:0 이 아님`,
    !startFrames.some(d => /\bopacity\s*:\s*0(?:\s*[;}]|\s*$)/.test(d)),
    startFrames.filter(d => /\bopacity\s*:\s*0(?:\s*[;}]|\s*$)/.test(d)).join(' | '));
  const staged = [...html.matchAll(/class="([^"]*)"/g)]
    .map(m => m[1]).filter(c => /\b(ani|reveal|d[123])\b/.test(c));
  check(`D12c ${name} — 진입 애니메이션 클래스가 마크업에 남아 있지 않음`,
    staged.length === 0, staged.join(' | '));
});

console.log(`\n결과: ${pass}/${pass + fail} PASS${fail ? `, ${fail} FAIL` : ''}${warned ? `, ${warned} KNOWN ISSUE` : ''}`);
process.exit(fail ? 1 : 0);
