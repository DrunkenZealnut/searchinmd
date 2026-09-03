# Plan: keyword-search-perf (키워드 문서분석 루틴 리뷰 및 성능개선)

> **Rev 2 (2026-06-21)** — 소스 복원 완료 반영. 복원본이 리뷰 기준 사본과 **바이트 동일**(diff 일치)이므로
> 기존 병목 분석(B1–B8)·라인 번호는 그대로 유효. 본 개정은 ① FR-0 복원 완료, ② 복원으로 드러난 검증 자산
> (`test-core-logic.html`), ③ 측정 환경 현실화, ④ TODOS 연계를 추가한다.

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | 키워드 검색 루틴이 **재검색마다 코퍼스 전체를 재파싱**하고(`split`·`buildPageMapping`·`extract*`), 키워드 수만큼 동일 텍스트를 **반복 소문자화**한다. 코퍼스·키워드 증가 시 검색 지연이 선형 누적된다. |
| **Solution** | 파일별 파싱 결과(lines·sentences·tables·images·pageMap·소문자본)를 **content 기반 캐시**로 1회만 계산하고, 검색 루프를 **`item 바깥/keyword 안쪽`**으로 전환하며, 렌더 정규식을 호이스팅한다. `test-core-logic.html` 하네스를 확장해 **결과 동일성 회귀 테스트**로 안전망을 건다. |
| **Function UX Effect** | 동일 코퍼스에서 키워드만 바꿔 재검색할 때 추출 비용 0회 → 즉시 응답. 대용량 결과도 청크 렌더로 UI 멈춤 제거. |
| **Core Value** | "검색 → 키워드 변경 → 재검색" 탐색 루프의 반복 비용을 **O(코퍼스 전체) → O(매칭 결과)** 로 축소. 단일 파일 HTML·CDN 의존 구조는 유지. |

| 항목 | 내용 |
|------|------|
| Feature | keyword-search-perf |
| 작성일 / 개정일 | 2026-06-21 / 2026-06-21 (Rev 2) |
| 대상 산출물 | `outputs/markdown-search-app.html` (1963줄, 키워드 모드 검색 엔진) |
| 소스 상태 | **복원 완료** — 워킹 트리 확보, 리뷰 사본과 diff 동일 |
| 검증 자산 | `outputs/test-core-logic.html` (헬퍼 단위 테스트), `outputs/server.py` (로컬 서버 + LLM 프록시) |
| PDCA 단계 | Plan (Rev 2) |

---

## 1. 배경 및 현황 (복원 후 갱신)

`outputs/markdown-search-app.html`은 NCS `.md` 코퍼스 대상 클라이언트 사이드 키워드 검색 엔진으로,
빌드 없는 단일 파일 HTML이며 검색이 브라우저에서 동기 실행된다.

- **소스 복원 완료**: 워킹 트리에 `markdown-search-app.html`(1963줄) 복원. 리뷰 기준 사본과 `diff` **동일** 확인 →
  Rev 1의 병목 분석·라인 번호 전부 유효.
- **함께 복원된 자산**:
  - `outputs/test-core-logic.html` — `isHeadingLine`·`isStandaloneTitle`·`normalizeHeading`·`nfc` **단위 테스트 하네스**.
    헬퍼를 **수동 복사**해 검증(assert/assertEqual, 결과를 `document.title`에 PASS/FAIL로 노출 → CI 친화).
    단 **성능개선 대상(`extract*WithLineNumbers`·`performSearch`)은 미커버**.
  - `outputs/server.py` — 정적 서빙 + `/api/llm/*` → `localhost:1234` 프록시(LLM 모드용). 미리보기·측정 실행 수단.
  - `outputs/reclassify_accident_cases.py`(349줄) 복원. 검색 성능과 무관.
- **미복원/한계**:
  - 전처리 `.py` 3종(`page_utils.py`·`insert_page_markers.py`·`add_fullpage.py`)은 아직 워킹 트리에 없음 →
    대용량 측정 코퍼스에 page marker를 넣으려면 복원 필요.
  - `outputs/test-samples/`는 `sample1.md`(46줄)·`sample2.md`(25줄), **page marker 없음** → fallback 경로 검증용일 뿐
    **성능 기준선 측정엔 부적합**(규모 부족).

## 2. 문제 정의 — 현행 루틴 성능 병목 (Rev 1 유지)

`performSearch()`(L1318) 실행 구조:

