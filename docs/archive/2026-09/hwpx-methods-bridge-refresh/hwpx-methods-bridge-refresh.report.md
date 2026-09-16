# HWPX 기초보고서 제2장 5절·제3장 2절 갱신

> **Feature**: hwpx-methods-bridge-refresh
> **Completed**: 2026-09-16
> **Match Rate**: 초기 98.2% → **100% (Act-1 완료)**
> **Author**: Claude (Opus 5) — 결정: 연구책임자
> **Date**: 2026-09-16
> **Status**: Completed
> **Duration**: 2026-09-16 (계획→설계→구현→분석→Act-1→보고, 동일 일자)

---

## Executive Summary

### 프로젝트 개요

| 항목 | 내용 |
|---|---|
| **Feature** | `data/반도체 기초보고서_20260911.hwpx` 원본에서 제2장 5절(연구 방법) 및 제3장 2절 4)항(집계 기준 변경·이전 기준 연결)을 2026-09-15 정본(사전 v2, 실제 PDF 쪽 기준) 수치로 갱신 |
| **방식** | 신규 모듈 `hwpx_methods_bridge.py`(사실·템플릿 적재) + 확장 `hwpx_results_refresh.py`(2단계 실행) + `occurrence_real_pages_impact.py` 데이터 확장 |
| **확인** | `test_hwpx_methods_bridge` 49 + `test_hwpx_results_refresh` 44 + 기존 하니스(24·79·390·32·38) + 실문서 실행(문단 45·표 12·그림 3·토큰 1,052·미일치 0, 재실행 HWPX 바이트 동일) |
| **산출물** | 새 HWPX(비추적), 대조 JSON(추적), 검토 HTML(추적) |

### 결과 요약

| 항목 | 값 |
|---|---|
| 설계 항목 | 109개 |
| 갭 분석(초회) | 98.2% (일치 105 · 부분 4 · 불일치 0, Medium 1 · Low 8) |
| 갭 해소(Act-1) | 9건 → **100%** |
| 문단 | 1단계 재작성 45(제3장 1~3절) · 2단계 삽입 35(제2장 5절 20 + 제3장 2절 15) · 삭제 6 · 재작성 2 · 목차 재작성 7/삭제 2/삽입 1 |
| 표 | 12(1단계 표 7~13 · 2단계 표 4·5·6·12-1·12-2 — 표 12-1·12-2 는 표 12 복제, 고유 id) |
| 그림 | 3(1단계 그림 2~4 SVG 재렌더; 2단계는 그림 없음) |
| 숫자 토큰 | 1,052개 검사(ship 리뷰 뒤 제2장 1절 편입), 미일치 0건 |
| 정본 사전 | v2 (표현 사전 개정, 22개 표현 검토·618건·κ 0.965) |
| 정본 쪽 기준 | NCS 실제 PDF 쪽(줄→쪽 대응표 84권), 교과서 쪽 표식(실제 쪽) |

### 1.3 Value Delivered — 4관점 가치 분석

| 관점 | 내용 |
|---|---|
| **Problem** | 정본 제3장 2절은 등급3 21.7%(출현 기준, 11,517건) 한 숫자만 제시했고, 제2장 5절은 2026-04 방법(목차 기반 쪽 표식, 등급 "페이지 또는 페이지 구역")을 설명했으나 실제는 2026-09-15 방법(실제 PDF 쪽 대응표, 줄→쪽 DP)이다. 표 4 는 NCS 85종으로 표 11의 86종과 어긋났다. 심사에서 "왜 기준이 바뀌었나"·"왜 방법이 다른가"·"표 개수가 왜 다른가" 에 답할 문단과 표가 없다(TODOS 5(a) 이월 항목). |
| **Solution** | `hwpx_methods_bridge.py`(신규, 사실·템플릿) + `hwpx_results_refresh.py` 2단계로 제2장 5절을 표 5(7단계)·표 6(8행, 쪽 기준·집계 단위·등급 임계 포함) + 소제목 1)~6) 본문(초안 A의 템플릿)으로, 제3장 2절 4) "집계 기준의 변경과 이전 결과와의 관계" 소절(문단 2·표 12-1·12-2·주 2·조건 분기)을 추가. 숫자는 추적 JSON/CSV 8종·코드 상수에서 읽고, 감사로 구 수치 차단. 정본이 바뀌면 원본에서 스크립트 재실행 한 번으로 따라간다. |
| **Function/UX Effect** | 출판 문서(HWPX)와 대시보드·README 수치 일치(NCS 86권·11,517건·실제 2,492쪽·등급3 143쪽·5.7%, 출현 기준 21.7%), 변환 방법·집계 기준 변경 효과(출현 4,016건·34.9% 등급 변경)·이전 기준(2026-09-06 발표, 2,189쪽·등급3 145)과의 관계(쪽 집합은 검출 방식, 비율은 분모 차이; 공유 2,035쪽 등급 일치 100%)를 표와 문단으로 명시. 대조 JSON 으로 모든 숫자의 출처 추적 가능. TODOS 5(a) 종결. |
| **Core Value** | "발표 문서 수치 ← 손 수정 ← 정본" 의존성을 "발표 문서 ← 스크립트(정본 JSON) ← 코드" 로 역전해 데이터 일관성·감사 추적성 보증. 새로운 결정 기준(A+B3, D1~D6 모두 (a))을 코드·템플릿·테스트로 고정하는 "PDCA 결과의 자동화". |

