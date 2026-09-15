# 의미 출현을 실제 PDF 쪽에 얹기 — 페이지 단위 이질성 해소 계획

> **Summary**: 정본 의미 재검산(사전 v2, NCS 11,517건)의 "페이지"는 마크다운 쪽 표식(`<!-- page: N -->`)이다. 86권 중 23권(+ 2026-09-13 추가 2권)만 실제 쪽 표식이고 63권은 목차에서 유도한 블록 표식이라, 한 "페이지" 가 실제 1쪽이기도 41쪽이기도 하다(출현의 44%가 4쪽 이상 블록에 놓임). 등급도 두 갈래 — 6,292건은 2026-04 워크북의 라벨(블록) 등급을 상속하고 5,225건은 현재 블록 텍스트로 새로 판정한다(외부감사 M2 "등급 모집단이 섞여 있다"). `resegment.py` 가 이미 만든 줄→실제 쪽 대응(`data/markdown/ncs_paged/*.pages.json`, 84권)을 재사용해 **모든 NCS 출현을 실제 PDF 쪽에 놓고, 등급은 실제 쪽 본문에 하나의 규칙(regrade 기준선 — 이전 기준 `reseg_summary.json` 과 같은 규칙)** 으로 판정한다. 실측: 실제 쪽 판정은 이전 기준의 쪽 등급과 공유 쪽 2,035개에서 100% 일치하고, 출현 기준 등급3 비율은 21.9% → 21.7% 로 거의 같으나 등급1/2 구성이 38.0/40.1 → 32.9/45.4% 로 바뀌며 출현 4,016건(34.9%)의 등급이 이동한다.

> **Project**: SearchInMD
> **Feature**: occurrence-real-pages
> **Author**: Claude (Opus 5) — 결정: 연구책임자
> **Date**: 2026-09-15
> **Status**: Approved (연구책임자 2026-09-15 — D1~D6 전부 A; 정본 워크북 복귀 확인 sha256 `80fdd14b…`)
> **Level**: Starter
> **선행**: `TODOS.md` "의미 재검산 감사 시정 후속" 2번(감사 M2), 3번(비단조 마커 1권 — 이 계획이 대체), 1(d)(분야별 쪽수 기준 — 이 계획 D4); `docs/archive/2026-09/resegment/`·`resegment-publish/`(줄→쪽 정렬, 하이브리드 배정), `docs/archive/2026-09/semantic-expression-review/`(사전 v2)

---

## Executive Summary

| 관점 | 내용 |
|---|---|
| **Problem** | 발표 중인 출현 기준 등급 분포(NCS 11,517건, 등급3 21.9%)는 두 종류의 "페이지"(실제 쪽 23권 + 대응 없는 2권 / 목차 블록 61권 — 블록 하나가 실제 1~41쪽)와 두 종류의 등급(2026-04 라벨 등급 상속 6,292건 / 현재 블록 텍스트 판정 5,225건)이 섞인 값이다. 같은 규칙으로 실제 쪽에 다시 판정하면 출현 4,016건(34.9%)의 등급이 바뀐다 — 외부감사 M2. |
| **Solution** | `resegment.py` 의 줄→실제 쪽 대응(84권, 정렬 자기 검증 ±1쪽 94.9%)을 `semantic_keyword_recount.py` 에 입력(`--page-maps`)으로 넣어 NCS 출현마다 실제 쪽을 붙이고, 등급은 실제 쪽 본문에 `regrade.grade_page` 기준선 하나로 판정한다(이전 기준 `ncs_pages_reseg.csv` 와 공유 쪽 2,035개에서 100% 일치 — 같은 규칙임을 테스트가 고정). 표식이 실제 쪽인 2권은 표식을 그대로 쓴다. 정본 재실행 → `EXPECTED` 재고정 → 대시보드·README·CLAUDE.md·기초보고서(HWPX) 재생성. |
| **Function/UX Effect** | 독자는 "페이지" 가 어느 교재에서나 PDF 한 쪽임을 전제로 등급 분포·분야별 쪽수(마커 최댓값 합 8,914 → PDF 쪽수 9,100)를 읽을 수 있고, 출현 기준 KPI 와 이전 기준(페이지 단위 2,189쪽·등급3 145쪽)이 같은 쪽 모집단 위에 놓여 브리지 표가 "같은 쪽, 다른 분모" 로 단순해진다. 검출 쪽은 1,785 → 2,492쪽. |
| **Core Value** | 등급 모집단의 동질성 — 감사 M2 종결. 비단조 마커 1권(TODOS 3)과 분야별 쪽수 기준(TODOS 1(d))도 같은 변경으로 닫힌다. 발표값의 등급3 비율은 거의 그대로(21.9 → 21.7%)지만, 그 값이 이제 "실제 쪽에 하나의 규칙" 이라는 말로 설명된다. |

