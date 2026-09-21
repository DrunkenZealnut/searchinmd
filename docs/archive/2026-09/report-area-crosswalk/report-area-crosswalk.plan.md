# 교과서 4영역 대응 변경(『반도체 인프라 일반』 재료 → 장비)을 정본 산출물까지 반영하는 계획

> **Summary**: 2026-09-19 Codex 세션이 연구책임자 지시로 『반도체 인프라 일반』의 연구상 대응을 재료 → 장비로 바꾸고 대응표를 공용 모듈(`semantic_report_areas.py`)로 옮겼으나(기능 `semantic-report-area-symmetry`), 범위를 Markdown 보고서(비추적)로 한정해 **기초보고서 HWPX·추적 대조 JSON·검토 HTML·문서는 옛 대응(재료)에 남아 있다**. 그 결과 코드는 "장비", 출하 산출물은 "재료"로 갈라졌고, 테스트가 옛 대응을 mock 으로 되살려 그 불일치를 가리고 있다. 이 기능은 같은 결정(2026-09-21 재확인, A.b)을 정본 산출물 전체에 끝까지 적용하고 mock 을 없앤다.
>
> **Project**: SearchInMD
> **Feature**: report-area-crosswalk (= `semantic-report-area-symmetry` 의 2단계)
> **Author**: Claude (Opus 5) — 결정: 연구책임자
> **Date**: 2026-09-21
> **Status**: Approved — 2026-09-21 연구책임자 결정 D1~D5 확정 (§6)
> **Level**: Starter
> **Branch**: `feat/report-area-crosswalk` (09-19 작업 트리를 2026-09-21 격리, 미커밋)

---

## Executive Summary

| 관점 | 내용 |
|---|---|
| **Problem** | 『반도체 인프라 일반』(197쪽·출현 501건 = 교과서 출현의 41.5%·등급 3 83건)은 출하된 2026-09-17 정본 HWPX 1절 2) (4)에서 "반도체 재료·인프라 분야 1권 197쪽 9.6%"의 근거이자 유일한 구성 교재다. 09-19 에 이 책의 대응이 장비로 바뀌었지만 HWPX·`hwpx_results_refresh_20260917.json`·`review.html`·README/CLAUDE.md 는 갱신되지 않았고, `test_hwpx_results_refresh.py` 는 옛 대응을 `mock.patch.dict` 로 되살려 커밋 JSON 검사를 통과시킨다 — 코드·문서·산출물이 세 갈래다. 게다가 디스크의 정본 HWPX 는 09-19 13:28 Polaris Office 재저장본(sha `9ef93187…`)이라 대조 JSON 의 `output_sha256`(`aa0f3453…`)과도 이미 다르다. |
| **Solution** | 공용 대응표(장비)를 그대로 두고 **HWPX 3단계까지의 파이프라인을 원본에서 다시 돌려** 1절 2) 문단·표 8·감사·대조 JSON·검토 HTML 을 새 대응으로 재생성한다. 빈 영역(교과서 재료 0권)과 2권 영역(장비)을 데이터 분기로 처리해 "0권, 총 0쪽" 같은 문장이 나오지 않게 하고, 역사 mock 을 지우며, 문서·TODOS·대시보드 설명을 맞춘다. 09-19 의 Markdown 절·`--skip-xlsx-write`·테스트는 그대로 승계한다. |
| **Function/UX Effect** | 보고서 1절 2)는 "장비 분야 2권 414쪽(20.1%) — 『반도체 장비 유지보수』·『반도체 인프라 일반』"과 "재료 분야는 해당 교과서 없음"으로, 표 8 의 재료 행은 0 으로 읽히고, Markdown 4영역 표·HWPX·코드가 같은 대응표 하나를 가리킨다. 정본 수치(11,517 / 1,207, 해시 4종)는 변하지 않는다 — 바뀌는 것은 교과서 영역 표시값과 그에 걸린 문장뿐이다. |
| **Core Value** | "코드가 말하는 분류 = 출하 문서가 말하는 분류". 연구상 분류 결정 한 건이 대응표 한 줄로만 존재하고, 그 줄이 바뀌면 산출물 전부가 스크립트 한 번으로 따라온다는 이 리포지토리의 원칙(hwpx-ncs-section-refresh 이후)을 09-19 변경에도 지킨다. |