---

## PDCA 사이클 요약

### Plan
- **문서**: `docs/01-plan/features/hwpx-methods-bridge-refresh.plan.md` (Approved)
- **목표**: 정본 HWPX 제2장 5절·제3장 2절 갱신, 방법 서술 일치, 집계 기준 변경 효과 설명, 테스트 60% 이상, 감사 통과
- **소요**: 1일(2026-09-16)
- **결정**: D1~D6 모두 (a) — 연구책임자 2026-09-16 승인

### Design
- **문서**: `docs/02-design/features/hwpx-methods-bridge-refresh.design.md` (Implemented)
- **설계 항목**: 109개 (데이터 확장·사실 모델·XML 능력·절차·템플릿·감사·대조 JSON·백업·테스트·문서)
- **주요 결정**:
  - D1: 출력 파일 같은 이름 `…_20260915_정본.hwpx`, 기존 파일 `.bak` 보존
  - D2: 쪽 단위 등급 수를 `occurrence_real_pages_impact.py` 확장(추적 JSON·테스트)
  - D3: JSON 없는 값(상수·변환 보고서 4건)은 코드·문장에서 제외 또는 데이터로 대체
  - D4~D6: 표 12-2 4열, 소절 번호 4)→5), 표 4 정정(86종·13·24)

### Do
- **구현 파일**:
  - 신규: `hwpx_methods_bridge.py`(MethodsFacts·BridgeFacts·템플릿·적재, 545줄)
  - 확장: `hwpx_results_refresh.py`(2단계·XML 능력·장부 검사·백업, +471/−82줄)
  - 확장: `occurrence_real_pages_impact.py`(pages.real_page_grades·pages.교과서)
  - 신규 테스트: `test_hwpx_methods_bridge.py`(49 — ship 리뷰 가드·캐시·적대적 리뷰 테스트 13 포함)
  - 확장 테스트: `test_hwpx_results_refresh.py`(fixture 제2장·2절 꼬리 확장, 44 유지, `CommittedDiffTests` 갱신), `test_semantic_keyword_recount.py`(`ImpactScriptTests` +2), `outputs/test-dashboard-data.js`(S3o 확장, 79 유지)

### Check
- **분석 문서**: `docs/03-analysis/hwpx-methods-bridge-refresh.analysis.md`
- **초회 결과**: 98.2% (109항목: 일치 105 · 부분 4 · 불일치 0)
- **갭**: 9건 (G1~G9: Medium 1 · Low 8)
  - G1: 목차 소제목 수 가드
  - G2: 계보 불일치 테스트 확장
  - G3: 감사 패턴·구 수치 심기 테스트
  - G4~G9: 산출물 기록·선제 거부·경계값·결정 기록·문구

### Act (Act-1)
- **처리**: 9건 갭 모두 닫힘
- **검증**: Act-1 시점 `test_hwpx_methods_bridge` 40 + `test_hwpx_results_refresh` 44(최종 49 + 44, 아래 §6) + 하니스 통과, 실문서 실행(조건 분기 양쪽 테스트, 재실행 HWPX sha256 동일)
- **결과 Match Rate**: **100%**

---

## 산출물 & 검증

### 추적 산출물

| 파일 | 형식 | 내용 | 비고 |
|---|---|---|---|
| `docs/03-analysis/data/hwpx_results_refresh_20260915.json` | JSON | 문단·표·그림별 구/신 수치·출처 키·조건·감사 상태 | `methods`·`bridge` 블록 추가; `audit.out_of_scope` 제거; 실행 환경(백업·동일 여부)은 화면에만 |
| `docs/03-analysis/hwpx-results-refresh/review.html` | HTML | 표 11개(표 7~13 + 표 4·5·6·12-1·12-2, 헤더 행 표시) + 그림 3 | 본문 문장 없음 |
| `docs/03-analysis/data/occurrence_real_pages_impact.json` | JSON | `pages.real_page_grades` 1,825/524/143 · `pages.교과서` 388(335/45/8) 추가 | 재실행(2026-09-16), 총계·이동 행렬 불변 |

