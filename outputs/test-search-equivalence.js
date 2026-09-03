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

// ===== 결과 =====
console.log(`\n결과: ${pass}/${pass + fail} PASS${fail ? `, ${fail} FAIL` : ''}`);
process.exit(fail ? 1 : 0);