---

## 1. 개요

### 1.1 목적

09-19 에 결정·구현된 교과서 대응 변경(『반도체 인프라 일반』 → 장비)을, 그때 범위 밖으로 두었던 정본 HWPX·추적 대조 JSON·검토 HTML·문서에 적용해 코드와 산출물을 다시 한 정의로 맞춘다. 정본 수치·해시·XLSX 는 바꾸지 않는다.

### 1.2 배경

- **1단계(2026-09-19, Codex, `semantic-report-area-symmetry`)** — 계획 "Approved — 2026-09-19 사용자 실행 지시". 산출: `semantic_report_areas.py`(AREA_ORDER·AREA_DISPLAY·NCS_GROUP_TO_AREA·TEXTBOOK_GROUP_TO_AREA·TEXTBOOK_CLASSIFICATION_ROWS·`area_for` 실패 폐쇄), `semantic_keyword_recount.py` 의 `area_distribution_rows`·`_area_distribution_markdown`(Markdown 보고서 "## 4영역별 키워드·등급 분포" 절, NCS·교과서 대칭 표 + 교과서 9권 대응 근거표)·`--skip-xlsx-write`, HWPX 두 모듈의 로컬 대응표 삭제·공용 import, 테스트 6건(unittest 247 → 253). `data/semantic_keyword_recount_20260917_report.md`(비추적)는 재생성됨(09-19 17:06). 명시적 제외: "HWPX 본문·표·그림의 재생성 또는 문안 변경", "`semantic_summary.json`·대시보드 갱신". 그 분석 문서의 권고 1 이 바로 이 기능이다: "현재 HWPX 정본도 새 연구상 대응으로 맞추려면 별도 변경 범위로 재생성하고 표·문장·그림 및 변경대조 JSON을 함께 갱신한다."
- **불일치의 실체(2026-09-21 실측)** — `hwpx_results_refresh.py` 는 이제 공용 대응표(장비)를 읽으므로 지금 실행하면 새 대응으로 출력되지만, 추적 대조 JSON 은 옛 출력(`output_sha256 aa0f3453…`, 삽입 14·layout 124/912/124)을 담고 있고 `CommittedDiffTests` 는 `mock.patch.dict(HR.TEXTBOOK_AREA, {"반도체 인프라 일반": "재료"})` 로 옛 대응을 되살려 숫자 감사를 통과시킨다. 디스크의 `data/반도체 기초보고서_20260917_정본.hwpx` 는 sha `9ef93187…`, `version.xml appVersion="9, 1, 1, 5656 PolarisOffice_"`, 최상위 문단 1,425개 전부에 `hp:linesegarray` 있음(스크립트 출력은 124개가 없음) — 09-19 13:28 Polaris 재저장본이다. 09-19 분석 문서가 "HWPX SHA 9ef93187 전후 동일"이라고 적은 것은 이 재저장본을 기준으로 한 것이며, 스크립트 출력(`aa0f3453…`)과 같다는 뜻이 아니다.
- **연구책임자 결정 2026-09-21** — A.b 『반도체 인프라 일반』을 장비로(09-19 결정 재확인) · B 정식 PDCA 로 구현 · D 09-19 작업 트리를 브랜치로 격리(`feat/report-area-crosswalk`, 커밋 없음).
- **왜 정본 재실행(`semantic_keyword_recount.py`)은 필요 없는가** — 4영역 접기는 `semantic_summary.json` 에 저장되지 않는다(`corpora.교과서.groups[]` 는 교재별 9행 그대로; 영역 합산은 `hwpx_results_refresh.corpus_facts(…, TEXTBOOK_AREA.get)` 과 `area_distribution_rows` 가 읽을 때 한다). 따라서 정본 JSON·data.js·분석 페이지·`EXPECTED`·해시 4종·XLSX 는 이번에 손대지 않는다. 대시보드도 교과서는 `groups[]`(교재별)만 그리므로 4영역 대응과 무관하다(`S1x`).

