# keyword-search-perf Design Document

> **Summary**: 키워드 검색 루틴의 재검색 재파싱·반복 소문자화·렌더 정규식 재컴파일을 제거하는 코드 레벨 설계.
>
> **Project**: searchinmd
> **Date**: 2026-06-21
> **Status**: Draft
> **Planning Doc**: [keyword-search-perf.plan.md](../../01-plan/features/keyword-search-perf.plan.md)
> **대상 파일**: `outputs/markdown-search-app.html` (1963줄, 단일 파일 HTML)

---

## 1. Overview

### 1.1 Design Goals
- 동일 코퍼스 재검색 시 추출/매핑 재계산 0회 (파일별 파싱 캐시).
- 키워드 수 K에 대한 소문자화·순회를 K배 → 1배.
- 렌더 단계 정규식 재컴파일 제거 + 대용량 결과 청크 렌더.
- **검색 결과 동일성 보장**(회귀 0): 모든 변경은 `test-search-equivalence.js`(node vm) 하네스로 전후 비교.

### 1.2 Design Principles
- **불변 입력 가정**: 로드된 `file` 객체는 수명 동안 `content` 불변 → 파싱 결과 캐싱 안전.
- **자연 무효화**: 캐시를 `file` 객체에 결속(WeakMap) → 코퍼스 재로드 시 객체 교체로 자동 무효화. 별도 클리어 코드 불요.
- **동작 보존 리팩토링**: 출력(매칭 건수·내용·정렬)을 바꾸지 않는다. 성능만 개선.
- **단일 파일·CDN 유지**: 번들러·신규 런타임 의존 금지.

### 1.3 조사로 정정된 Plan 가정 (Design의 검증 결과)
| Plan 항목 | Design 조사 결과 | 조치 |
|-----------|------------------|------|
| **B8** NFC 불일치 우려 | 키워드=Excel 시트명이 **이미 `nfc`**(L776), content도 `nfc`(L848·894). `toLowerCase`는 한글 무영향 → **현행 이미 일관** | FR-8을 "보강" → **"불변성 회귀 테스트로 고정"** 으로 축소 |
| **B7** 다중 키워드 단일 패스 | K=시트 수(보통 수~수십), B1·B2 해소 후 추가 이득 제한적 추정 | **보류**(측정 후 판단), 기본 설계에서 제외 |

---

## 2. Architecture

### 2.1 현행 vs 개선 데이터 흐름

```
[현행] performSearch (재검색마다 전부 재실행)
 파일 → split → buildPageMapping → extract(문장/표/이미지)
        → for keyword { forEach item { toLowerCase; includes } }   ← K×N 소문자화
        → render { 행마다 new RegExp }

[개선]
 파일 → getParsed(file)  ──hit─→ 캐시 반환 (재검색 시 split/extract/map 0회)
              └─miss─→ split→map→extract→소문자본 precompute→ WeakMap 저장
        → forEach item { hay=소문자본(1회); for keyword { includes } }  ← N 소문자화
        → render { regex 1회 생성; 청크 append }
```

### 2.2 캐시 결속 구조 (무효화 자동화)

```
markdownFiles = [ fileA, fileB, ... ]   // L846 / L870 에서 재할당 시 옛 객체 폐기
        │
   WeakMap<file, ParsedDoc>             // 옛 file GC → 캐시 엔트리 자동 소멸
        │
   ParsedDoc { lines, pageMap, sentences[], tables[], images[] }   // *Lower 포함
```

- 무효화 트리거 = `markdownFiles = []`(L846 input 경로 / L870 scan 경로). 새 `file` 객체 → WeakMap miss → 재계산. **추가 무효화 코드 0줄**.
- 두 로딩 경로의 객체 형태 차이(input 경로엔 `metadata` 없음 L849, scan 경로 있음 L895) → `getParsed`는 `file.metadata ?? null` 방어.

---

## 3. 상세 설계 (FR별)

### 3.1 FR-1 파일별 파싱 캐시 + 3.2 FR-2 소문자 precompute

신규 헬퍼(파일 스코프, `performSearch` 위):

```js
const __parseCache = new WeakMap(); // file -> ParsedDoc

function getParsedDoc(file) {
    let p = __parseCache.get(file);
    if (p) return p;                              // 재검색 캐시 히트 (FR-1)
    const lines = file.content.split('\n');
    const pageMap = buildPageMapping(lines, file.metadata ?? null);
    const sentences = extractSentencesWithLineNumbers(lines);
    const tables = extractTablesWithLineNumbers(lines);
    const images = extractImagesWithLineNumbers(lines);
    // 소문자본 1회 precompute (FR-2) — 검색·키워드와 무관하게 파일당 1회
    for (const s of sentences) s.lower = s.sentence.toLowerCase();
    for (const t of tables)    t.lower = t.table.toLowerCase();
    for (const im of images)   im.lower = im.searchText.toLowerCase();
    p = { lines, pageMap, sentences, tables, images };
    __parseCache.set(file, p);
    return p;
}
```