---

## 1. 개요

### 1.1 목적

NCS 86권의 모든 의미 출현(사전 v2 포함 레코드)에 **실제 PDF 쪽** 을 붙이고, 그 쪽의 본문에 **하나의 판정 규칙** 을 적용해 출현 기준 등급 분포를 다시 낸다. 교과서 9권은 이미 실제 쪽 표식(2,055쪽 = `recount_grades.py` 쪽수)이라 바뀌지 않는다.

### 1.2 배경

- **외부감사(2026-09-13) M2**: 마커 파일 84권 중 실제 쪽 표식은 일부이고 나머지는 목차 블록 단위라 등급 모집단이 섞여 있다. `feat/semantic-recount-remediation`(PR #15) 은 이를 이월했다(`TODOS.md` 2번).
- **현재 정본의 페이지·등급 구조** (`semantic_keyword_recount.py`): `split_pages` 가 `<!-- page: N -->` 표식으로 블록을 나누고, 출현의 `page` = 블록 표식. 등급(`assign_match_grades`)은 (교재, 표식 쪽) 이 2026-04 워크북에 있으면 그 라벨의 등급을 상속(`existing`, 6,292건)하고, 없으면 블록 텍스트에 `regrade.grade_page` 기준선을 적용(`new`, 5,225건)한다. 워크북 라벨 자체가 목차 블록이므로 상속 등급도 블록 등급이다.
- **이미 있는 해법**: `resegment.py`(2026-09-06, PR #14) 가 84권의 마크다운 줄을 PDF 쪽 텍스트에 정렬해 줄→쪽 대응을 `data/markdown/ncs_paged/<LM코드>.pages.json`(`line_pages`, gitignore) 에 남겼고, 그 쪽에 같은 기준선으로 낸 쪽 등급이 이전 기준 `docs/03-analysis/data/ncs_pages_reseg.csv`(2,189쪽) 다. 표식이 실제 쪽인 23권은 표식을 쓰고(`markers`), 표식 결손 구간은 하이브리드 배정(`hybrid_lines` 1,575). 정렬 자기 검증(23권): DP 후보 줄 83.6% 정확·94.9% ±1쪽, 결손 구간 제외 88.6%·98.5%.

### 1.3 실측 (2026-09-15, 정본 코퍼스 `data_source/markdown/ncs` 86권 · 사전 v2 · 스크래치 스크립트)

| 항목 | 값 |
|---|---|
| 줄→쪽 대응이 있는 교재 | 84권(`ncs_paged/*.pages.json`; `line_pages` 길이가 정본 마크다운의 줄 수와 84권 전부 일치). 대응 없는 2권 = 2026-09-13 추가 교재 `LM1903060408`(117쪽)·`LM1903060424`(118쪽) — 표식이 실제 쪽(25~28줄/쪽) |
| 표식 종류 | 블록 수 / PDF 쪽수 ≥ 0.8 인 "실제 쪽" 교재 23권(평균 0.91, 27.7줄/블록) vs "목차 블록" 교재 63권(평균 0.40, 56.8줄/블록) — `reseg_summary.json` 의 `markers` 23권 / `alignment` 61권과 같은 그림 (영향표의 교재 분류도 `per_book.method` 를 따라 23 / 61 / 대응 없음 2 — 출고 전 적대적 리뷰에서 비율 규칙(대응의 실제 쪽 수 분모, 25 / 59)을 대체 규칙으로 내렸다) |
| 출현 분포 | 11,517건 중 목차 블록 교재 7,931건(68.9%), 실제 쪽 교재 3,586건 |
| 출현이 놓인 블록의 실제 쪽 폭 | 1쪽 3,718건(32.3%) · 2~3쪽 2,335(20.3%) · 4~9쪽 3,022(26.2%) · **10쪽 이상 2,027(17.6%)**; 최대 41쪽(`LM1903060305`), 40쪽(`LM1903060323`, 출현 415건) |
| 검출 쪽 수 | (교재, 표식 쪽) 1,785 → (교재, 실제 쪽) 2,492 (84권 2,415 + 새 2권 77) |
| 실제 쪽 등급(기준선) vs 이전 기준 | 공유 쪽 2,035개에서 **100% 일치**(`text` 2,027/2,027 · `text-fallback` 8/8) — 같은 규칙. 의미 표현으로만 닿는 새 쪽 380개는 같은 규칙으로 새로 판정 |
| 출현 기준 등급 분포 | 현재 정본 38.0 / 40.1 / **21.9%** → 실제 쪽 32.9 / 45.4 / **21.7%** (등급3 2,525 → 2,502) |
| 출현별 등급 이동 | 4,016건(34.9%): 1→2 1,296 · 1→3 398 · 2→1 727 · 2→3 587 · 3→1 377 · 3→2 631. 현재 `new`(블록 텍스트 판정) 5,225건은 79.9% 불변, `existing`(2026-04 라벨 상속) 6,292건은 **52.8%** 만 불변 — 이질성의 크기 |
| 분야별 쪽수 | 현재 표식 최댓값 합 8,914(84권 8,675 + 새 2권 239) → PDF 쪽수 8,861 + 239(새 2권 표식 최댓값 120·119) = **9,100** (`TODOS.md` 1(d)) |
| 비단조 마커 1권 | `LM1903060113` 은 목차 블록 교재(정렬 대응 있음) — 대응을 쓰면 표식 순서와 무관하게 실제 쪽이 붙는다(`TODOS.md` 3번 종결) |
| PDF 원본 검증 (2026-09-15 추가) | 연구책임자가 원본 PDF 86권을 `data/markdown/ncs/pdf/<분야>/`(비추적, 757 MB)에 모아 두어 PyMuPDF 로 쪽수를 세었다: 84권 전부 `reseg_summary.json per_book.pdf_pages` 와 일치, 새 2권 120·119쪽 = 표식 최댓값, 86권 합 **9,100쪽** = 이 기능의 분야별 쪽수 합 — D2·D4 의 전제가 원본으로 확인됨. `NCS_PDF_ROOT=data/markdown/ncs/pdf` 로 `resegment.py` 재실행(새 2권 대응, ④ 마커 보정)이 로컬에서 가능해졌다 |

### 1.4 관련 문서·자산

- 코드: `semantic_keyword_recount.py`(`split_pages`, `assign_match_grades`, `run_manifest`, `EXPECTED`, `summary_payload` 의 `groups[].pages`), `resegment.py`(`page_texts`, `hybrid_pages`, `write_atomic` 의 `pages.json`), `regrade.grade_page`, `page_utils.PAGE_MARKER_RE`
- 데이터: `data/markdown/ncs_paged/*.pages.json`(84권, gitignore), `docs/03-analysis/data/{reseg_summary.json, ncs_pages_reseg.csv}`(이전 기준), `semantic_summary.json`(정본 v2)
- 문서: `CLAUDE.md` "4. Semantic recount"·"Safety Grading Scheme" 예외 문단, `docs/04-report/features/semantic-occurrence-grades.report.md` 브리지 표, `docs/archive/2026-09/resegment/resegment.design.md`
- 하니스: `test_semantic_keyword_recount.py`, `outputs/test-dashboard-data.js` S2~S5·S7·S8, `outputs/test-recount-grades.py` R16

---

## 2. 범위

### 2.1 포함

1. `semantic_keyword_recount.py` 에 줄→쪽 대응 입력(`--page-maps DIR`, 기본 `data/markdown/ncs_paged`) — NCS 문서마다 `<LM코드>.pages.json` 이 있으면 출현의 `page` 를 `line_pages[줄-1]` 로, 등급 판정 단위를 "같은 실제 쪽에 대응된 줄들의 본문" 으로 바꾼다. 대응이 없는 문서는 표식이 실제 쪽일 때만 허용(D2), 아니면 오류.
2. 등급 규칙 통일(D1): NCS 는 실제 쪽 본문에 `regrade.grade_page` 기준선(`word_boundary=False, normalize=False`) — 2026-04 워크북 라벨 등급 상속(`existing`)을 NCS 에서는 쓰지 않는다(라벨은 블록이라 실제 쪽에 대응되지 않는다). 교과서는 현행 유지(실제 쪽 표식 + 워크북 상속).
3. 이전 기준과의 결속: 실행이 `ncs_pages_reseg.csv` 를 읽어 공유 쪽의 등급 일치율을 manifest(`meta.run.reseg_agreement`)에 기록하고, 100% 미만이면 `EXPECTED` 불일치로 멈춘다(같은 규칙·같은 대응이라는 것이 이 기능의 전제).
4. manifest 확장: `page_maps`(파일 수·sha256 합), `page_basis: "real"`, `grade_sources` 에 `real-page`(NCS) 추가, `groups[].pages` = PDF 쪽수(`reseg_summary.json per_book.pdf_pages`) + 대응 없는 교재는 표식 최댓값(D4).
5. 정본 재실행(사전 v2 그대로) → `EXPECTED` 재고정 → 대시보드(`semantic_recount_data.js`·분리 HTML 3건)·`semantic_summary.json`·xlsx·report 갱신. 영향표 `docs/03-analysis/data/occurrence_real_pages_impact.json`(블록 기준 v2 vs 실제 쪽 기준: 총계·등급·키워드·분야·이동 행렬 — 위 §1.3 을 산출물로 고정).
6. 발표면: `index.html` 브리지 절 문구("같은 쪽 모집단, 분모만 다름"), README·CLAUDE.md 예외 문단 수치, `docs/04-report/features/semantic-occurrence-grades.report.md` 브리지 표, 기초보고서 HWPX 재생성(`hwpx_results_refresh.py` — 원본 `…_20260911.hwpx` 에서, 산출물 이름 날짜 갱신; 2절 분야별 쪽수 문구 "쪽 표식 최댓값 합" → "PDF 쪽수").
7. 테스트: `test_semantic_keyword_recount.py` 에 대응 적용·대응 없는 문서 규칙·실제 쪽 판정·reseg 결속·manifest 필드·`EXPECTED` 가드; `test-dashboard-data.js` 에 `page_basis`·쪽수 합·브리지 문구; `test_hwpx_results_refresh.py` 는 재실행 산출물로 통과.

### 2.2 제외

- 줄→쪽 대응 자체의 재생성(`resegment.py` 재실행, `NCS_PDF_ROOT` 필요) — 기존 84권 대응을 그대로 쓴다. 대응의 정확도 개선(마커 ±1 보정 `--marker-correct`, `TODOS.md` ④)은 별개 결정.
- 교과서 9권(실제 쪽 표식, 변경 없음).
- 사전 자체(v2 유지) · 등급 규칙 변경(regrade 변형 D1~D5·V 는 연구 트랙, `TODOS.md` P2).
- 2026-04 워크북 라벨 등급의 재해석 — NCS 상속을 끊는 것이 이 계획이고, 라벨 등급은 `summary.json`·`ncs_pages.csv` 에 계보로만 남는다.
- 사고사례 판정(`accident_case_pages.json` 은 이미 실제 쪽 기준) — 재판정 없음.

---

## 3. 요구사항

### 3.1 기능 요구사항

| ID | 요구사항 | 근거 | 우선순위 | 상태 |
|---|---|---|---|---|
| FR-01 | `--page-maps DIR` 로 `<LM코드>.pages.json` 을 읽어 NCS 출현의 `page` 를 `line_pages[줄-1]` 로 놓는다; `line_pages` 길이가 문서 줄 수와 다르면 오류(대응이 다른 판의 마크다운) | §1.3 84권 일치 | High | 대기 |
| FR-02 | 대응 없는 NCS 문서는 표식이 실제 쪽일 때만 허용(D2: 표식 수 ≥ PDF 쪽수 × 0.8 또는 명시 목록 `REAL_PAGE_MARKER_BOOKS`) — 아니면 실행 거부 | 새 2권 | High | 구현 — 명시 목록 + 표식 1..N 연속 검사만(0.8 자동 임계는 채택하지 않음, 설계 §6 결정 3; 0.8 은 영향표의 교재 분류에만) |
| FR-03 | 실제 쪽의 본문 = 그 쪽에 대응된 줄 전부(표식 줄 제외); 등급 = `regrade.grade_page` 기준선; `grade_source = "real-page"`; NCS 에서 `existing` 상속을 쓰지 않는다 | D1 | High | 대기 |
| FR-04 | `ncs_pages_reseg.csv` 와 공유 쪽의 등급 일치율을 계산해 manifest 에 기록, 100% 미만이면 `EXPECTED` 불일치 | §1.3 100% | High | 대기 |
| FR-05 | `groups[].pages` = PDF 쪽수(`reseg_summary.json per_book.pdf_pages`), 대응 없는 교재는 표식 최댓값; manifest `page_basis` | D4 | High | 대기 |
| FR-06 | `EXPECTED` 재고정: documents 86/9, totals, grades, `grade_sources`(`real-page`·`new`·`existing`), `reseg_agreement`, 해시 4종 + `page_maps_sha256` | 가드 | High | 대기 |
| FR-07 | 영향표 `occurrence_real_pages_impact.json`: 블록 기준(현 정본) vs 실제 쪽 기준 — 총계·등급·키워드별·분야별·이동 행렬·교재 종류별(실제 쪽/목차 블록) | §1.3 | Medium | 대기 |
| FR-08 | 대시보드 브리지 절·`previous_basis` 문구: 같은 쪽 모집단(2,189쪽은 워크북 검출 쪽, 2,492쪽은 의미 출현 쪽) | D3 | Medium | 대기 |
| FR-09 | 기초보고서 HWPX 재생성(원본에서), 2절 쪽수 문구·분야 쪽수 갱신, 대조 JSON·검토 HTML 갱신 | D6 | Medium | 대기 |
| FR-10 | 문서: CLAUDE.md 그룹 4·예외 문단, README 재생성 절(`--page-maps`), data README 계보, `TODOS.md` 2·3·1(d) 종결 | — | Medium | 대기 |

### 3.2 비기능 요구사항

- 대응 파일은 gitignore(줄 단위 대응은 본문이 아니지만 `resegment.py` 산출물 규약을 따른다); manifest 에는 파일 수와 sha256 합만.
- 재실행 결정론: 같은 대응·같은 코퍼스 → 같은 해시(`test_two_runs_on_same_fixture_are_identical` 확장).
- 실행 시간: 대응 적용·쪽 본문 판정을 더해도 2배 이내 — 실측 34.7 s(대응) vs 34.8 s(대응 없음, 같은 입력·같은 기기; 갭 분석 Act-1 G-11).
- 절대 경로·본문은 추적 산출물에 넣지 않는다(`public_path`).

---

## 4. 성공 기준

- [ ] 정본 재실행이 가드 통과: NCS 86권, 출현 11,517건(사전 v2 그대로), `grade_sources.NCS = {real-page: 11,517, existing: 0, new: 0}` 또는 D2 의 대응 없는 2권 몫만 `new`, 교과서 불변(1,207).
- [ ] 공유 쪽 등급 일치율 100%(`meta.run.reseg_agreement`), 검출 쪽 2,492(±정렬 오차 범위는 영향표에 기록).
- [ ] `groups[].pages` 합 = 9,100(PDF 8,861 + 새 2권 표식 최댓값 239); 대시보드·README·CLAUDE.md·HWPX 가 같은 값.
- [ ] 영향표에 §1.3 의 이동 행렬(4,016건)이 산출물로 고정되고, 보고서 문구가 "등급3 비율은 21.9 → 21.7% 로 거의 같으나 구성이 바뀐다" 를 개선으로 서술하지 않는다.
- [ ] 하니스 전부 통과(unittest·S1~S9·R·SRI·core), `EXPECTED` 를 손으로 바꾼 값은 CI 가 잡는다(`test_committed_summary_json_matches_expected`).
- [ ] `TODOS.md` 2·3·1(d) 닫힘, ④(마커 보정)는 그대로 결정 대기.

---

## 5. 위험과 대응

| 위험 | 영향 | 대응 |
|---|---|---|
| 정렬 오차(±1쪽 5%, DP 후보 줄 기준)로 출현이 이웃 쪽에 놓인다 | 출현별 등급이 이웃 쪽 등급을 받음 | 이전 기준과 같은 오차(같은 대응) — 영향표에 정렬 자기 검증 수치를 병기; 마커 보정(④)은 별도 결정 |
| **정본 재실행 입력 부재**: `data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx`(sha256 `80fdd14b…`) 가 `data/` 에 없다 | Do 단계 착수 불가(정본 실행·`EXPECTED` 재고정·F11 도 같은 입력) | 연구책임자가 사본(iCloud/Google Drive)을 `data/` 로 복귀 → sha256 이 manifest 값과 같은지 먼저 확인 |
| 대응이 옛 마크다운 판에 묶여 있다(교재 마크다운이 바뀌면 줄 수가 어긋남) | 잘못된 쪽 배정 | FR-01 줄 수 검사 + manifest `md_corpus_sha256`(reseg) 대조; 어긋나면 `resegment.py` 재실행 필요를 메시지로 |
| 대응 없는 교재가 늘어난다(새 교재 추가) | 표식이 목차 블록이면 이질성 재발 | FR-02 거부 + `REAL_PAGE_MARKER_BOOKS` 명시 목록 |
| 발표 KPI 변경(등급1/2 구성, 검출 쪽 수, 분야 쪽수) | 보고서·대시보드·README 의 인용 수치 전부 변경 | 하니스가 인용을 대조(S5·S7·S8), HWPX 는 스크립트 재생성; 이전 정본(블록 기준 v2)은 영향표에 열로 보존 |
| 교과서와 NCS 의 등급 출처가 달라진다(교과서는 워크북 상속 유지) | 설명 부담 | 교과서 워크북은 실제 쪽 기준이라 상속이 정당 — CLAUDE.md 에 명시 |

---

## 6. 결정 기록 · 진행 순서

### 6.1 연구책임자 결정 (2026-09-15 — 전부 A)

| ID | 질문 | 선택지 | 권장 |
|---|---|---|---|
| **D1** | NCS 등급 규칙 | A) 실제 쪽 본문에 regrade 기준선 하나(이전 기준과 동일, 워크북 상속 없음) / B) 현행 혼합 유지(실제 쪽으로 옮기되 라벨 등급 상속 — 라벨이 블록이라 대응 불가, 사실상 선택 불가) | **A** |
| **D2** | 대응 없는 새 2권 | A) 표식(실제 쪽)을 그대로 쓰고 명시 목록으로 허용 / B) `resegment.py` 를 두 권에 돌려 대응 생성(`NCS_PDF_ROOT` 필요) | **A**(B 는 ④와 함께 나중에) |
| **D3** | 발표 | A) 새 정본으로 교체(대시보드·README·CLAUDE.md), 블록 기준 v2 는 영향표 열로 보존 / B) 연구 변형으로만 두고 발표값 유지 | **A**(M2 종결) |
| **D4** | 분야별 쪽수 | A) PDF 쪽수(9,100) / B) 표식 최댓값 합(8,914) 유지 | **A**(TODOS 1(d)) |
| **D5** | 비단조 마커 1권 | A) 대응으로 대체되므로 재유도 없이 종결(기록만) / B) 별도 재유도 | **A** |
| **D6** | 기초보고서 HWPX | A) 정본 재실행 뒤 원본(20260911)에서 재생성해 `…_20260915_정본.hwpx` 로 교체 / B) 보고서는 v2 블록 기준 유지 | **A** |