```
for each file (F개)                                    [L1333]
    lines = file.content.split('\n')                   [L1340]  ← 매 검색 재분할
    pageMap = buildPageMapping(lines, metadata)        [L1343]  ← 매 검색 재계산(정규식 + TOC 2-pass DP)
    pageContentCache = new Map()                       [L1344]  ← 검색 1회용(종료 시 폐기)
    sentences = extractSentencesWithLineNumbers(lines) [L1354]  ← 매 검색 재추출
    tables   = extractTablesWithLineNumbers(lines)     [L1357]  ← 매 검색 재추출
    images   = extractImagesWithLineNumbers(lines)     [L1358]  ← 매 검색 재추출
    for each keyword (K개)                              [L1360]
        sentences.forEach → item.sentence.toLowerCase()[L1366]  ← K×S회 동일 텍스트 재소문자화
        tables.forEach   → item.table.toLowerCase()    [L1414]  ← K×T회
        images.forEach   → img.searchText.toLowerCase()[L1441]  ← K×I회
    await setTimeout(1)                                [L1466]  ← 파일마다 yield(클램프 누적)
sort (localeCompare)                                   [L1475]
renderResultsTable → results.map().join('') innerHTML  [L1697]  ← 대용량 결과 일괄 DOM
    highlightKeyword: new RegExp 매 행                  [L1736]  ← 결과 N행 × 정규식 재컴파일
```

### 식별된 병목

| ID | 병목 | 위치 | 영향 |
|----|------|------|------|
| **B1** | 검색 간 파싱 결과 미캐싱 | L1340·1343·1354·1357·1358 | 재검색 R회 → 추출/매핑 R배 |
| **B2** | `toLowerCase()` 키워드마다 재계산 | L1366·1414·1441 | 동일 텍스트 K배 소문자화 |
| **B3** | 루프 순서 `keyword 바깥` | L1360→1365 | item 집합 K회 순회 |
| **B4** | `highlightKeyword` 정규식 행마다 재컴파일 | L1736 | 결과 N행 × `new RegExp` |
| **B5** | 대용량 결과 비가상화 렌더 | L1697 | 수천 행 단일 innerHTML → UI 멈춤 |
| **B6** | 파일마다 `setTimeout(1)` yield | L1466 | 파일 多 시 클램프 지연 누적 |
| **B7** | 다중 키워드 K회 독립 스캔 | L1360–1463 | 텍스트를 키워드 수만큼 스캔 |
| **B8** | 검색 비교 시 NFC 정규화 점검 | `performSearch` 전반 | NFD 키워드 매칭 누락(정확도) |

### 정량 추정 (가정: F=52, S≈300문장/파일, K=10, 재검색 R=10회)

| 지표 | 현행 | 개선 후(목표) |
|------|------|--------------|
| 1회 검색 `toLowerCase` 호출 | ≈ **156,000회** | ≈15,600회(precompute) → 캐시 시 0회 |
| 재검색 10회 추출 실행 | **520회** | 52회(최초 1회 후 캐시 히트) |
| 하이라이트 정규식 컴파일 | 결과행 N × 탭전환 | 렌더당 1회 |

> 상대 비교용 추정. Check 단계에서 실제 코퍼스로 측정·검증(§5-1, FR-0b).

## 3. 목표 / 비목표

**목표** — G1. 재검색 재파싱 제거(파일별 캐싱) · G2. 키워드에 대한 소문자화·순회 K배→1배 ·
G3. 렌더 정규식 재컴파일 제거 + 대용량 청크 렌더 · G4. **검색 결과 동일성 보장**(회귀 없음).

**비목표** — N1. LLM 모드(`extractSentencesWithLLM`, 이미 `llmCache` 보유) 최적화 ·
N2. 역색인/Aho-Corasick 등 자료구조 전면 교체(B7은 선택) · N3. UI/디자인·Excel 포맷 변경 ·
N4. 번들러 도입(단일 파일 HTML·CDN 유지) · N5. TODOS의 "LLM fallback indicator"(데이터 무결성 UX, 별개).

## 4. 개선 요구사항 (FR)

| ID | 요구사항 | 대응 | 우선순위 | Rev 2 상태 |
|----|----------|:----:|:--------:|:----------:|
| ~~FR-0~~ | iCloud 아카이브 소스를 `outputs/`로 복원 | — | P0 | ✅ **완료** |
| FR-0b | 기준선 측정용 **대용량 코퍼스 확보**(전처리 `.py` 복원 → 마커 삽입, 또는 합성) | B1·B5 측정 | P1 | 신규 |
| FR-1 | 파일별 파싱 캐시: `content` 키로 `{lines, sentences, tables, images, pageMap, *Lower}` 1회 계산·재사용. 코퍼스 변경 시 무효화 | B1 | P1 | 유지 |
| FR-2 | 검색 대상 소문자본을 추출 시 1회 precompute, 비교는 캐시본 사용 | B2 | P1 | 유지 |
| FR-3 | 검색 루프를 `item 바깥/keyword 안쪽`으로 전환 | B3 | P2 | 유지 |
| FR-4 | `renderResultsTable`에서 하이라이트 정규식 1회 생성 후 재사용 | B4 | P2 | 유지 |
| FR-5 | 대용량 결과 청크/페이지네이션 렌더(초기 N행 + 더보기/가상 스크롤) | B5 | P2 | 유지 |
| FR-6 | yield 단위를 파일 → 청크(N파일마다)로 조정 | B6 | P3 | 유지 |
| FR-7 | (선택) 다중 키워드 단일 패스 매칭 — 효과/복잡도 분석 후 결정 | B7 | P3 | 유지 |
| FR-8 | 검색 비교 경로 NFC 정규화 일관성 검증·보강(키워드 입력 정규화) | B8 | P2 | 유지 |
| FR-9 | **`test-core-logic.html` 하네스 확장** — `extractSentencesWithLineNumbers`·표/이미지 추출·검색 매칭의 고정 입출력 테스트 추가, 개선 전후 **결과 동일성 회귀 검증** | G4 | P1 | 신규 |