### 1.3 실측 — 대응 변경이 바꾸는 값 (정본 `semantic_summary.json` 2026-09-17 에서 계산)

| 교과서 영역 | 현행(인프라 일반 = 재료) | 변경(인프라 일반 = 장비) |
|---|---|---|
| 개발 | 3권 · 639쪽(31.1%) · 출현 136(11.3%) · 등급 114/22/0 | 변화 없음 |
| 제조 | 4권 · 1,002쪽(48.8%) · 출현 299(24.8%) · 등급 243/52/4 | 변화 없음 |
| 장비 | 1권 · 217쪽(10.6%) · 출현 271(22.5%) · 등급 121/122/28 | **2권 · 414쪽(20.1%) · 출현 772(64.0%) · 등급 276/385/111** |
| 재료(·인프라) | 1권 · 197쪽(9.6%) · 출현 501(41.5%) · 등급 155/263/83 | **0권 · 0쪽(0.0%) · 출현 0 · 등급 0/0/0** |
| 합계 | 9권 · 2,055쪽 · 1,207건 · 633/459/115 | 불변 |

`largest_area`(쪽수 최대)는 제조 그대로. 교과서 등급 3 115건 중 111건(96.5%)이 장비 영역 2권에 몰리게 된다(TODOS "C 교과서 보강" 메모의 96.5% 와 같은 값).

### 1.4 실측 — HWPX 에서 손대야 하는 위치 (`hwpx_results_refresh.py`, 1단계 제3장 1절 = 교과서 절)

| 위치 | 현행 산출(재료 대응) | 변경 후 |
|---|---|---|
| 1절 2) 리드 문단(`:753`) "…반도체 개발, 반도체 제조, 반도체 장비, 반도체 재료·인프라 분야로 재분류하였다" | 영역명에 "재료·인프라" | 영역명 표기 결정 D2 에 따름 |
| (3) 장비 문단(`area_sentence("장비")`, `:763`) "반도체 장비 분야는 1권, 총 217쪽 … 장비 유지보수는 …" | 1권 서술 | 2권(414쪽, 20.1%) + 두 교재 이름 + 인프라 일반의 전기·공조·유틸리티·설비 운용 서술 흡수 — 권수 분기 |
| (4) 재료·인프라 문단(`:766-769`) "반도체 재료·인프라 분야는 1권, 총 197쪽 … 화학물질, 특수 가스, 전력, 초순수 …" + 대형 사고·SDS/GHS 문단 | 1권 서술 | **0권 분기**: "해당 교과서 없음" 한 문장으로 줄이거나(D3-W1) 절 자체를 재구성(D3-W2). 사고·SDS 문단은 교재가 없는 영역에 걸 수 없으므로 자리 이동(장비 문단 뒤) 또는 삭제 — D3 |
| 표 8(교과서 영역별, `area_table_rows(facts.school)`) | 재료 행 1·197… | 재료 행 0·0·0·0·0·0.0%, 장비 행 2·772·276·385·111·64.0% |
| `Facts.value_index()` 영역 키(`:149-156`) | 재료 197쪽 등 | 새 값으로 감사 통과, 옛 값(197쪽·9.6%·501건 등)은 감사에서 탈락해야 정상 |
| 대조 JSON `hwpx_results_refresh_20260917.json` | `output_sha256 aa0f3453…`, 문단 45 | 문단 수는 같고 숫자·sha 변경 — 파일 이름은 정본 실행일(20260917) 그대로(정본 재실행 없음) |
| `review.html` 표 8 | 재료 1권 행 | 0 행 |
| NCS 절·2단계·3단계 | — | 불변(NCS 대응은 1:1, `NCS_GROUP_TO_AREA` 값 동일) — 재실행 결정론으로 확인 |