### 비추적 산출물

| 파일 | 형식 | 내용 | 용도 |
|---|---|---|---|
| `data/반도체 기초보고서_20260915_정본.hwpx` | ZIP | 원본 + 2단계 갱신 제2장 5절·제3장 2절 | 발표 문서 |
| `data/반도체 기초보고서_20260915_정본.hwpx.235ec03f.bak` | ZIP | 덮어쓴 이전 정본(2026-09-15, 한글 재저장본) — 8자리 이름은 ship 리뷰 전 규칙의 산출물 | D1 안전 장치 |
| `data/반도체 기초보고서_20260915_정본.hwpx.e9856fad.bak` | ZIP | 대조 JSON 재생성(G4) 때의 백업(8자리, ship 리뷰 전) — 그 시점 정본과 바이트 동일; 최종 정본은 `161d2408…`(ship 리뷰 문구 반영 뒤), 직전 출력은 `.573484cb3e9a41b7.bak`(16자리, 현재 규칙) | 결정론 증거 |
| `data/hwpx-results-refresh/review_text.html` | HTML | 절·문단별 구/신 문장 병기(본문 포함) | 검수용(비추적) |

### 검증 항목

| 항목 | 결과 | 근거 |
|---|---|---|
| 설계 항목 구현률 | 100% (109/109) | 갭 분석 Act-1 완료 |
| 정본 수치 매칭 | 100% | `semantic_summary.json` v2 정본 실행(2026-09-15) |
| 숫자 감사 | OK (1,052 토큰·0 미일치) | 추적 파일 8종 + 코드 상수 1(`EXCEL_MAX_CHARS`) |
| 테스트 | unittest 4모듈 OK · 하니스 563 | `test_hwpx_methods_bridge` 49 + `test_hwpx_results_refresh` 44 + semantic·expression; 24/79/390/32/38 |
| 재현성 | OK (동일 입력 → 동일 HWPX sha256) | `--force` 재실행 검증 |
| 조건 분기 | 양쪽 테스트 | 동사(늘었/줄었/거의), 비율(↑/↓/동일), 일부/모두, 임계값 |

---

## 연구책임자 결정 기록

### 기본 결정 (D1~D6, 계획 §6)

| 항목 | 선택지 | 채택 | 반영 |
|---|---|---|---|
| **D1 출력** | (a) 같은 이름 `.bak` 보존 / (b) 새 이름 v2 | (a) | 정본 실행일 규칙 유지, 기존 파일 `.235ec03f.bak`; 백업 이름은 ship 리뷰 뒤 `<이름>.<sha16>.bak` |
| **D2 데이터** | (a) impact JSON 확장 / (b) HWPX 스크립트가 xlsx 읽기 | (a) | `pages.real_page_grades` 1,825/524/143 + 테스트 |
| **D3 상수** | (a) import + 코드·문장 정제 / (b) 주석 상수표 | (a) | `SAFETY_MIN`·`ACTION_MIN` 설계에서 JSON 으로 대체 |
| **D4 표 12-2** | (a) 4열(이전 쪽·정본 쪽·정본 출현) / (b) 3열 | (a) | 같은 표에서 분모 3종 명시 |
| **D5 소절** | (a) 새 4) + 소결 5) / (b) 3) 안에 무제 | (a) | 목차 갱신, 소결 5) 호출 |
| **D6 표 4** | (a) 포함(86·13·24) / (b) 제외 | (a) | `corpora.NCS.groups[].documents` 정본값 |

### 구현 결정 기록 (설계 §6)

| 항목 | 결정 | 근거 |
|---|---|---|
| **임계 6·5** | `regrade_impact.json.rule` 에서 읽음 | JSON 이미 있음, 상수 이동 불필요 |
| **날짜** | ISO 형식(`2026-09-15`, `2026-09-06`) | 정본 `generated_at`·`previous_basis.date` 정규화 |
| **삭제 범위** | 첫~끝 locator 연속 최상위 문단 6개 | "각 문단 뒤 빈 문단" 규칙과 일치, 구현 단순 |
| **표 4 셀** | "반도체개발" 로 시작하는 문단을 가진 셀 | 행·열 위치보다 견고 |
| **최대 표식 폭** | 58 (`;` 분리 `구라벨` 최대값) | `ncs_pages_reseg.csv` 산출, 초안의 `|` 분리 오류 정정 |
| **소결 문장** | 새 문단(마지막 소결에 `ctrl` run) | `set_text` 불가라 뒤에 삽입 |