## 5. 접근 방식 (단계적)

1. **기준선 측정** — FR-0b. 대용량 코퍼스 확보 후 `performance.now()`로 현행 검색 시간 기록(소·중·대, 키워드 1·5·10개).
   `outputs/server.py`로 로컬 구동 또는 파일 직접 열기.
2. **안전망 구축** — FR-9. 개선 착수 **전에** 현행 동작을 고정 테스트로 캡처(골든 결과). 이후 모든 변경의 회귀 기준.
3. **무위험 개선** — FR-2·FR-4·FR-8(국소 변경, 결과 불변).
4. **구조 개선** — FR-1(파싱 캐시)·FR-3(루프 전환). 캐시 무효화 + 결과 동일성 검증 동반.
5. **렌더 개선** — FR-5·FR-6.
6. **선택 과제** — FR-7은 측정이 목표 미달일 때만.

> 헬퍼 수정 시 `test-core-logic.html`의 **복사본도 동기화**해야 함(수동 복사 구조). FR-9는 이 동기화 절차를 명문화한다.

## 6. 리스크 및 전제 (Rev 2 정정)

| 리스크 | 영향 | 완화 |
|--------|------|------|
| ~~소스 부재·git 손상~~ | — | ✅ 복원 완료. git은 여전히 손상 → 버전관리 비의존, 변경 전 수동 백업 |
| 측정 코퍼스 부재(test-samples 71줄) | 성능 효과 입증 불가 | FR-0b로 대용량 코퍼스 확보 |
| 자동화 테스트 **부분 커버**(헬퍼만, 검색/추출 미커버) | 리팩토링 회귀 미탐지 | FR-9로 검색/추출 테스트 추가 |
| 헬퍼 "수동 복사" 동기화 부채 | 테스트-구현 불일치 | 변경 시 양쪽 동기화 절차 명문화 |
| 캐시 무효화 누락 | 코퍼스 변경 후 stale 결과 | content/파일목록 기반 키, 폴더 재선택 시 클리어 |
| 루프 전환 시 결과 순서·중복 변화 | 회귀 | 정렬(L1475) 유지 + 전후 결과 diff |
| NFC 보강이 기존 매칭에 영향 | 정확도 변동 | 정규화 일관 적용 + 샘플 회귀 |

## 7. 완료 기준 체크리스트 (Design·Check 검증 기준)

- [x] **C1. FR-0**: 소스 `outputs/` 복원 + 리뷰 사본과 diff 동일 (Rev 2에서 충족)
- [ ] C2. FR-1: 동일 코퍼스 재검색 시 `extract*`·`buildPageMapping` 재호출 0회(캐시 히트)
- [ ] C3. FR-2: 키워드 K개 검색에서 문장당 `toLowerCase` 1회로 축소
- [ ] C4. FR-3: 검색 루프가 item 단위 1회 순회 구조로 전환
- [ ] C5. FR-4: 하이라이트 정규식이 렌더당 1회만 컴파일
- [ ] C6. FR-5: 대용량 결과(1000행+)에서 초기 렌더 멈춤 없음
- [ ] C7. FR-8: NFD 키워드 입력으로도 한글 매칭 정상
- [ ] C8. **결과 동일성**: 개선 전후 모든 키워드의 매칭 건수·내용 일치 (FR-9 하네스로 검증)
- [ ] C9. FR-0b 기준선 대비 재검색 시간 유의미 단축(추출 캐시 적용 시 재검색 추출 ≈0)
- [ ] C10. 단일 파일 HTML·CDN 의존 원칙 유지
- [ ] C11. **FR-9**: `test-core-logic.html`에 검색/추출 회귀 테스트 추가, PASS

## 8. 연계 메모 (TODOS.md)

- **buildPageMapping Strategy 2 dead-code화**: 모든 문서에 `<!-- page: N -->` 마커가 보급되면 TOC 매칭 + DP 보간(약 200줄,
  B1 재계산 비용의 주요부)이 미사용 경로가 됨. FR-1 캐싱과 별개로, 마커 보급 시 **Strategy 2 제거**가 추가 성능·정결 이득.
  본 과제 범위 밖이나 Design에서 연계 검토.

## 9. 다음 단계

→ `/pdca design keyword-search-perf` — 각 FR의 구현 위치·캐시 자료구조·무효화 시점, FR-9 테스트 케이스,
FR-0b 코퍼스 확보 방법을 구체화한다. 구현은 복원된 `outputs/markdown-search-app.html`에서 진행.