그림 2~4 는 등급·NCS 영역 그림이라 영향 없음(`area_bars_svg` 는 NCS 만). `recount_grades.py` 의 `AREAS` 는 NCS 원자료 그룹 4개라 무관.

### 1.5 관련 문서·자산

- 09-19 1단계 문서(미추적): `docs/01-plan/features/semantic-report-area-symmetry.plan.md`, `docs/02-design/…design.md`, `docs/03-analysis/semantic-report-area-symmetry.analysis.md`, `docs/04-report/features/…report.md` — 처분은 D5.
- `docs/archive/2026-09/hwpx-ncs-section-refresh/`(1단계 문안 분기 규약 — "data-dependent claims are branched, never assumed"), `hwpx-methods-bridge-refresh/`(장부·`check_untouched`·백업 규약), `ncs-book-concentration/`(3단계·`--force` 재실행 결정론).
- CLAUDE.md 그룹 4 `hwpx_results_refresh.py` 문단("the textbook→area map (`TEXTBOOK_AREA`, the report's 연구상 분류)"), `hwpx_methods_bridge.py` 문단(`NCS_GROUP_TO_AREA` "한 정의") — 공용 모듈로 옮긴 사실 미반영.
- TODOS "기초보고서 보강 후속" 3(C 교과서 보강 96.5%)·5(한글 확인).

---

## 2. 범위

### 2.1 포함

- [ ] **문안 분기(D2·D3)**: 1절 2) 리드 문단의 영역명, (3) 장비 문단의 권수·교재 나열·내용 서술, (4) 재료 문단의 0권 분기와 사고·SDS 문단의 처리 — 모두 데이터(권수)로 분기하고 양쪽을 테스트(현행 재료 1권 대응은 fixture 로 계속 검사).
- [ ] **감사·불변**: 새 문단·표 8 의 숫자가 전부 `value_index` 키(영역 쪽수·비율·권수·출현·등급)로 해소, 옛 값(197쪽·9.6%·501건·1권 재료)은 `STALE_PATTERNS` 에 넣지 않되(값이 아니라 대응이 바뀐 것) 새 대응에서는 자연히 미일치가 되어야 함을 테스트로 확인.
- [ ] **재생성**: 원본 `data/반도체 기초보고서_20260911.hwpx` → 1·2·3단계 `--force` → `…_20260917_정본.hwpx`(이름은 정본 실행일 유지), 대조 JSON·`review.html` 갱신, 재실행 바이트 동일 확인. 기존 디스크 파일(Polaris 재저장본 `9ef93187…`)은 스크립트가 `<이름>.9ef93187cd38f10e.bak` 로 보존한다(D4: 본문 대조는 하지 않음).
- [ ] **테스트 정리**: `CommittedDiffTests` 의 역사 mock 제거(대조 JSON 이 새 대응이므로 그대로 감사), `AreaCrosswalkTests`·`SharedAreaCrosswalkTests`·09-19 테스트 6건 유지, `AuditTests` 의 `{장비 2, 재료 0}` 단언 유지, 분기 양쪽 테스트 추가, 1단계 fixture(`build_fixture_hwpx` 교과서 절)에 2권/0권 영역이 실제로 지나가는지 확인.
- [ ] **문서**: CLAUDE.md(그룹 4 두 문단 → `semantic_report_areas.py` 로, 연구상 분류 문장·Testing/Test Coverage 항목·Third stage 문단의 영향 없음 명시), README(재생성 절에 `--skip-xlsx-write` 와 4영역 md 절 한 문장), `docs/03-analysis/data/README.md`(대조 JSON 행: 교과서 영역 재대응·sha), TODOS(3·5 갱신, 09-19 항목 기록), `docs/textbook.html` 은 교재별이라 무변경 확인.
- [ ] **09-19 산출물 승계**: 공용 모듈·Markdown 절·`--skip-xlsx-write`·테스트는 그대로; 1단계 PDCA 문서 4건의 처분(D5).
- [ ] **실문서 확인**: 재생성 HWPX 를 Polaris 로 1절 2) 문단·표 8 확인(Drive 자동 업로드 주의는 TODOS 5 그대로), 한글은 `[→E2E]`.