### 6.2 진행 순서

1. 연구책임자: D1~D6 결정 + 정본 워크북 `data/` 복귀(sha256 확인).
2. 설계(`/pdca design`): `--page-maps` 입력·`RealPageIndex`(문서 → 줄→쪽, 쪽→줄들)·`assign_match_grades` 분기·manifest·`EXPECTED`·영향표·하니스 대응표.
3. 구현(TDD): fixture 문서 + fixture `pages.json` 으로 대응 적용·거부·판정·결속 테스트 → 구현 → 정본 재실행(`--force` 측정 → 가드 통과 실행) → 영향표.
4. 발표면·문서·HWPX 재생성 → 갭 분석 → ship.

---

## 7. 입력 자료

| 자료 | 경로 | 상태 |
|---|---|---|
| NCS 마크다운 86권 | `data_source/markdown/ncs` | 있음(sha256 `aa5c5e06…`) |
| 줄→쪽 대응 84권 | `data/markdown/ncs_paged/*.pages.json` | 있음(정본 줄 수와 일치) |
| 이전 기준 | `docs/03-analysis/data/reseg_summary.json`·`ncs_pages_reseg.csv` | 추적 |
| 키워드·NCS 등급 워크북 | `data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx` | 있음 — 2026-09-15 복귀, sha256 `80fdd14b…` = 정본 manifest 값 |
| 교과서 등급 워크북 | `data/ncs_keywords_in_markdown_results_교과서_results_20260415.xlsx` | 있음 |
| 기초보고서 원본 | `data/반도체 기초보고서_20260911.hwpx` | 있음 |

---

## 버전 이력

| 버전 | 날짜 | 변경 | 작성자 |
|---|---|---|---|
| 0.1 | 2026-09-15 | 초안 — 실측(§1.3)·결정 D1~D6 | Claude (Opus 5) |
| 1.0 | 2026-09-15 | Approved — D1~D6 전부 A, 워크북 복귀 확인 | 연구책임자 |