`performSearch` 내부 변경(L1340–1358 대체):
```js
const { lines, pageMap, sentences: sentencesWithLines,
        tables: tablesWithLines, images: imagesWithLines } = getParsedDoc(file);
const pageContentCache = new Map(); // 페이지 전체내용 캐시는 검색 단위 유지(결과 부착용)
```

> **LLM 모드 분리**: `useHybrid`일 때 문장은 `extractSentencesWithLLM`(기존 `llmCache` L979 활용) 경로 유지.
> 즉 `getParsedDoc`의 `sentences`는 rule-based 전용. hybrid면 `sentencesWithLines`를 LLM 결과로 교체하고
> 그때 `.lower`를 즉석 precompute. 표/이미지 캐시는 공통 사용.

### 3.3 FR-3 검색 루프 전환 (item 바깥 / keyword 안쪽)

키워드 소문자본은 **파일 루프 밖에서 1회**:
```js
const caseSensitive = document.getElementById('caseSensitive').checked;
const kwPrep = keywords.map(k => ({ raw: k, needle: caseSensitive ? k : k.toLowerCase() }));
```

문장 매칭 (L1360–1409 대체, 표·이미지 동형):
```js
sentencesWithLines.forEach((item, idx) => {
    const hay = caseSensitive ? item.sentence : item.lower;   // ← 소문자화 item당 1회
    for (const { raw, needle } of kwPrep) {
        if (!hay.includes(needle)) continue;
        // (기존 content/heading/페이지캐시 로직 그대로) → searchResults[raw].push({...})
    }
});
```

- 결과 객체·필드·`pageContentCache` 키 규칙(L1389 `pageNum || L{lineNumber}`) **불변** → 출력 동일.
- 정렬(L1475 `localeCompare` + page/line)·`searchResults` 초기화(L1320) **유지**.

### 3.4 FR-4 하이라이트 정규식 호이스팅

`renderResultsTable(keyword)` 시작에서 1회 생성, 행 루프엔 객체 전달:
```js
const hlRegex = new RegExp(`(${escapeRegex(keyword)})`, 'gi');   // 렌더당 1회 (was: 행마다)
// 행: highlightWith(textSlice, hlRegex)
function highlightWith(text, regex){ regex.lastIndex = 0; return text.replace(regex, '<span class="highlight">$1</span>'); }
```
기존 `highlightKeyword(text, keyword)`(L1735)는 내부에서 `highlightWith` 호출하도록 유지(타 호출부 호환).

### 3.5 FR-5 대용량 결과 청크 렌더

- 초기 `RENDER_CHUNK = 200`행만 `innerHTML` 생성, 나머지는 스크롤 근접 시 append.
- 수단: 테이블 `tbody` 끝 sentinel `<tr>` + `IntersectionObserver` → 다음 200행 `insertAdjacentHTML('beforeend', ...)`.
- 토글 바인딩(L1717 `.fullpage-toggle`)은 **이벤트 위임**으로 전환(`tbody` 1개 리스너) → append 행도 자동 처리, 리스너 누수 방지.

### 3.6 FR-6 yield 청킹

```js
const YIELD_EVERY = 8;                              // 파일 8개마다 양보 (was: 매 파일 setTimeout(1))
if (i % YIELD_EVERY === 0) await new Promise(r => setTimeout(r));
```
진행률(`progressFill`/`statusText`)은 매 파일 갱신 유지(저비용).

### 3.7 FR-8 NFC 불변성 (축소)
현행이 이미 일관(§1.3)이므로 **신규 코드 없음**. 단 회귀 방지로 FR-9에 "NFD 키워드 입력 → 매칭" 케이스를 포함해
향후 입력 경로 추가 시 `nfc` 누락을 탐지.

### 3.8 FR-7 다중 키워드 단일 패스 (보류)
B1·B2 적용 후 측정값이 목표 미달일 때만 재검토. 도입 시 `hay`를 1회 순회하며 다중 needle 매칭(작은 K에선
`for needle includes`로 충분, 대 K에서만 Aho-Corasick 고려). 기본 설계 제외.

---

## 4. 테스트 설계 (FR-9) — `test-search-equivalence.js` (node vm 하네스)

기존 `test-core-logic.html`은 헬퍼만 커버. 신규 `test-search-equivalence.js`는 node `vm` + DOM mock으로
`markdown-search-app.html`의 **실제 함수를 직접 로드**(수동 복사 부채 0)해 다음을 검증:

| # | 대상 | 케이스 | 기대 |
|---|------|--------|------|
| T1 | `extractSentencesWithLineNumbers` | 제목+본문+표+이미지+코드블록 혼합 고정 입력 | 문장 수·lineNumber·isHeading·headingContext 고정 스냅샷 |
| T2 | `extractTablesWithLineNumbers` | 표 2개(공백 구분) | 블록 2개, 각 `lineNumber` 정확 |
| T3 | `extractImagesWithLineNumbers` | `![]()` + `<img>` 혼합 | alt/path/context 추출 |
| T4 | 매칭 동치 | 동일 입력에 **현행 루프 vs 개선 루프** 결과 | 매칭 건수·내용·순서 **완전 일치** |
| T5 | 소문자 precompute | caseSensitive on/off | 대소문자 동작 현행과 동일 |
| T6 | NFC | NFD 키워드 needle로 NFC content 매칭 | 매칭 성공(불변성) |
| T7 | 캐시 일관성 | 동일 file 2회 `getParsedDoc` | 동일 참조 반환 + 결과 동일 |