### 2.2 제외

- 정본 재실행(`semantic_keyword_recount.py`)·`semantic_summary.json`·data.js·분석 페이지·`EXPECTED`·해시·XLSX 변경 — 영역 접기는 저장되지 않으므로 불필요(§1.2).
- 나머지 교과서 8권의 대응 변경, 4영역을 공식 분류로 승격하는 서술(09-19 계획 §2.2 와 동일).
- 대시보드에 4영역 표를 추가하는 것(교과서 대시보드는 교재별 `groups[]` — D6 of ncs-book-concentration 그대로).
- NCS 절·제2장 5절·제3장 2절 4)·5) 문안 — 대응이 1:1 이라 바뀔 값이 없고, 재실행 결정론으로 불변을 확인만 한다.
- 09-19 Markdown 4영역 표의 문구 재검토(이미 "연구상 대응" 주석 포함, 승계).

---

## 3. 요구사항

### 3.1 기능 요구사항

| ID | 요구사항 | 우선순위 | 상태 |
|---|---|---|---|
| FR-01 | 교과서 영역 문단(개발·제조·장비·재료)이 권수로 분기한다: 0권 영역은 "해당 교과서 없음" 계열 한 문장(D3), 2권 이상 영역은 교재 이름을 나열하고 각 교재의 내용 서술을 합친다; 1권 영역은 현행 문장 유지. 분기는 `conditions` 에 기록된다 | High | Pending |
| FR-02 | 1절 2) 리드 문단의 영역명이 대응표(`AREA_DISPLAY`/D2)에서 나오고, "재료·인프라" 같은 손 문구는 대응표 밖에 남지 않는다 | High | Pending |
| FR-03 | 표 8 은 `area_table_rows` 그대로(0 행 허용) — 재료 행 `0 · 0 · 0 · 0 · 0 · 0.0%`, 장비 행 `2 · 772 · 276 · 385 · 111 · 64.0%`, 합계 불변 | High | Pending |
| FR-04 | 사고·SDS/GHS 문단(현행 (4) 아래)은 교재가 없는 영역에 걸리지 않는다 — D3 에 따라 장비 문단 뒤로 옮기거나 삭제하며, 어느 쪽이든 `find_paragraph` locator 가 원본 첫머리로 여전히 찾는다 | High | Pending |
| FR-05 | 숫자 감사: 재생성 문단·표 8·`value_index` 가 새 대응 값으로 미일치 0; 옛 대응 값(197쪽·9.6%·501)을 넣은 fixture 는 미일치가 나야 한다(감사가 대응 변경을 실제로 본다는 증거) | High | Pending |
| FR-06 | `hwpx_results_refresh.py --force` 로 원본에서 재생성: 문단 45(→ 설계 1.1 로 46: 본문 소제목 "(4)" locator 추가)·표 14·그림 3, NCS·2·3단계 절 ZIP 바이트/XML 동일(교과서 절만 변경), 두 번 실행 시 바이트 동일 | High | Pending |
| FR-07 | 대조 JSON `hwpx_results_refresh_20260917.json` 갱신(교과서 절 문단 `new_numbers`·`conditions`, 표 8 `changed_cells`, `output_sha256`), `review.html` 표 8 갱신; `CommittedDiffTests` 는 mock 없이 현행 대응으로 감사 | High | Pending |
| FR-08 | 디스크 정본 HWPX(Polaris 재저장본 `9ef93187…`)는 `--force` 의 자동 백업 `.bak` 로만 보존한다 — 본문 대조 없음(D4 무시) | Medium | Pending |
| FR-09 | 분기 양쪽 테스트: 0권/1권/2권 영역 문장, 리드 영역명, 사고·SDS 문단 위치; fixture HWPX 로 E2E; `AuditTests` 교과서 `{개발 3, 제조 4, 장비 2, 재료 0}`·쪽수 합 2,055 | High | Pending |
| FR-10 | 문서·TODOS·메모리 동기화: CLAUDE.md(대응표 위치·연구상 분류 문장·mock 제거), README, data README, TODOS 3·5, `docs/textbook.html` 무변경 확인 | High | Pending |
| FR-11 | 09-19 1단계 PDCA 문서 처분(D5)과 이 기능 문서의 보관이 같은 아카이브 항목에서 서로를 가리킨다 | Medium | Pending |

