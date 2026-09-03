#!/usr/bin/env node
/**
 * SRI 무결성 검사
 *
 *   실행: node outputs/test-sri.js            오프라인 검사만
 *         node outputs/test-sri.js --online   CDN 을 받아 해시까지 대조
 *
 * SRI 는 틀리면 스크립트가 통째로 차단돼 페이지가 죽는다. 문법만 보는 검사로는
 * 부족해서 두 층으로 나눴다.
 *
 *   오프라인 — 외부 <script> 에 integrity·crossorigin 이 붙어 있는지, 버전이
 *              고정돼 있는지, 세 대시보드가 같은 URL 에 같은 해시를 쓰는지.
 *              네트워크가 필요 없어 CI 기본 경로다.
 *   온라인   — 실제 CDN 응답의 sha384 가 integrity 와 일치하는지. CDN 이
 *              내용을 바꾸면(버전 고정이면 없어야 할 일) 여기서 잡힌다.
 *
 * Google Fonts 의 <link> 는 대상이 아니다. css2 응답이 User-Agent 마다 달라
 * (Chrome 과 Firefox 의 sha384 가 다름을 실측) integrity 를 걸면 일부 브라우저에서
 * 폰트가 차단된다. 고정하려면 woff2 를 자가 호스팅해야 한다.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PAGES = ['docs/index.html', 'docs/textbook.html', 'docs/osha.html', 'outputs/markdown-search-app.html'];
const ROOT = path.join(__dirname, '..');
const ONLINE = process.argv.includes('--online');

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; console.log('  ✗ ' + name + (detail !== undefined ? ' — ' + detail : '')); }
}

/** 페이지에서 외부 호스트를 참조하는 <script src> 를 뽑는다. */
function externalScripts(html) {
  return [...html.matchAll(/<script\b[^>]*\bsrc="(https?:\/\/[^"]+)"[^>]*>/g)].map((m) => ({
    tag: m[0],
    url: m[1],
    integrity: (m[0].match(/\bintegrity="([^"]+)"/) || [])[1] || null,
    crossorigin: /\bcrossorigin=/.test(m[0]),
  }));
}

console.log('[SRI] 외부 스크립트 무결성');

const all = [];
for (const rel of PAGES) {
  const html = fs.readFileSync(path.join(ROOT, rel), 'utf8');
  for (const s of externalScripts(html)) all.push({ page: rel, ...s });
}
check('외부 스크립트를 찾았다', all.length > 0, all.length);

for (const s of all) {
  const where = `${s.page} → ${s.url.replace(/^https:\/\//, '')}`;
  check(`integrity 있음: ${where}`, !!s.integrity);
  check(`crossorigin 있음: ${where}`, s.crossorigin, 'integrity 는 crossorigin 없이는 무시된다');
  check(`sha384 이상 사용: ${where}`, /^sha(384|512)-/.test(s.integrity || ''), s.integrity);
  // 버전이 고정돼 있지 않으면 CDN 이 내용을 바꿔 SRI 가 페이지를 깨뜨린다.
  check(`버전 고정: ${where}`, /@\d+\.\d+\.\d+\//.test(s.url) || /\/\d+\.\d+\.\d+\//.test(s.url), s.url);
}

// 같은 URL 은 어느 페이지에서든 같은 해시여야 한다. 한 곳만 갱신하는 실수를 잡는다.
const byUrl = new Map();
for (const s of all) {
  if (!byUrl.has(s.url)) byUrl.set(s.url, new Set());
  byUrl.get(s.url).add(s.integrity);
}
for (const [url, hashes] of byUrl) {
  check(`페이지 간 해시 일치: ${url.replace(/^https:\/\//, '')}`, hashes.size === 1, [...hashes].join(' vs '));
}

// Google Fonts 에 integrity 가 붙으면 UA 별 응답 차이로 폰트가 차단된다.
for (const rel of PAGES) {
  const html = fs.readFileSync(path.join(ROOT, rel), 'utf8');
  const bad = [...html.matchAll(/<link\b[^>]*fonts\.googleapis\.com[^>]*>/g)].filter((m) => /\bintegrity=/.test(m[0]));
  check(`Google Fonts 에 integrity 없음: ${rel}`, bad.length === 0, 'css2 응답은 User-Agent 마다 다르다');
}

async function online() {
  console.log('\n[SRI] CDN 응답 대조 (--online)');
  for (const [url, hashes] of byUrl) {
    const want = [...hashes][0];
    if (!want) continue;
    try {
      const res = await fetch(url, { redirect: 'follow' });
      if (!res.ok) { check(`받기: ${url}`, false, 'HTTP ' + res.status); continue; }
      const buf = Buffer.from(await res.arrayBuffer());
      // 선언된 알고리즘으로 계산해야 한다. sha512 로 선언된 태그를 sha384 로 재면
      // 항상 불일치가 난다(실제로 그렇게 짰다가 XLSX 태그에서 잡혔다).
      const algo = (want.match(/^(sha\d+)-/) || [])[1] || 'sha384';
      const got = algo + '-' + crypto.createHash(algo).update(buf).digest('base64');
      check(`실제 응답과 일치: ${url.replace(/^https:\/\//, '')}`, got === want, `기대 ${want} / 실제 ${got}`);
    } catch (e) {
      check(`받기: ${url}`, false, e.message);
    }
  }
}

(async () => {
  if (ONLINE) await online();
  else console.log('\n  (--online 을 붙이면 CDN 응답 해시까지 대조합니다)');
  console.log(`\n결과: ${pass}/${pass + fail} PASS${fail ? `, ${fail} FAIL` : ''}`);
  process.exit(fail ? 1 : 0);
})();
