#!/usr/bin/env node
/**
 * test-core-logic.html 헤드리스 실행기
 *
 * test-core-logic.html 은 브라우저에서 열어 탭 제목("PASS: N/N tests passed")으로
 * 결과를 보는 하니스다. 그대로는 CI 에 걸 수 없어, 최소 DOM 을 세워 <script> 를
 * 실행하고 document.title 을 읽어 exit code 로 바꾼다.
 *
 *   실행: node outputs/run-core-logic-tests.js
 *   PASS 시 exit 0, FAIL·파싱 실패 시 exit 1
 *
 * 브라우저에서 여는 방식도 그대로 유효하다 — 이 파일은 같은 HTML 을 다른 방법으로
 * 돌릴 뿐이고, 어서션 사본을 따로 두지 않는다.
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = path.join(__dirname, 'test-core-logic.html');

function mkEl() {
  return {
    className: '', innerHTML: '', textContent: '', style: {},
    appendChild() {}, setAttribute() {}, addEventListener() {},
  };
}

function main() {
  const html = fs.readFileSync(HTML, 'utf8');
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  if (scripts.length === 0) {
    console.error('FAIL: test-core-logic.html 에서 <script> 블록을 찾지 못했습니다.');
    process.exit(1);
  }

  const ctx = {
    console,
    document: {
      title: '',
      getElementById: mkEl,
      querySelector: mkEl,
      querySelectorAll: () => [],
      createElement: mkEl,
      body: mkEl(),
      // 하니스는 DOMContentLoaded 에서 실행을 시작한다. 즉시 호출해 준다.
      addEventListener: (_event, fn) => fn(),
    },
  };
  ctx.window = ctx;
  ctx.globalThis = ctx;
  vm.createContext(ctx);

  try {
    vm.runInContext(scripts.join('\n'), ctx, { filename: 'test-core-logic.html' });
  } catch (err) {
    console.error('FAIL: 하니스 실행 중 예외 —', err && err.message ? err.message : err);
    process.exit(1);
  }

  const title = ctx.document.title;
  if (!title) {
    console.error('FAIL: document.title 이 설정되지 않았습니다. 하니스가 끝까지 실행되지 않았을 수 있습니다.');
    process.exit(1);
  }

  console.log(title);
  process.exit(/^PASS/.test(title) ? 0 : 1);
}

main();