---

## 구현 요약

### 데이터 출처 (8종)

| 파일 | 용도 | 검증 |
|---|---|---|
| `semantic_summary.json` | NCS 86권·11,517건·출현 등급·분야·쪽수 | meta.run.generated_at 2026-09-15, expected true |
| `occurrence_real_pages_impact.json` | NCS 2,492쪽·등급 1,825/524/143, 교과서 388쪽·335/45/8 | pages 블록 확장(D2), 불변식 테스트 |
| `reseg_summary.json` | 이전 기준 2,189쪽·1,519/525/145(정본 `meta.previous_basis` 사본과 대조), 정렬 자기검증 23권·21,711줄·83.6%/94.9%, 검색 행 7,769 | 공유 쪽 일치 2,035/2,035 는 `semantic_summary.json meta.run.reseg_agreement` |
| `ncs_pages_reseg.csv` | 한 표식(구라벨)이 덮은 실제 쪽 최대 58 | `구라벨` 을 `;` 로 나눈 (교재, 라벨) 별 행 수 |
| `regrade_impact.json` | 임계(안전 6·조치 5), 규칙 재현율 99.6%(1,839/1,847쪽) | rule.safety_min·action_min 읽음 |
| `recoding_scores.json` | 규칙 검증 표본 538쪽(44+85+109+300), 정밀도 80~84%·재현율 13~21% | 코더 C·B baseline, population strata |
| `expression_review_*.json` | 사전 v2 검토 22표현·최대 30건·618건·612유효·17불일치·κ 0.965·95%·0.8, 보류 2·조건부 4, v1fix→v2 12,310→11,517·1,272→1,207 | key·scores·impact |
| `summary.json` | NCS 절단 16쪽 | ncs.truncated_pages |

### 주요 기능

| 모듈 | 클래스/함수 | 역할 |
|---|---|---|
| `hwpx_methods_bridge.py` (신규) | `MethodsFacts` dataclass | 제2장 5절 사실 36필드(권수·사전 검토·대응 검증·규칙 검증·재현성) |
| | `BridgeFacts` dataclass | 제3장 2절 사실 21필드(블록/실제 쪽 등급·이동·쪽 단위·이전 기준·공유 쪽) |
| | `load_methods_facts` / `load_bridge_facts` | 정본 파일 적재, 계보 가드 7종 |
| | `methods_paragraphs` / `bridge_paragraphs` | 템플릿 생성(설계 분기 5종 + 보조 3종, 양쪽 테스트) |
| | `bridge_table1_rows` / `bridge_table2_rows` | 표 12-1·12-2 행 데이터 |
| `hwpx_results_refresh.py` (확장) | `clone_paragraph` | 문단 깊은 복사 + 텍스트 교체 |
| | `insert_after` / `remove_paragraphs` | XML 순서 편집 |
| | `next_object_ids` | 표 id·zOrder 를 문서 최댓값+1 로(결정적) |
| | `clone_table_paragraph` | 표 복제, 고유 ID·행 수 조정 |
| | `locate_range` / `locate_toc_block` | 절·목차 탐지(발생 번호 지정) |
| | `check_untouched` | 손댄 집합 검사(순번 검사 대체) |
| | `refresh_methods_bridge` | 2단계 조립(A·B3 절차 호출) |

### 감사 & 불변

| 항목 | 범위 | 결과 |
|---|---|---|
| 숫자 토큰 | 제2장 1절·5절 + 제3장 재탐지(1~3절) + 목차 + 삽입 문단 | 1,052개·미일치 0 |
| STRIP 패턴 | 연-월(2026-04)·표 12-1·v1fix/v1/v2·3-gram·±1쪽 (+ 기존 날짜·표/그림 번호·목차 번호·(n)·등급 1~3) | 확장 5 |
| 범위 외 문단 | 최상위 `hp:p` 구조·ET 직렬화 | 100% 일치(빈 태그 표기 제외) |
| ZIP 항목 | 교체(section0.xml·BinData) 외 | 바이트 동일 |

---

## 교훈 & 이월

### 잘 된 점

