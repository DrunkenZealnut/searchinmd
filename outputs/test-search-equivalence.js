#!/usr/bin/env node
/**
 * 검색 루틴 회귀 테스트 (FR-9) — keyword-search-perf
 *
 * markdown-search-app.html 의 실제 함수를 Node vm + DOM mock 으로 로드해
 * (수동 복사 부채 0) 성능개선 전후 동작 동일성을 검증한다.
 *
 *   실행: node outputs/test-search-equivalence.js
 *   PASS 시 exit 0, FAIL 시 exit 1 (CI 친화)
 *
 * 커버: T1-T3 추출 정확성 / T4 루프전환 동치 / T5 caseSensitive / T6 NFC / T7 캐시 일관성
 */
const fs = require('fs'), vm = require('vm'), path = require('path');

function loadApp(p) {
  const h = fs.readFileSync(p, 'utf8');
  const js = [...h.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
  const mkEl = () => new Proxy(function () { return mkEl(); }, {
    get(t, k) {
      if (k === 'style') return {}; if (k === 'classList') return { add() {}, remove() {}, contains() { return false; } };
      if (k === 'addEventListener') return () => {}; if (k === 'checked') return false; if (k === 'value') return '';
      if (k === 'dataset') return {}; if (k === 'files') return []; return mkEl();
    }, apply() { return mkEl(); }, set() { return true; }
  });
  const document = { getElementById: () => mkEl(), querySelector: () => mkEl(), querySelectorAll: () => [], createElement: () => mkEl(), addEventListener: () => {}, body: mkEl() };
  const ctx = {
    document, console, setTimeout, clearTimeout, Promise, Map, Set, WeakMap, JSON, Math, RegExp, Array, Object,
    String, Number, parseInt, parseFloat, Intl, XLSX: { utils: {} }, navigator: { language: 'ko' }, alert: () => {},
    fetch: () => Promise.reject(new Error('no net')), localStorage: { getItem: () => null, setItem: () => {} },
    IntersectionObserver: function () { this.observe = () => {}; this.disconnect = () => {}; }, FileReader: function () {}
  };
  ctx.window = ctx; ctx.globalThis = ctx; vm.createContext(ctx); vm.runInContext(js, ctx, { filename: p });
  return ctx;
}

const A = loadApp(path.join(__dirname, 'markdown-search-app.html'));

let pass = 0, fail = 0;
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
function check(name, cond) { if (cond) { pass++; console.log('  ✓ ' + name); } else { fail++; console.log('  ✗ ' + name); } }

// ---- 공통 push 본문(루프 순서만 다르게 하기 위해 본문 공통화) ----
function pushSentence(R, key, item, idx, arr, pageMap, lines, pcc, file) {
  const pageNum = pageMap ? pageMap.get(item.lineNumber) : null; let content;
  if (item.isHeading) { let s = [item.sentence.trim()]; for (let si = idx + 1; si < arr.length && s.length <= 5; si++) { const sub = arr[si]; if (sub.isHeading) break; s.push(sub.sentence.trim()); } content = s.join('\n'); }
  else content = item.headingContext ? `[${item.headingContext}]\n${item.sentence.trim()}` : item.sentence.trim();
  const ck = pageNum || `L${item.lineNumber}`; let fp; if (pcc.has(ck)) fp = pcc.get(ck); else { fp = A.extractPageContent(lines, pageMap, pageNum, item.lineNumber); pcc.set(ck, fp); }
  R[key].push({ type: '문장', filename: file.name, content, lineNumber: item.lineNumber, pageNumber: pageNum || item.lineNumber, hasPage: !!pageNum, headingContext: item.headingContext || null, fullPageContent: fp });
}
function pushTable(R, key, item, pageMap, lines, pcc, file) { const pageNum = pageMap ? pageMap.get(item.lineNumber) : null; const ck = pageNum || `L${item.lineNumber}`; let fp; if (pcc.has(ck)) fp = pcc.get(ck); else { fp = A.extractPageContent(lines, pageMap, pageNum, item.lineNumber); pcc.set(ck, fp); } R[key].push({ type: '표', filename: file.name, content: item.table.trim(), lineNumber: item.lineNumber, pageNumber: pageNum || item.lineNumber, hasPage: !!pageNum, fullPageContent: fp }); }
function pushImage(R, key, img, pageMap, lines, pcc, file) { const pageNum = pageMap ? pageMap.get(img.lineNumber) : null; const ck = pageNum || `L${img.lineNumber}`; let fp; if (pcc.has(ck)) fp = pcc.get(ck); else { fp = A.extractPageContent(lines, pageMap, pageNum, img.lineNumber); pcc.set(ck, fp); } R[key].push({ type: '이미지', filename: file.name, content: img.content, lineNumber: img.lineNumber, pageNumber: pageNum || img.lineNumber, hasPage: !!pageNum, fullPageContent: fp }); }
function sortR(R, kws) { kws.forEach(k => R[k].sort((a, b) => { const f = a.filename.localeCompare(b.filename); if (f) return f; const ap = a.hasPage ? a.pageNumber : a.lineNumber, bp = b.hasPage ? b.pageNumber : b.lineNumber; return ap - bp; })); }

// 원본 루프(keyword 바깥, 매 비교마다 toLowerCase) — 개선 전 동작
function oldSearch(files, kws, o) {
  const R = {}; kws.forEach(k => R[k] = []);
  for (const file of files) {
    const lines = file.content.split('\n'); const pageMap = A.buildPageMapping(lines, file.metadata); const pcc = new Map();
    const S = o.s ? A.extractSentencesWithLineNumbers(lines) : [], T = o.t ? A.extractTablesWithLineNumbers(lines) : [], I = o.i ? A.extractImagesWithLineNumbers(lines) : [];
    for (const kw of kws) {
      const sk = o.cs ? kw : kw.toLowerCase();
      if (o.s) S.forEach((it, idx) => { const x = o.cs ? it.sentence : it.sentence.toLowerCase(); if (x.includes(sk)) pushSentence(R, kw, it, idx, S, pageMap, lines, pcc, file); });
      if (o.t) T.forEach(it => { const x = o.cs ? it.table : it.table.toLowerCase(); if (x.includes(sk)) pushTable(R, kw, it, pageMap, lines, pcc, file); });
      if (o.i) I.forEach(im => { const x = o.cs ? im.searchText : im.searchText.toLowerCase(); if (x.includes(sk)) pushImage(R, kw, im, pageMap, lines, pcc, file); });
    }
  }
  sortR(R, kws); return R;
}
// 신규 루프(getParsedDoc 캐시 + item 바깥 + lower precompute) — 개선 후 동작
function newSearch(files, kws, o) {
  const R = {}; kws.forEach(k => R[k] = []);
  for (const file of files) {
    const p = A.getParsedDoc(file); const lines = p.lines, pageMap = p.pageMap, pcc = new Map();
    const S = o.s ? p.sentences : [], T = o.t ? p.tables : [], I = o.i ? p.images : [];
    const kwPrep = kws.map(k => ({ raw: k, needle: o.cs ? k : k.toLowerCase() }));
    if (o.s) S.forEach((it, idx) => { const hay = o.cs ? it.sentence : it.lower; for (const { raw, needle } of kwPrep) if (hay.includes(needle)) pushSentence(R, raw, it, idx, S, pageMap, lines, pcc, file); });
    if (o.t) T.forEach(it => { const hay = o.cs ? it.table : it.lower; for (const { raw, needle } of kwPrep) if (hay.includes(needle)) pushTable(R, raw, it, pageMap, lines, pcc, file); });
    if (o.i) I.forEach(im => { const hay = o.cs ? im.searchText : im.lower; for (const { raw, needle } of kwPrep) if (hay.includes(needle)) pushImage(R, raw, im, pageMap, lines, pcc, file); });
  }
  sortR(R, kws); return R;
}

// ---- 합성 코퍼스 ----
const md1 = `<!-- page: 1 -->
# 안전 관리 개요
작업장 안전은 중요하다.
○ 적용범위
모든 근로자에게 적용된다.
<!-- page: 2 -->
## 보호구 착용
- 안전모를 착용한다
- 보호장갑 사용
| 항목 | 기준 |
| --- | --- |
| 안전모 | 필수 |
![안전표지](img/sign.png)
SAFETY first and Safety always`;
const md2 = `# 위험성 평가
위험 요소를 식별한다.
(가) 기계 위험
회전체 접촉 주의
\`\`\`
code block 안전 무시
\`\`\`
일반 문장입니다.`;
const mkFiles = () => [
  { name: 'a/doc1.md', content: A.nfc(md1), metadata: null },
  { name: 'b/doc2.md', content: A.nfc(md2), metadata: null }
];

// ===== T1-T3: 추출 정확성 =====
console.log('\n[T1-T3] 추출 정확성');
const lines1 = A.nfc(md1).split('\n');
const sents = A.extractSentencesWithLineNumbers(lines1);
const tbls = A.extractTablesWithLineNumbers(lines1);
const imgs = A.extractImagesWithLineNumbers(lines1);
check('T1a 코드블록 내 라인은 표/이미지로 추출되지 않음', !tbls.some(t => t.table.includes('code block')));
check('T1b 제목 "안전 관리 개요" 가 isHeading=true', sents.some(s => s.sentence.includes('안전 관리 개요') && s.isHeading));
check('T1c 본문 "모든 근로자에게 적용된다." headingContext 보유', sents.some(s => s.sentence.startsWith('모든 근로자') && s.headingContext));
check('T2 표 1개 추출 + lineNumber 정수', tbls.length === 1 && Number.isInteger(tbls[0].lineNumber));
check('T3 이미지 1개, path=img/sign.png', imgs.length === 1 && imgs[0].searchText.includes('img/sign.png'));

// ===== T4: 루프 전환 동치 (다양한 키워드·옵션) =====
console.log('\n[T4] 루프 전환 동치 (개선 전 == 개선 후)');
const kwSets = [['안전', '보호', '위험'], ['Safety'], ['안전모', '적용범위'], ['safety'], ['없는키워드xyz']];
const optSets = [{ s: 1, t: 1, i: 1, cs: 0 }, { s: 1, t: 1, i: 1, cs: 1 }, { s: 1, t: 0, i: 0, cs: 0 }, { s: 0, t: 1, i: 0, cs: 0 }, { s: 0, t: 0, i: 1, cs: 0 }];
let t4ok = 0, t4n = 0;
for (const kws of kwSets) for (const o of optSets) { t4n++; if (eq(oldSearch(mkFiles(), kws, o), newSearch(mkFiles(), kws, o))) t4ok++; }
check(`T4 ${t4n}개 (키워드×옵션) 조합 전부 결과 동일`, t4ok === t4n);

// ===== T5: caseSensitive 동작 =====
console.log('\n[T5] caseSensitive');
const csOff = newSearch(mkFiles(), ['safety'], { s: 1, t: 0, i: 0, cs: 0 });
const csOn = newSearch(mkFiles(), ['safety'], { s: 1, t: 0, i: 0, cs: 1 });
check('T5a cs=off: 소문자 needle이 "SAFETY/Safety" 매칭', csOff['safety'].length > 0);
check('T5b cs=on: 소문자 needle이 대문자 원문에 미매칭', csOn['safety'].length === 0);

// ===== T6: NFC 불변성 =====
console.log('\n[T6] NFC');
const nfdKw = '가나다'.normalize('NFD'); // 조합형이 아닌 자모 분해 모사
const nfcContent = A.nfc('가나다 안전 테스트');
const f6 = [{ name: 'n.md', content: nfcContent, metadata: null }];
const r6 = newSearch(f6, [A.nfc('안전')], { s: 1, t: 0, i: 0, cs: 0 });
check('T6 nfc 정규화된 키워드로 한글 매칭 성공', r6[A.nfc('안전')].length > 0);

// ===== T7: 캐시 일관성 =====
console.log('\n[T7] 캐시 일관성');
const f7 = { name: 'x.md', content: A.nfc(md1), metadata: null };
const p1 = A.getParsedDoc(f7), p2 = A.getParsedDoc(f7);
check('T7a 동일 file 2회 호출 → 동일 참조(재계산 0)', p1 === p2);
check('T7b sentences 전부 .lower precompute 보유', p1.sentences.every(s => typeof s.lower === 'string'));

// ===== T8: 청크 렌더 (FR-5) — sentinel 이 스크롤 컨테이너 안에 있고 root 가 그 컨테이너인가 =====
// 회귀 배경: sentinel 을 .results-table-wrapper(max-height:400px; overflow-y:auto) *밖* 에 붙이면
// 행을 append 해도 sentinel 이 움직이지 않아 교차 상태가 불변이고, 콜백이 1회 발화 후 다시
// 발화하지 않는다 → 결과가 400행에서 조용히 멈춘다. 이 테스트가 그 구조를 고정한다.
console.log('\n[T8] 청크 렌더 sentinel');

function loadAppForRender() {
  const h = fs.readFileSync(path.join(__dirname, 'markdown-search-app.html'), 'utf8');
  const js = [...h.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
  const rec = { ios: [], nodes: {} };
  const mkNode = (id) => (rec.nodes[id] = rec.nodes[id] || {
    id, innerHTML: '', textContent: '', style: {}, dataset: {}, children: [],
    classList: { add() {}, remove() {}, contains: () => false },
    addEventListener() {}, appendChild(c) { this.children.push(c); },
    insertAdjacentHTML(_, html) { this.innerHTML += html; }, remove() { this.removed = true; },
    closest: () => null, contains: () => true, querySelector: () => null,
  });
  const document = {
    getElementById: mkNode, querySelector: mkNode, querySelectorAll: () => [],
    createElement: () => mkNode('created'), addEventListener() {}, body: mkNode('body'),
  };
  const ctx = {
    document, console: { log() {}, warn() {}, error() {} }, setTimeout, clearTimeout,
    Promise, Map, Set, WeakMap, JSON, Math, RegExp, Array, Object, String, Number,
    parseInt, parseFloat, Intl, XLSX: { utils: {} }, navigator: { language: 'ko' }, alert() {},
    fetch: () => Promise.reject(new Error('no net')),
    localStorage: { getItem: () => null, setItem() {} },
    IntersectionObserver: function (cb, opts) {
      rec.ios.push({ cb, opts, observed: [] });
      this.observe = (el) => rec.ios[rec.ios.length - 1].observed.push(el);
      this.disconnect = () => {};
    },
    FileReader: function () {},
  };
  ctx.window = ctx; ctx.globalThis = ctx; vm.createContext(ctx);
  // searchResults 는 `let` 이라 컨텍스트 프로퍼티로 덮을 수 없다. 주입 헬퍼를 덧붙인다.
  vm.runInContext(js + '\n;globalThis.__setResults = (k, v) => { searchResults[k] = v; };',
                  ctx, { filename: 'render' });
  return { ctx, rec };
}

const { ctx: RC, rec } = loadAppForRender();
// RENDER_CHUNK(200) 을 넘겨야 청크 경로가 켜진다
const many = Array.from({ length: 450 }, (_, i) => ({
  type: '문장', filename: 'a.md', content: '안전 ' + i, lineNumber: i + 1,
  pageNumber: i + 1, hasPage: false, headingContext: null, fullPageContent: 'x',
}));
RC.__setResults('안전', many);
RC.renderResultsTable('안전');

const wrapperHtml = rec.nodes['resultsContent'].innerHTML;
// wrapper 의 여는 태그부터 div 중첩을 세어 *짝이 맞는* 닫는 태그를 찾는다.
// lastIndexOf('</div>') 를 쓰면 sentinel 이 밖으로 나가도 그 자신의 닫는 태그를 잡아
// 검사가 통과해 버린다(실제로 그랬다).
function wrapperRange(html) {
  const open = html.indexOf('<div class="results-table-wrapper"');
  if (open < 0) return null;
  const tag = /<div\b|<\/div>/g;
  tag.lastIndex = open;
  let depth = 0, m;
  while ((m = tag.exec(html))) {
    depth += m[0] === '</div>' ? -1 : 1;
    if (depth === 0) return [open, m.index];
  }
  return null;
}
const range = wrapperRange(wrapperHtml);
const sentinelAt = wrapperHtml.indexOf('id="resultsSentinel"');
check('T8a sentinel 이 .results-table-wrapper 안에 렌더된다',
  !!range && sentinelAt > range[0] && sentinelAt < range[1]);
check('T8b IntersectionObserver 가 1개 생성된다', rec.ios.length === 1);
const io = rec.ios[0] || {};
check('T8c IO 의 root 가 스크롤 컨테이너(resultsWrapper)다',
  !!io.opts && io.opts.root === rec.nodes['resultsWrapper']);
check('T8d IO 가 sentinel 을 관찰한다',
  (io.observed || []).length === 1 && io.observed[0] === rec.nodes['resultsSentinel']);
// 콜백을 발화시켜 다음 청크가 실제로 append 되는지
const before = rec.nodes['resultsTbody'].innerHTML.length;
if (io.cb) io.cb([{ isIntersecting: true }]);
check('T8e 콜백 발화 시 다음 청크가 tbody 에 append 된다',
  rec.nodes['resultsTbody'].innerHTML.length > before);

// ===== T9: 파싱 캐시 지연 계산 =====
// 회귀 배경: sentences/tables/images 를 즉시 계산하면 검색 옵션이 꺼져 있어도, LLM
// 하이브리드 모드로 sentences 가 버려질 때도 그대로 계산·보관된다(캐시의 약 59%).
console.log('\n[T9] 파싱 캐시 지연 계산');

const A9 = loadApp(path.join(__dirname, 'markdown-search-app.html'));
const md9 = [
  '<!-- page: 1 -->', '## 안전 관리',
  '보호구를 착용한다.', '',
  '| 구분 | 대책 |', '|---|---|', '| 화학 | 환기 |', '',
  '![표지](img/a.png)', ''
].join('\n');
const f9 = { name: 'lazy.md', content: A9.nfc(md9), metadata: null };

// 추출 함수 호출 횟수를 세도록 감싼다
const calls = { sentences: 0, tables: 0, images: 0 };
for (const [k, fn] of [['sentences', 'extractSentencesWithLineNumbers'],
                       ['tables', 'extractTablesWithLineNumbers'],
                       ['images', 'extractImagesWithLineNumbers']]) {
  const orig = A9[fn];
  A9[fn] = function (...args) { calls[k]++; return orig.apply(this, args); };
}

const p9 = A9.getParsedDoc(f9);
check('T9a getParsedDoc 은 lines/pageMap 만 즉시 만든다',
  calls.sentences === 0 && calls.tables === 0 && calls.images === 0);
check('T9b lines/pageMap 은 바로 쓸 수 있다',
  Array.isArray(p9.lines) && p9.lines.length > 0 && p9.pageMap instanceof Map);

const t9 = p9.tables;                       // 표만 건드린다
check('T9c 표를 읽어도 문장·이미지는 계산되지 않는다',
  calls.tables === 1 && calls.sentences === 0 && calls.images === 0);
check('T9d 표 결과가 정상이고 lower 가 붙는다',
  t9.length === 1 && typeof t9[0].lower === 'string');

p9.tables; p9.tables;                       // 재접근
check('T9e 한 번 계산하면 값으로 굳어 재계산이 없다', calls.tables === 1);

check('T9f 문장은 접근할 때 계산된다',
  (p9.sentences.length > 0) && calls.sentences === 1 && calls.images === 0);
check('T9g 이미지도 마찬가지', (p9.images.length === 1) && calls.images === 1);
check('T9h 지연 프로퍼티도 열거 가능해 객체 모양이 이전과 같다',
  ['lines', 'pageMap', 'sentences', 'tables', 'images'].every(k => Object.keys(p9).includes(k)));

// ===== 결과 =====
console.log(`\n결과: ${pass}/${pass + fail} PASS${fail ? `, ${fail} FAIL` : ''}`);
process.exit(fail ? 1 : 0);