### 3.2 비기능 요구사항

| 항목 | 기준 | 확인 |
|---|---|---|
| 정본 수치 불변 | `semantic_summary.json`·data.js·XLSX·해시 4종·`EXPECTED` 무변경(git diff 0) | `S2`·`S3`·`test_committed_summary_json_matches_expected` |
| 재현성 | 같은 입력 → 같은 HWPX ZIP 항목·대조 JSON·review.html(재실행 "새 출력과 같음") | 실측 |
| 공개 경계 | 대조 JSON·review.html 에 본문 문장·절대 경로 없음 | `CommittedDiffTests`·`S3i` |
| 국소성 | 교과서 절(제3장 1절) 밖의 ZIP 항목·문단은 바이트 동일 | `check_untouched` + 절별 XML 대조 |

---

## 4. 성공 기준

- [ ] 재생성 HWPX 1절 2): 장비 "2권, 총 414쪽 … 20.1%" + 두 교재 이름, 재료 영역은 D3 의 0권 문장, 리드 영역명은 D2, 표 8 재료 0 행·장비 2 행, 감사 미일치 0, 재실행 바이트 동일.
- [ ] 대조 JSON·review.html 갱신, `CommittedDiffTests` mock 없이 통과, unittest·하니스 전부 통과(하니스 84 는 대시보드 무변경이라 그대로).
- [ ] `git diff` 에 `semantic_summary.json`·data.js·XLSX 없음; 해시 4종·`books_digest` 불변.
- [ ] CLAUDE.md·README·data README·TODOS 갱신, 09-19 문서 처분 완료, Polaris 확인 기록, 한글 `[→E2E]` 갱신.

---

## 5. 위험과 대응

| 위험 | 영향 | 가능성 | 대응 |
|---|---|---|---|
| 0권 영역 문장이 "0권, 총 0쪽으로 0.0%" 로 나감 | 보고서 품질 | 높음(현행 템플릿 그대로면 확정) | FR-01 권수 분기 + 양쪽 테스트 |
| 사고·SDS 문단이 근거 교재 없는 영역에 남음 | 논리 오류 | 높음 | FR-04, D3 |
| Polaris 재저장본에 사람이 고친 문장이 있는데 재생성이 덮음 | 작업 손실 | 중 | `.bak` 자동 보존 + 재생성 전 본문 대조(FR-08, D4) |
| 옛 값(197쪽·9.6%)이 어딘가 손 문구로 남아 감사를 통과 | 낡은 수치 | 중 | 감사는 값 소속만 보므로, 옛 값 fixture 가 미일치를 내는 역방향 테스트(FR-05)로 확인 |
| 대조 JSON 이름이 20260917 인데 내용이 바뀌어 계보가 헷갈림 | 문서 계보 | 중 | data README 행에 "2026-09-21 교과서 대응 재생성(정본 실행일은 그대로)" 명시, `source.summary_run` 은 여전히 09-17 정본 |
| `find_paragraph` locator 가 (4) 문단 첫머리("반도체 재료·인프라 분야는")를 못 찾음 | 실행 정지 | 낮음 | locator 는 원본(2026-09-11) 첫머리 기준이라 불변; 재작성 문장만 바뀜 |
| 09-19 Codex 문서의 검증 수치(HWPX sha `9ef93187`·unittest 226)가 스크립트 출력 기준이 아님 | 계보 오해 | 확정 | §1.2 에 실측으로 정정, D5 처분 시 주석 |

