# Completion Report: keyword-search-perf

## Executive Summary

| 항목 | 내용 |
|------|------|
| Feature | keyword-search-perf (키워드 문서분석 루틴 리뷰 및 성능개선) |
| 대상 | `outputs/markdown-search-app.html` (키워드 모드 검색 엔진) |
| 기간 | 2026-06-21 (Plan→Design→Do→Check→Report, Rev 2) |
| Match Rate | **98%** (D1~D13 전부 PASS) |
| Iteration | 0 (정합성 마무리 1회로 94%→98%) |
| 회귀 테스트 | 11/11 PASS (`test-search-equivalence.js`) |
| 코드 변경 | +207 / −142 (1963 → 2028줄) |

### 1.3 Value Delivered

| 관점 | 결과 (메트릭 포함) |
|------|--------------------|
| **Problem** | 재검색마다 코퍼스 전체 재파싱(`split`·`buildPageMapping`·`extract*`) + 키워드 수만큼 동일 텍스트 반복 소문자화 → 코퍼스·키워드 증가 시 지연 선형 누적 |
| **Solution** | `getParsedDoc()` WeakMap 캐시 + 소문자본 precompute + 검색 루프 `item 바깥/keyword 안쪽` 전환 + 하이라이트 정규식 호이스팅 + 200행 청크 렌더(이벤트 위임). node `vm` 회귀 하네스로 동작 동일성 자동 보장 |
| **Function UX Effect** | 키워드만 바꿔 재검색 시 추출 비용 **0회**(캐시 히트) → 즉시 응답. 대용량 결과도 청크 렌더로 초기 멈춤 제거 |
| **Core Value** | 탐색 루프 반복 비용 **O(코퍼스 전체) → O(매칭 결과)**. `toLowerCase` 호출 **재검색 99.2%↓**(24,200→200), 최초 89.3%↓. 매칭 결과 **완전 동일**(회귀 0). 단일 파일 HTML·CDN 원칙 유지 |

## 2. PDCA 진행 이력

```
[Plan] ✅(Rev2) → [Design] ✅ → [Do] ✅ → [Check] ✅ 94% → [정합성] ✅ 98% → [Report] ✅
```

| Phase | 상태 | 산출물 |
|-------|:----:|--------|
| Plan | 완료(Rev 2) | `docs/01-plan/features/keyword-search-perf.plan.md` — 병목 B1~B8, FR-0~FR-9 |
| Design | 완료 | `docs/02-design/features/keyword-search-perf.design.md` — 코드 레벨 설계, D1~D13 |
| Do | 완료 | `outputs/markdown-search-app.html` + `outputs/test-search-equivalence.js` |
| Check | 98% | `docs/03-analysis/keyword-search-perf.analysis.md` (gap-detector) |
| Act | 불필요 | 94%→98% 정합성 마무리(코드 1건 + 문서 2건), iterate 미사용 |

> **특이사항**: 착수 시 소스가 워킹 트리에 부재(git 손상). iCloud 아카이브에서 복원(diff 동일 검증) 후 진행.

## 3. 구현 상세

### 변경 파일

| 파일 | 변경 | 규모 |
|------|------|------|
| `outputs/markdown-search-app.html` | 성능개선 구현 | +207/−142 (1963→2028) |
| `outputs/test-search-equivalence.js` | 회귀 테스트 신설(node vm) | 신규 |
| `outputs/markdown-search-app.html.bak-20260621` | 변경 전 백업 | 신규 |

### 구현 요구사항 (FR)

| FR | 항목 | 구현 |
|----|------|------|
| FR-1 | 파일별 파싱 캐시 | `getParsedDoc()` + `WeakMap` — 코퍼스 재로드 시 객체 GC로 자동 무효화 |
| FR-2 | 소문자 precompute | `sentence.lower`/`table.lower`/`searchText.lower` 파일당 1회 |
| FR-3 | 검색 루프 전환 | `forEach item → for keyword`, `kwPrep` 파일 루프 밖 1회(D4 정합성) |
| FR-4 | 정규식 호이스팅 | `renderResultsTable`당 `hlRegex` 1회 + `highlightWith(lastIndex=0)` |
| FR-5 | 청크 렌더 | `RENDER_CHUNK=200` + IntersectionObserver append + 토글 이벤트 위임 |
| FR-6 | yield 청킹 | 8파일마다 양보(was 매 파일) |
| FR-8 | NFC 일관성 | 현행 이미 일관(시트명·content `nfc`) — 무코드, 불변성 테스트로 고정 |
| FR-9 | 회귀 하네스 | `test-search-equivalence.js` (T1~T7, 앱 원본 vm 로드 → 동기화 부채 0) |
| FR-7 | 다중 키워드 단일 패스 | **보류**(K=시트수로 작아 이득 제한적) |

### 회귀 안전 (백업본 대비 보존)

`pageContentCache` 키 규칙 · 정렬(`localeCompare`+page/line) · `searchResults` 초기화 · 결과 객체 필드 — 전부 동일.
부가 방어: `item.lower` 폴백, 탭 전환 시 `IntersectionObserver` 정리.

## 4. Gap Analysis 결과

### Match Rate: 98% (정합성 마무리 후)

| Category | Score |
|----------|:-----:|
| Design Match | 98% (PASS 13 · PARTIAL 0 · FAIL 0) |
| Architecture Compliance | 100% |
| Convention Compliance | 100% |

초기 gap-detector 94%(PARTIAL 3) → 정합성 마무리(D4 호이스팅 + D10·D11 Design 정정) → 98%.

## 5. 품질 지표

| 지표 | 값 | 비고 |
|------|-----|------|
| Match Rate | 98% | 기준 90% 초과 |
| `toLowerCase` 절감 | 재검색 99.2% / 최초 89.3% | 합성 20파일×120문장, K=10 |
| 재검색 추출 실행 | 캐시 히트 시 0회 | was 매 검색 전체 재추출 |
| 결과 동일성 | 25조합 완전 일치 | T4 (키워드5×옵션5) |
| 회귀 테스트 | 11/11 PASS | T1~T7 |
| Major 결함 | 0 | — |
| 코드 증가 | +65줄 순증 | 적정 규모 |

## 6. 후속 권장사항

1. **브라우저 수동 확인**: FR-5 청크 렌더·스크롤 append·토글 동작은 node 검증 범위 밖 → `outputs/server.py` 구동 또는 파일 직접 열기로 대용량(1000행+) 실측.
2. **실코퍼스 측정(FR-0b)**: 전처리 `.py`(page_utils 등) 복원 → 마커 삽입한 NCS 코퍼스로 `performance.now()` 실측.
3. **FR-7 재검토**: 측정이 목표 미달일 때만 다중 키워드 단일 패스 도입.
4. **TODOS 연계**: 마커 전면 보급 시 `buildPageMapping` Strategy 2(TOC+DP 200줄) dead-code 제거.
5. **CI 연계**: `node outputs/test-search-equivalence.js`(exit code)로 회귀 게이트 자동화 가능.