- node `vm`이 앱 원본을 직접 로드하므로 **함수 복사 불필요** → 구현 변경 시 테스트가 자동으로 최신 함수를 검증.
- 실행: `node outputs/test-search-equivalence.js` (전부 PASS 시 exit 0, FAIL 시 exit 1 → CI 친화).

> **개선점**: 당초 Design은 `test-core-logic.html` 확장(헬퍼 수동 복사)을 명세했으나, node vm 하네스로 대체해
> 원래 우려했던 "동기화 부채"를 0으로 제거했다.

---

## 5. 측정 설계 (FR-0b)

| 항목 | 내용 |
|------|------|
| 코퍼스 | 소(현 test-samples 71줄)·중(합성 ~수천 줄)·대(전처리 `.py` 복원 후 마커 삽입한 NCS 다수 `.md`) 3등급 |
| 키워드 | 시트 1·5·10개 Excel |
| 지표 | 최초 검색 시간 / **재검색 시간**(동일 코퍼스·키워드 변경) / 렌더 시간 / `toLowerCase` 호출수(계측 카운터, 측정 후 제거) |
| 방법 | `outputs/server.py` 구동 또는 파일 직접 열기, `performance.now()` 전후 차 |
| 목표 | 재검색 추출 호출 0, 재검색 시간 최초 대비 대폭↓, 결과 동일 |

---

## 6. 구현 순서 (Do 단계)

1. **착수 전**: 현행 그대로 FR-9 골든 스냅샷 캡처(T1–T7) + 기준선 측정.
2. FR-4(정규식 호이스팅) — 국소·무위험.
3. FR-2+FR-1(`getParsedDoc` 도입, `.lower` precompute) — 핵심.
4. FR-3(루프 전환) — 결과 동치 T4 통과 확인.
5. FR-6(yield) → FR-5(청크 렌더 + 이벤트 위임).
6. 재측정·결과 diff → 미달 시에만 FR-7 검토.

각 단계 후 T1–T7 재실행, 모두 PASS 유지.

---

## 7. 영향 범위 / 회귀 위험

| 변경 | 영향 함수 | 위험 | 가드 |
|------|-----------|------|------|
| `getParsedDoc` 신설 | `performSearch` L1340–1358 | 캐시 stale | WeakMap 자연 무효화 + T7 |
| 루프 전환 | `performSearch` L1360–1464 | 결과 순서/중복 변화 | 정렬 유지 + T4 |
| 정규식 호이스팅 | `renderResultsTable`/`highlightKeyword` | `lastIndex` 전역 g플래그 상태 | `regex.lastIndex=0` 명시 |
| 청크 렌더 | `renderResultsTable` L1683–1732 | 토글 이벤트 누락 | 이벤트 위임 |
| Excel export | (불변) | 회귀 | export 경로 미수정 — 결과 객체 형태 유지로 보장 |

---

## 8. Design 체크리스트 (= Check 단계 검증 기준)

- [ ] D1. `getParsedDoc`가 WeakMap 캐시 — 동일 file 재호출 시 재계산 없음 (T7 PASS)
- [ ] D2. `pageMap`·`sentences`·`tables`·`images`가 파일당 1회만 계산(재검색 0회) — 계측/로그로 확인
- [ ] D3. `*.lower` precompute 존재, 매칭이 `caseSensitive ? 원본 : lower` 사용
- [ ] D4. 키워드 소문자본(`kwPrep`)을 파일 루프 밖 1회 생성
- [ ] D5. 검색 루프가 `forEach item → for keyword` 구조 (item당 `toLowerCase` ≤1회)
- [ ] D6. `renderResultsTable`에서 하이라이트 정규식 1회 생성, 행 루프 내 `new RegExp` 없음
- [ ] D7. 결과(매칭 건수·내용·정렬) 현행과 **완전 일치** (T4 PASS)
- [ ] D8. 대용량(1000행+) 결과 초기 렌더 멈춤 없음, 청크 append + 토글 위임 동작
- [ ] D9. yield가 N파일 청크 단위
- [ ] D10. nfc 정규화 일관성 유지 — 정규화된 한글 키워드 매칭 정상 (T6 PASS)
- [ ] D11. `test-search-equivalence.js`(node vm)에 T1–T7 존재, 전부 PASS (앱 원본 직접 로드 → 복사 부채 0)
- [ ] D12. 단일 파일 HTML·CDN 유지(번들러/신규 의존 0), Excel export·UI 결과 불변
- [ ] D13. LLM(hybrid) 경로에서도 표/이미지 캐시 공유, 문장은 `llmCache` 경로 유지

---

## 9. 다음 단계
→ `/pdca do keyword-search-perf` (구현 순서 §6) 또는 먼저 FR-0b 코퍼스 확보·골든 스냅샷 캡처.