---

## 6. 결정 기록 (연구책임자, 2026-09-21 — D1~D5 확정)

| # | 결정 | 선택지 | 상태 |
|---|---|---|---|
| D1 | 『반도체 인프라 일반』 대응 | **(b) 장비** — 09-19 결정을 2026-09-21 재확인(A.b). (a) 재료 유지는 기각 | **확정** |
| D2 | 리드 문단·표의 교과서 재료 영역 이름 | (a) "반도체 재료·인프라" 유지(0권이라도 이름은 NCS 재료와 대칭이 아님) / **(b) "반도체 재료"로 통일**(공용 `AREA_DISPLAY` 그대로, NCS 와 같은 4영역명) | **확정 (b)** "반도체재료"로 통일 |
| D3 | 0권 영역(재료)의 문단과 사고·SDS 문단 | **(W1)** (4) 를 "반도체 재료 분야에 해당하는 교과서는 없다" 한 문장으로 두고 사고·SDS 문단은 장비 문단 뒤로 이동(인프라 일반이 그 근거이므로) / (W2) (4) 삭제하고 4영역 열거를 3영역으로 / (W3) (4)+사고·SDS 문단 모두 삭제 | **확정 W1** — (4) 유지·한 문장, 사고·SDS 문단은 장비 문단 뒤로 |
| D4 | 디스크 정본(Polaris 재저장본 `9ef93187…`) | (a) 대조만 하고 `.bak` 보존 후 재생성 / (b) 재저장본에 사람 편집이 있으면 먼저 그 편집을 스크립트 템플릿에 반영 | **확정 — 무시**: 재저장본 본문 대조를 하지 않는다. 스크립트의 `--force` 자동 백업(`.9ef93187cd38f10e.bak`)만 남기고 재생성 |
| D5 | 09-19 1단계 PDCA 문서 4건(미추적) | (a) 이 기능과 함께 커밋·`docs/archive/2026-09/semantic-report-area-symmetry/` 로 보관(계보) / (b) 이 기능 문서에 흡수하고 삭제 | **확정 (a)** — 함께 커밋·보관(sha `9ef93187` 은 Polaris 재저장본 기준이라는 주석 추가) |

---

## 7. 입력 자료

| 자료 | 위치 | 용도 |
|---|---|---|
| 원본 HWPX | `data/반도체 기초보고서_20260911.hwpx`(비추적) | 1·2·3단계 재생성 입력 |
| 정본 요약 | `docs/03-analysis/data/semantic_summary.json`(2026-09-17, 불변) | 교재별 `groups[]` → 영역 접기 |
| 공용 대응표 | `semantic_report_areas.py`(09-19, 미커밋) | 유일한 분류 출처 |
| 09-19 산출물 | `data/semantic_keyword_recount_20260917_report.md`(비추적, 4영역 절 있음), 1단계 PDCA 문서 4건 | 대칭 문구·근거표 승계, 계보 |
| 디스크 정본 | `data/반도체 기초보고서_20260917_정본.hwpx`(sha `9ef93187…`, Polaris 재저장) | D4 대조 대상, `.bak` 보존 |
| 추적 대조 JSON | `docs/03-analysis/data/hwpx_results_refresh_20260917.json`(`aa0f3453…`) | 갱신 대상(계보는 git 이력) |

---

## 버전 이력

| 버전 | 날짜 | 내용 | 작성 |
|---|---|---|---|
| 1.0 | 2026-09-21 | 초안 — 09-19 1단계(`semantic-report-area-symmetry`)의 범위 밖이던 HWPX·대조 JSON·문서 반영 계획, 실측(재저장본·mock·영역 수치) 포함, 결정 D2~D5 요청 | Claude (Opus 5) / 결정: 연구책임자 |
| 1.1 | 2026-09-21 | 결정 확정 — D2 (b) 반도체재료 · D3 W1 · D4 무시(대조 없이 `.bak` 만) · D5 (a) | 연구책임자 |
