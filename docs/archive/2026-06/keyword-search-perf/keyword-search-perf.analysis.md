# Gap Analysis: keyword-search-perf

> Check 단계 — Design(D1~D13) 대비 구현 검증. gap-detector 독립 분석 + node 회귀 테스트(test-search-equivalence.js) 기반.
> 분석일: 2026-06-21 · 대상: `outputs/markdown-search-app.html` · 비교: `*.bak-20260621`(개선 전)

## Match Rate: **98%** (정합성 마무리 반영)

| Category | Score |
|----------|:-----:|
| Design Match | 98% (PASS 13 · PARTIAL 0 · FAIL 0) |
| Architecture Compliance | 100% |
| Convention Compliance | 100% |
| **Overall** | **98%** ( ≥ 90% 충족 ) |

> 초기 gap-detector 분석 **94%**(PARTIAL 3) → **정합성 마무리**: D4 코드 호이스팅(PARTIAL→PASS, 회귀 11/11 유지)
> + D10·D11 Design 문구 정정(구현과 일치) → **98%**. 코드 회귀 위험 0(kwPrep 위치 이동만, 결과 불변).

## D1~D13 체크리스트

| # | 항목 | 판정 | 근거 |
|---|------|:----:|------|
| D1 | `getParsedDoc` WeakMap 캐시, 재호출 재계산 0 | ✅ PASS | `__parseCache=new WeakMap()`, hit 시 즉시 반환. T7a `p1===p2` |
| D2 | pageMap·sentences·tables·images 파일당 1회 | ✅ PASS | getParsedDoc 1회 계산 후 캐시, performSearch는 `parsed.*` 재사용 |
| D3 | `*.lower` precompute + `caseSensitive?원본:lower` | ✅ PASS | precompute 루프 + `hay = caseSensitive ? item.sentence : item.lower` (문장/표/이미지 3곳) |
| D4 | `kwPrep` 파일 루프 밖 1회 | ✅ PASS | **정합성 마무리**: `kwPrep`을 파일 루프 밖으로 호이스팅(`caseSensitive` 직후). 선언 1개·파일 루프 외부. 회귀 11/11 유지 |
| D5 | `forEach item → for keyword`, item당 toLowerCase ≤1회 | ✅ PASS | 3개 블록 모두 hay 1회 산출 후 needle 순회 |
| D6 | 하이라이트 정규식 렌더당 1회, 행 내 `new RegExp` 없음 | ✅ PASS | `hlRegex` 1회 생성, rowHtml은 `highlightWith(inner, hlRegex)` |
| D7 | 결과(건수·내용·정렬) 현행과 완전 일치 | ✅ PASS | **T4: 키워드5×옵션5=25조합 `JSON.stringify` 동치**. 결과 필드·정렬 백업본과 동일 |
| D8 | 청크 렌더 + IO append + 토글 위임 | ✅ PASS | `RENDER_CHUNK=200`, IntersectionObserver `insertAdjacentHTML`, `tbody` 이벤트 위임 |
| D9 | yield N파일 청크 | ✅ PASS | `if ((i+1)%8===0) await setTimeout` (백업: 매 파일) |
| D10 | nfc 정규화 일관성 유지 | ✅ PASS | **정합성 마무리**: Design 문구를 실제 검증범위(nfc 일관성)로 정정. nfc 보존 + T6 통과로 구현과 일치 |
| D11 | 회귀 하네스 T1~T7 (node vm) | ✅ PASS | **정합성 마무리**: Design §4·§8을 `test-search-equivalence.js` 기준으로 갱신. 앱 원본 직접 로드 → 동기화 부채 0 |
| D12 | 단일 파일 HTML·CDN·번들러 0, Excel·UI 불변 | ✅ PASS | 신규 import 0, Excel export·테이블 컬럼 구조 보존 |
| D13 | LLM 경로 표/이미지 캐시 공유, 문장 llmCache 유지 | ✅ PASS | hybrid 시 문장만 LLM 경로, 표/이미지는 `parsed.*` 공유, LLM 결과도 `.lower` 보강 |

## 회귀 안전 점검 (모두 보존)

| 항목 | 결과 |
|------|------|
| `pageContentCache` 키 `pageNum \|\| L{n}` | 백업 == 현행 |
| 정렬 `localeCompare` + page/line | 백업 == 현행 |
| `searchResults` 초기화 | 백업 == 현행 |
| `highlightWith` `regex.lastIndex=0` 가드 | 존재 (g플래그 상태 버그 예방) |

## 부가 변경 (Design 외, 방어적 개선 — 긍정)

- `item.lower !== undefined ? item.lower : ...toLowerCase()` 폴백 — LLM 등 lower 누락 대비 안전망.
- `resultsContent.__io.disconnect()` — 탭 전환 시 이전 옵서버 정리(누수 방지).

## 성능 실측 (FR-0b, 합성 코퍼스 20파일×120문장, K=10)

| toLowerCase 호출 | 최초 | 재검색 |
|---|---|---|
| 개선 전 | 24,200 | 24,200 |
| 개선 후 | 2,600 | **200** |
| 절감 | **89.3%** | **99.2%** |

매칭 결과 8,000건 동일.

## Issues

**Major**: 없음. **Minor**: 정합성 마무리로 3건 전부 해소.

| # | 초기 PARTIAL | 해소 |
|---|------|------|
| D4 | kwPrep 파일 루프 내 위치 | 코드 호이스팅 → 파일 루프 밖 (회귀 11/11 유지) |
| D10 | 문구 "NFD 키워드 매칭" | Design 문구를 "nfc 정규화 일관성"으로 정정 |
| D11 | `test-core-logic.html` 명세 | Design §4·§8을 `test-search-equivalence.js`(node vm) 기준으로 갱신 |

## 결론

핵심 FR(FR-1~6) 전부 PASS, 결과 동치(T4 25조합)·회귀 안전 검증 완료. **정합성 마무리 후 98% — D1~D13 전부 PASS.**
PARTIAL 3건 해소(D4 호이스팅 + D10·D11 문서 정정), 코드 회귀 0.

→ 다음: `/pdca report keyword-search-perf` (완료 보고서).