1. **데이터 주도 설계**: 추적 JSON 8종에서 정본값을 자동 적재해 손으로 수치를 넣을 일이 0건.
2. **조건 분기 완전 테스트**: 불가능한 상황(예: 등급3 비율 < 쪽 비율) 포함해 8가지 경로를 양쪽 모두 검증.
3. **모듈 분리로 순환 import 회피**: `hwpx_methods_bridge` 는 `hwpx_results_refresh` 를 import 하지 않고, `Facts` 의 `methods`·`bridge` 필드로 결합.
4. **갭 분석 의도적 활용**: 98.2%→100% 격차를 1일 내 명시적으로 닫아 설계·구현 일관성 입증.

### 개선 여지

1. **숫자 감사의 다의성(알려진 한계)**: 85(control 층)·30(키워드·분야 권수) 같은 작은 수가 우연에 일치하면 통과 — 문맥 무시. 대조 JSON `keys` 로 추적하도록 보상.
2. **산출물 재입력 불가**: 원본에서만 출발 가능. 정본을 입력으로 주면 선제 거부(`"이미 2단계 산출물"` 메시지). 수치 변경 시 원본 재실행 필수.
3. **한글 렌더링 미자동화**: 표 너비·쪽 넘김·목차 쪽수 검증은 HWP 소프트웨어 필요 — `[→E2E]` 항목.

### 후속 항목 (TODOS "기초보고서 보강 후속")

| ID | 항목 | 이유 |
|---|---|---|
| B1 | 교재별 집중·편차(안전관리 2권 38.6%, 파일 중앙값 0%) | 파일별 등급 분포가 추적 JSON 에 없음 — `semantic_summary.json` 확장 필요 |
| B2 | 보조 분모(100쪽당 출현, 검출 쪽 비율, 키워드별 출현 교재 수) | 정본 JSON 으로 계산 가능, 문안 미작성 |
| B4·B5 | 판정 한계 상자·원문 검토 목록 | file_insights §3·§6 — 문안 미작성 |
| C | 교과서 보강(T05·T04 96.5%, 법·제도 키워드 0/9) | 문안 미작성 |
| D·E·F | 검증 부록·30 키워드×교육주제 점검표·근거–설계 연결표 | 부록 표 미작성 |
| Codex | 표 21·22 분모, 표 14 문헌, 해외 사례, 표 1 질소, 학생 역할, 설문, 목차 시수 + 본문 검토 메모·각주 중복 | 원저자 |
| E2E | 한글에서 5절 길이·2절 표 2개 뒤 쪽 넘김·표 12-1·12-2 열 너비 | HWP 필요 |

---

## 재현 절차

### 환경

- Python 3.12+ (CI 3.12, 로컬 3.13) · ImageMagick `magick`(그림; `--no-render` 면 불필요) · openpyxl 불필요
- 입력: `docs/03-analysis/data/semantic_summary.json`(2026-09-15, v2), `occurrence_real_pages_impact.json`, `reseg_summary.json`, `ncs_pages_reseg.csv`, `regrade_impact.json`, `recoding_scores.json`, `expression_review_*.json`, `summary.json`

### 실행

```bash
python3 hwpx_results_refresh.py \
  --hwpx data/반도체\ 기초보고서_20260911.hwpx \
  --out data/반도체\ 기초보고서_20260915_정본.hwpx \
  --diff-out docs/03-analysis/data/hwpx_results_refresh_20260915.json \
  --review-dir docs/03-analysis/hwpx-results-refresh \
  --force
```

### 테스트

```bash
python3 -m unittest test_hwpx_methods_bridge test_hwpx_results_refresh      # 49 + 44
python3.13 -m unittest test_semantic_keyword_recount test_expression_review  # openpyxl 필요
node outputs/test-dashboard-data.js                                         # 79 (S3o 확장)
python3 outputs/test-recount-grades.py; node outputs/test-search-equivalence.js; node outputs/run-core-logic-tests.js; node outputs/test-sri.js
```

---

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 1.0 | 2026-09-16 | 초안 — 계획·설계·분석(98.2%→100%)·실행·보고 통합 | Claude (Opus 5, report-generator) |
| 1.1 | 2026-09-16 | 사실 정정 — 문단·표·그림 수(1·2단계 구분), 백업 파일 이름, 산출물 표(data.js 아님 → impact JSON), 출처 표, 후속 표 | Claude (Opus 5) |
| 1.2 | 2026-09-16 | ship 리뷰 반영 — critical 1(`main()` 스텁 KeyError)·informational 40여 건(레드팀 12·유지보수 13·테스트 11·디자인 6·보안 2·성능 1): 계보 가드, 꼬리 글, 백업 원자성, 추적 JSON 에서 실행 환경 제거, 감사 범위(제2장 1절), 테스트 45 | Claude (Opus 5) |
