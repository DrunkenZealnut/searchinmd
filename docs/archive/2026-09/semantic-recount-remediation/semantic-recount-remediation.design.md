# 의미 재검산 감사 시정 설계

> **Feature**: semantic-recount-remediation
> **Plan**: [semantic-recount-remediation.plan.md](semantic-recount-remediation.plan.md) (Approved 2026-09-13)
> **Author**: Claude (Opus 5)
> **Date**: 2026-09-13
> **Status**: Draft
> **Level**: Starter

---

## 1. 설계 목표

계획의 FR-01~FR-11 을 **정본 실행 1개 + 그 실행을 지키는 가드** 로 구현한다. 원칙 세 가지:

1. **수치는 한 곳에서만 태어난다.** `semantic_keyword_recount.py` 한 번의 실행이 xlsx·보고서 md·`semantic_recount_data.js`·`semantic_summary.json`·분리 분석 HTML 3건을 모두 쓴다. 발표면(HTML·README·CLAUDE.md)은 그 산출물을 인용만 하고, 하니스가 인용값을 산출물과 대조한다.
2. **바뀌면 멈춘다.** `EXPECTED` 가드는 `resegment.py`·`recount_grades.py` 와 같은 규약(`check_expected()` + `--force`). 실행 manifest 는 git commit·CLI·입력 SHA-256 을 기록해 "어느 실행이 정본인가"를 저장소가 답하게 한다.
3. **승인된 결정은 코드와 문서에 같이 남긴다.** 출현건수 분모(Q4)·미확정 강제 배정(Q2)·86권 코퍼스(Q1)는 각각 `EXPECTED` 키, 문서 문구, 하니스 단언으로 고정한다.

---

## 2. 아키텍처

```
data_source/markdown/ncs (87 파일)        data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx
data_source/markdown/school-text (9)      data/ncs_keywords_in_markdown_results_교과서_results_20260415.xlsx
        │                                            │
        ▼  load_documents() → select_ncs_documents() (LM 필수·중복 제거·마커 base 검사)
   semantic_keyword_recount.py  run_census()
        │  aggregate_matches → assign_match_grades → artifact_manifest(+run) → check_expected
        │        ↳ 불일치 & --force 없음 → exit 1, 아무것도 쓰지 않음
        ▼
   ┌─ data/semantic_keyword_recount_20260914.xlsx        (gitignore, 본문 포함)
   ├─ data/semantic_keyword_recount_20260914_report.md   (gitignore)
   ├─ docs/semantic_recount_data.js                      (추적) ─┐ 같은 JSON
   ├─ docs/03-analysis/data/semantic_summary.json         (추적) ─┘
   ├─ docs/keyword-analysis.html                          (추적, 목차)
   ├─ docs/NCS_키워드검색결과.html                         (추적, 상세)
   └─ docs/교과서_키워드검색결과.html                       (추적, 상세)
        │
        ▼  인용
   docs/index.html · textbook.html (렌더러 semantic_grade_dashboard.js 가 data.js 로 그림)
   README.md · CLAUDE.md · PDCA 문서
        │
        ▼  대조
   outputs/test-dashboard-data.js  (S1~S9)  +  test_semantic_keyword_recount.py  (코퍼스·가드·manifest·결정론)
   docs/03-analysis/data/reseg_summary.json  ←  이전 기준(2,189쪽·145) 의 유일한 출처
```

`data/markdown/` 은 복사본이므로 정본 실행은 `--ncs-root data_source/markdown/ncs --school-root data_source/markdown/school-text` 로 고정한다(README 재생성 절에 명령 그대로 기록).

---

## 3. 상세 설계

### 3.1 코퍼스 규칙 — FR-01, FR-01a (`semantic_keyword_recount.py`)

**`select_ncs_documents(documents) -> list[Document]`** (신설, `load_documents` 뒤에서 NCS 에만 적용)

| 단계 | 규칙 | 근거 |
|---|---|---|
| 1 | `_NCS_CODE_RE`(`LM\d{10}`) 가 `relative_path` 에 없으면 **ValueError** (조용히 버리지 않는다 — report 요약본 같은 비교재는 디스크에서 지우는 것이 규칙) | Q1 |
| 2 | 같은 LM 코드가 2개 이상이면 (마커 수 내림차순, 밑줄 경로 우선, 경로 사전순) 으로 1개 선택. 선택 결과는 `Document` 대신 별도 `DedupRecord(code, kept, dropped)` 리스트로 반환해 manifest 에 기록 | 1.3 실측: 공백 경로 마커 0 / 밑줄 경로 마커 84 |
| 3 | `REPORT_PATH_RE` 와 그 3개 사용처 삭제 | m4 |

**`check_marker_base(documents) -> list[str]`** (신설): 각 문서의 첫 `<!-- page: N -->` 을 읽어 N < 1 이면 `"<path>: 첫 마커 N"` 을 모은다. 비어 있지 않으면 `run_census` 가 ValueError — 새 2권을 시프트하지 않고 돌리면 여기서 멈춘다.

**문서 수 검증**: `len(ncs_documents) != 89` 하드코딩을 `EXPECTED["documents"]` (`{"NCS": 86, "교과서": 9}`) 대조로 바꾼다. `--force` 여도 이 검증은 우회하지 않는다(코퍼스가 다르면 정본이 아니다).

`PAGE_MARKER_RE` 는 `page_utils.PAGE_MARKER_RE` 를 import 해 한 정의로 통일한다(로컬 복사본 삭제).

### 3.2 마커 시프트 — FR-01a (`shift_page_markers.py`, 신설, 저장소 루트)

`insert_page_markers.py` 와 나란히 두는 단일 목적 도구. `data_source` 가 gitignore 라 **결과가 아니라 절차** 를 추적한다.

```
python3 shift_page_markers.py <file.md> [--by 1] [--dry-run] [--backup]
```

- `page_utils.PAGE_MARKER_RE` 로 마커 줄만 찾아 N → N+by 로 다시 쓴다. 마커가 아닌 줄은 바이트 단위로 보존.
- 거부 조건(exit 1, 파일 무변경): 마커 0개 / 결과 마커 < 1 / 시프트 전 비단조(마커 값이 감소) / 본문 줄 안에 낀 마커가 하나라도 있음(`insert_page_markers.py` 와 같은 규칙; R8q).
- 출력: `markers=120 first=0→1 last=119→120`. `--backup` 은 `<file>.bak` 을 남긴다.
- 적용 대상 2건과 실행 명령을 README `산출물 재생성` 절과 완료 보고서에 기록. `_meta.json` 은 건드리지 않는다(`page_id` 0-based 규약 그대로).

### 3.3 회귀 가드 — FR-03

```python
EXPECTED = {
    "documents": {"NCS": 86, "교과서": 9},
    "totals":    {"NCS": None, "교과서": None},            # semantic_total 합
    "grades":    {"NCS": {"1": None, "2": None, "3": None, "unpaged": 0},
                  "교과서": {"1": None, "2": None, "3": None, "unpaged": 0}},
    "grade_sources": {"existing": None, "new": None, "unpaged-context": None, "unpaged-fallback": None},
    "candidates": {"included": 75, "held": None, "excluded": None, "not-found": None},   # 합 100 — 키는 CandidateDecision 의 기존 명명
    "dedup": {"LM1903060205": 1},                        # 코드별 버린 파일 수
    "rule_sha256": "<현재 값 유지>", "source_sha256": None, "detail_sha256": None, "summary_sha256": None,
}
```

- `None` 인 값은 **아직 고정 전** 이라 비교하지 않는다(정본 실행 후 인쇄된 블록을 붙여 넣어 고정). 고정 뒤에는 `None` 이 남아 있으면 안 되므로 하니스가 `EXPECTED` 에 `None` 이 0개인지 확인한다(`test_expected_block_is_fully_pinned`).
- `check_expected(result, manifest) -> list[str]`: 키마다 `"<키>: <실측> != <기대>"`. `resegment.check_expected` 처럼 special 키 외 나머지는 그대로 대조.
- `run_census(..., force=False)`: 결과·manifest 를 만든 **뒤**, 쓰기 **전** 에 검사. 불일치이고 `force=False` → `SystemExit(1)` 와 불일치 목록 출력, 파일 무변경. `force=True` → 쓰되 manifest `expected` 를 `null` 로, 불일치 목록을 `expected_mismatch` 에 기록(resegment 규약).
- `grades.*.unpaged` 는 0 으로 고정 — Q2 결정을 코드가 지킨다(FR-02).

### 3.4 실행 manifest 와 결정론 — FR-04

`artifact_manifest(result)` 는 4종 해시를 유지하고, `run_manifest(result, argv, force)` 를 신설해 아래를 더한다.

```json
"run": {
  "generated_at": "2026-09-13T22:40:11+09:00",
  "git_commit": "6021edd", "git_dirty": true,
  "command": "python3 semantic_keyword_recount.py --source-workbook data/ncs_keywords_…_20260414.xlsx --ncs-root data_source/markdown/ncs …",
  "python": "3.12.4", "openpyxl": "3.1.5",
  "inputs": [{"kind": "키워드 등록 워크북", "count": 1, "sha256": "…"}, {"kind": "NCS Markdown", "count": 86, "sha256": "…"}, …],
  "dedup": [{"code": "LM1903060205", "kept": "반도체제조/LM…_MI_장비_운영/…md", "dropped": ["반도체제조/LM…_MI 장비 운영/…md"]}],
  "expected": true, "expected_mismatch": [], "force": false
}
```

- 경로는 `public_path()` (resegment 와 같은 규칙: 저장소 상대 또는 `~`) 로만 쓴다. 절대 경로·홈 디렉터리는 어떤 산출물에도 남지 않는다(하니스 S3 가 `/Users/` 부재를 확인).
- 기록 위치: xlsx `입력정보` 시트 하단 "실행 정보" 행들, 보고서 md `## 실행 정보`, `semantic_summary.json.meta.run`, `semantic_recount_data.js` 첫 줄 주석(하드코딩된 `20260909.xlsx` 문구 제거).
- **결정론**: `generated_at`·`git_*` 은 해시 4종과 `dashboard_payload` 비교에서 제외한다. 테스트 `test_two_runs_on_same_fixture_are_identical`: 같은 fixture 로 `aggregate_matches`+`assign_match_grades` 2회 → `artifact_manifest` 4종 동일, `dashboard_payload` (meta.generated 제외) 동일, `write_workbook` 2회의 시트 내용 동일.

### 3.5 `semantic_summary.json` — FR-05 (추적, `docs/03-analysis/data/`)

`dashboard_payload()` 의 JSON 그대로 + `meta.run` + `meta.previous_basis`. `semantic_recount_data.js` 는 `window.SEMANTIC_RECOUNT=<같은 JSON>;` 이므로 두 파일은 **바이트가 아니라 JSON 이 같다**(하니스 S2 가 deep-equal).

```
meta:   generated, denominator:"occurrences", gradeLabels, run{…}, manifest{4 해시},
        previous_basis:{source:"docs/03-analysis/data/reseg_summary.json", date:"2026-09-06" (PREVIOUS_BASIS_DATE 상수 — reseg 는 날짜를 싣지 않는다), unit:"pages",
                        pages:2189, page_g:{1,2,3}, books:86, cases_pages:13}
corpora: NCS/교과서 → documents, total, graded, grades{1,2,3,unpaged}, grade_sources{existing,new,unpaged-context,unpaged-fallback}, groups[]
keywords: [{name, expressions[], corpora{…}}]      ← 표현 문자열은 사전 값이지 본문이 아니다
status:  {included, held, excluded, not-found}
```

`previous_basis` 는 `--previous-basis <reseg_summary.json>` 로 읽어 **복사** 한다 — 렌더러가 브리지 표를 데이터에서 그리게 하기 위해서다. 원본과 어긋나면 하니스 S4 가 잡는다. 본문 텍스트·파일 경로(`relative_path`)는 담지 않는다.

### 3.6 한 실행에서 나오는 산출물 — FR-05

`run_census` 시그니처에 `summary_out`, `analysis_dir`, `previous_basis`, `force` 를 더하고 CLI 에 `--summary-out`, `--analysis-dir`, `--previous-basis`, `--force` 를 만든다. 정본 명령(README 에 그대로):

```bash
python3 semantic_keyword_recount.py \
  --source-workbook data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx \
  --ncs-root data_source/markdown/ncs --school-root data_source/markdown/school-text \
  --xlsx-out data/semantic_keyword_recount_20260914.xlsx \
  --report-out data/semantic_keyword_recount_20260914_report.md \
  --dashboard-data-out docs/semantic_recount_data.js \
  --summary-out docs/03-analysis/data/semantic_summary.json \
  --analysis-dir docs --previous-basis docs/03-analysis/data/reseg_summary.json
```

**분리 분석 HTML** (`write_analysis_pages(result, docs_dir)`, `export_keyword_outputs.py` 의 `make_html`·`table_html`·`summary` 를 흡수 후 그 파일은 삭제):

| 파일 | 내용 | 변경점 |
|---|---|---|
| `docs/keyword-analysis.html` | 목차 | 날짜 없는 링크, "기준 파일" 을 manifest 의 xlsx 이름·git commit 으로, "85개 자료" → "NCS 교재 86권 · 교과서 9권" |
| `docs/NCS_키워드검색결과.html` | 요약표 + 상세표 | 파일명에서 날짜·`report제외` 제거(링크 안정), 헤더 총 건수는 payload 값 |
| `docs/교과서_키워드검색결과.html` | 〃 | 〃 |

기존 `docs/NCS_키워드검색결과_report제외_20260911.html`·`docs/교과서_키워드검색결과_20260911.html` 은 `git rm`. 본문 문맥 열은 유지(Q8).

### 3.7 발표면 갱신 — FR-06, FR-07, FR-08

**`docs/index.html` · `textbook.html`**
- `.ctn` 은 렌더러가 데이터로 그리므로 수치 편집 없음. 렌더러에 **브리지 절** 추가: `meta.previous_basis` 가 있으면 KPI 아래에 "이전 기준(페이지 단위, 2026-09-06 재세그먼트): 검출 2,189쪽 · 등급3 145쪽(6.6%)" 한 줄과 브리지 표(§3.9 서식)를 그린다. NCS 에만 표시(교과서는 이전 기준이 바뀌지 않았다 — 362쪽·8쪽은 `summary.json` 그대로).
- `<template id="legacy-dashboard">` 안의 하드코딩 수치(hero 14,168/12,875/1,293/98, KPI 145/2,189 등)는 렌더러가 실패했을 때만 보이는 정적 대체 화면이다. 정본 값으로 교체하고 하니스 S5 가 payload 와 대조한다. 대체 화면의 페이지 기준 KPI 3장(L135~137)은 "이전 기준" 라벨을 붙인다.
- 산문(L188·196 "86권 중 57권" 등 `reseg` 파생값)은 그대로 — 이전 기준 문맥임을 절 제목에 명시.
- m2: 기존/동등/구체 막대에 `--g1/--g2/--g3` 를 쓰던 코드는 `index.html` 의 **죽은 스크립트**(0f47e3e 세대 의미 렌더러, `if(!SEMANTIC_RECOUNT || SEMANTIC_RECOUNT.meta) return` 으로 실행되지 않음, "NCS 89개" 문자열 보유)였다. 새 토큰을 만드는 대신 그 스크립트를 삭제한다(하니스 S5h). 살아 있는 렌더러는 계층 막대를 그리지 않으므로 `--t*` 토큰은 두지 않는다. *(Do 에서 확정, 초안의 `--t1~3` 안 폐기.)*

**README.md**

| 줄 | 현재 | 변경 |
|---|---|---|
| 9 | "report 자료 4개를 제외한 85개 자료 기준" | "NCS 교재 86권 · 교과서 9권 기준(2026-09-13 정본 실행)" |
| 13 | "검출 2,189쪽(원본 PDF 실제 쪽 기준)의 등급 분포" | "의미 출현 N건(출현건수 기준)의 등급 분포 · 이전 기준(실제 쪽) 2,189쪽 병기" |
| 17 | 핵심 수치 6.6% / 2.2% (페이지 분모) | 핵심 수치를 출현건수 기준(등급3 비율 NCS x.x% / 교과서 y.y%, 분모 등급 확정 출현)으로 바꾸고, 괄호에 "이전 기준(페이지 단위) NCS 6.6%(145/2,189), 교과서 2.2%(8/362)" 병기 + 브리지 표 링크 |
| 44~ 산출물 재생성 | `recount_grades.py`·`resegment.py` 만 | `semantic_keyword_recount.py` 정본 명령(§3.6)·`shift_page_markers.py` 절차·`data_source` 가 원본이고 `data/markdown` 은 복사본이라는 문장 추가 |
| 72·144·153·154 | resegment 서술 | 유지. 첫 문장에 "(이전 기준 — 2026-09-13 부터 대시보드 KPI 는 출현건수 기준)" 삽입 |
| 테스트 블록 | `test-dashboard-data.js # 153` | 하니스 출력값으로 교체(D14) |

**CLAUDE.md**
- "Safety Grading Scheme" 의 두 규칙 아래에 예외 문단: *"Exception (research lead, 2026-09-13): the semantic-occurrence dashboards (`index.html`/`textbook.html` since 2026-09-09) use **occurrence count** as the grade denominator — every included keyword-expression match carries its page's grade and is counted once. This weights pages by how many matches they hold (a 등급3 page is by definition keyword-dense, so 등급3's share is ~3× its page-share: 20.6% vs 6.6% on the 2026-09 data). The page-unit numbers (2,189 / 145) stay published as the *previous basis* next to it; the bridge table in `semantic-occurrence-grades.report.md` §X says how the two relate. Do not present the occurrence share as an improvement over the page share."*
- Data pipeline 절에 4번째 그룹 "4. 의미 단위 재검산" 을 신설해 `semantic_keyword_recount.py`(입력·정본 명령·`EXPECTED`·manifest·산출물 7종)·`shift_page_markers.py`·`semantic_summary.json` 을 기술. 지금은 이 스크립트가 CLAUDE.md 에 없다.
- Testing 블록의 `test-dashboard-data.js` 수치, Test Coverage 의 `D13`·`D14` 서술을 새 S 그룹으로.
- "Two traps" 옆에 세 번째: `data_source/` 는 gitignore, 원본이며 `data/markdown` 은 복사본.

**PDCA 문서** (`semantic-keyword-recount` · `semantic-occurrence-grades`)
- plan §2 제외 "페이지가 없는 출현에 … 등급을 강제 부여" → 삭제하고 §3 성공 기준 "페이지 미확정 출현은 별도 상태로 보존" → "페이지 마커 없는 출현은 문맥 기준 판정 또는 등급1 배정(연구책임자 승인 2026-09-13, 정본 N건)". 버전 이력에 1.1 추가(승인자 명기, m3).
- report "페이지 마커가 없는 출현은 `등급 미확정`으로 보존했다" → 승인 문구. 등급 출현 결과 표·계보 표를 정본 값으로. 브리지 표 절 신설(§3.9).
- 두 analysis 의 "Match Rate 100%" → "설계 항목 구현률 100%"(m5). `semantic-keyword-recount.analysis.md:63` 해시 4종을 정본 값으로.
- 데이터 보고서 md `:14` "총계는 만들지 않았다" 와 대시보드 "전체 분모 14,168건" 의 모순(m1): `write_report`·렌더러 문구를 "키워드-표현 매칭 레코드 합계(고유 문장·쪽 수 아님)" 로 통일.

### 3.8 교차검증 하니스 — FR-09 (`outputs/test-dashboard-data.js`)

옛 `check()/known()/fmt()/pct()` 헬퍼를 복원하고, 현재 18개는 **S1** 로 유지한 채 아래를 더한다. 하드코딩 값끼리의 단언(현재 25~26행)은 S2·S3 로 대체.

| 그룹 | 대조 | 단언 |
|---|---|---|
| S1 렌더러 | data.js → `.ctn` | 현재 18개(섹션 순서·등급 열·공통 렌더러 연결) 그대로 |
| S2 data ↔ summary | `semantic_recount_data.js` JSON ≡ `semantic_summary.json` | deep-equal 1건 + `meta.run.expected === true`, `force === false` |
| S3 summary 자체 정합 | summary 내부 | corpus 별 grades 합 == total, graded+unpaged == total, unpaged == 0, keywords 합 == corpus total, groups 합 == corpus total, status 합 == 100, documents NCS 86 / 교과서 9, grade_sources 합 == graded, 파일에 `/Users/`·`relative_path` 없음 |
| S4 이전 기준 계보 (옛 D13) | `meta.previous_basis` ≡ `reseg_summary.json` (pages, page_g, books, cases_pages) ; `reseg.meta.expected` 있음 ; `marker_offset.moved` 0 (옛 D13q) | 4건 |
| S5 대시보드 정적 화면 | `index.html`·`textbook.html` `<template>` 수치 == summary(hero 5장, 등급 KPI, 86권) ; 렌더된 `.ctn` 에 브리지 절·이전 기준 문구 ; 구 수치(`12,875`·`4,869`·`813건`·`89개`·`85개`) 가시 소스에 0회 | ~10건 |
| S6 분리 분석 페이지 | `keyword-analysis.html`·결과 HTML 2건 헤더 총 건수 == summary total, 기준 파일 == `meta.run` xlsx 이름, "86권" | 5건 |
| S7 README | 핵심 수치 문장 == summary(등급3 비율·분모) ; "이전 기준" 문장 == reseg(2,189·145·6.6%) ; "85개" 0회 ; 재생성 절에 정본 명령 | 4건 |
| S8 CLAUDE.md | 예외 문단 존재(문자열 "occurrence count as the grade denominator") ; `data_source` 트랩 문장 | 2건 |
| S9 (옛 D14) | README·CLAUDE.md 가 인용한 `test-dashboard-data.js # N` == 실측 | 1건 |

`EXPECTED` 가 `None` 없이 고정됐는지는 Python 쪽(`test_expected_block_is_fully_pinned`)이 본다.

### 3.9 브리지 표 서식 (report·index.html 공통)

| 항목 | 출현건수 기준 (공식, 2026-09-13~) | 페이지 기준 (이전 기준, 2026-09-06 재세그먼트) |
|---|---|---|
| 분자 | 등급 g 를 가진 포함 매칭 레코드 수 | 등급 g 인 고유 (교재, 실제 쪽) 수 |
| 분모 | 등급 확정 출현(= 전체 출현, 미확정 0) | 키워드 검출 고유 쪽 2,189 |
| 같은 쪽의 중복 | 매칭마다 1 (쪽이 키워드 밀도로 가중됨) | 쪽당 1 |
| 미확정 처리 | 문맥 판정 또는 등급1 (Q2) | 라벨 유지 51쪽 |
| 코퍼스 | 86권 마크다운 | 84권 마크다운 + 2권 라벨 |
| 읽는 법 | "키워드가 나오는 자리 중 몇 %가 구체적 대책 페이지에 있는가" | "검출된 쪽 중 몇 %가 구체적 대책인가" |
| 등급3 비율 | N/M (x.x%) | 145/2,189 (6.6%) |

표 아래 고정 문장: *두 값의 차이는 가중 방식의 차이이지 교재가 나아졌거나 측정이 정밀해진 것이 아니다.*

### 3.10 구산출물 정리 — FR-10

| 대상 | 조치 |
|---|---|
| `data/semantic_keyword_recount_20260909.xlsx`·`_report.md`, `20260910_all_graded.xlsx`·`_report.md`, `20260911_report_excluded.xlsx`, `data/keyword_outputs_20260911/` | `data/archive/2026-09-semantic-pre-remediation/` 로 이동(gitignore 영역, 로컬 보존) |
| `docs/semantic_recount_data_20260910_all_graded.js` (미추적) | 삭제 |
| `docs/NCS_키워드검색결과_report제외_20260911.html`·`docs/교과서_키워드검색결과_20260911.html` | `git rm` (§3.6 의 날짜 없는 파일로 대체) |
| `export_keyword_outputs.py` (미추적) | §3.6 흡수 후 삭제 |
| `.gitignore` | `/data_source/` 추가 (FR-01b). 미커밋 `.bkit-codex/` 줄은 그대로 |

### 3.11 미커밋 diff 처리

| 부분 | 조치 |
|---|---|
| `assign_match_grades` 의 `unpaged-context`/`unpaged-fallback` 분기 | 유지(Q2). docstring 에 승인 근거 한 줄 |
| `test_unpaged_match_uses_its_occurrence_context` 와 기대값 변경 | 유지 |
| `REPORT_PATH_RE` 정의 + 사용처 3곳 | 삭제 (§3.1) |
| `.gitignore` `.bkit-codex/` | 유지 |

---

## 4. 테스트 설계 — 커버리지 대응표

| FR | 테스트 (`test_semantic_keyword_recount.py` 는 `T`, `test-recount-grades.py` 는 `R`, 하니스는 `S`) |
|---|---|
| FR-01 | `T corpus_rejects_file_without_lm_code`, `T corpus_keeps_marker_rich_duplicate_and_records_dedup`, `T run_census_checks_document_counts_against_expected`(89 하드코딩 소멸) |
| FR-01a | `T check_marker_base_reports_zero_based_files` ; `R8k shift_page_markers +1`, `R8l 거부: 결과 < 1`, `R8m 거부: 비단조`, `R8n --dry-run 무변경`, `R8o 마커 외 바이트 보존` |
| FR-01b | `S3` 파일 내 `/Users/` 부재 ; 수동: `git status` 에 `data_source/` 없음(완료 보고서에 출력 첨부) |
| FR-02 | 기존 `T unpaged_match_uses_its_occurrence_context` + `T expected_pins_unpaged_to_zero` |
| FR-03 | `T check_expected_lists_every_mismatch`, `T run_census_refuses_to_write_on_mismatch`(파일 부재 확인), `T force_writes_and_records_mismatch`, `T expected_block_is_fully_pinned`(정본 고정 후) |
| FR-04 | `T run_manifest_has_commit_command_inputs_versions`, `T public_path_never_absolute`, `T two_runs_on_same_fixture_are_identical` |
| FR-05 | `T summary_json_equals_dashboard_payload`, `T analysis_pages_cite_manifest_and_totals` ; `S2`, `S6` |
| FR-06 | `S5`, `S7` 구 수치 0회 |
| FR-07 | `T payload_copies_previous_basis` ; `S4`, `S5` 브리지 절, `S7` |
| FR-08 | `S8` |
| FR-09 | 하니스 자체 (`S1`~`S9`) + `S9` |
| FR-10 | 수동 — 완료 보고서에 `ls` 출력 |
| FR-11 | `S5h`(죽은 스크립트·참조 없는 js 부재), 문서 grep |

목표: 변경 함수 전부가 위 표의 한 항목 이상에 걸린다(계획 NFR 커버리지 ≥ 80%).

---

## 5. 구현 순서 (Do)

1. `.gitignore` 에 `/data_source/` — 다른 무엇보다 먼저.
2. `shift_page_markers.py` + R8k~o → 새 2권 시프트 실행(`--backup`), 전후 수치 기록.
3. `semantic_keyword_recount.py`: §3.1 코퍼스 규칙·마커 검사·문서 수 검증 → §3.3 `EXPECTED`(None)·`check_expected`·`--force` → §3.4 manifest·`public_path` → §3.5/3.6 `summary_out`·`analysis_dir`·`previous_basis`·`write_analysis_pages` → 테스트 T 전부.
4. 정본 실행 1차(`--force`, EXPECTED 미고정) → 인쇄된 블록으로 `EXPECTED` 고정 → **정본 실행 2차(`--force` 없이)** 가 통과해야 한다. 2차 산출물이 정본. 미확정 건수 ≤ 5 확인(초과 시 중단·보고).
5. 렌더러 브리지 절·토큰, `index.html`·`textbook.html`·`osha.html` 정적 화면·토큰 블록.
6. README·CLAUDE.md·PDCA 4문서·analysis 해시.
7. 하니스 S1~S9 작성 → 실행 → 인용 수치(README·CLAUDE.md) 동기화 → 전체 하니스 5종 + `test_semantic_keyword_recount.py` 통과.
8. 구산출물 정리(§3.10).
9. `/pdca analyze` → 보고서.

---

## 6. 결정 기록

| 항목 | 결정 | 근거 |
|---|---|---|
| MI 장비 운영 중복 파일 | **디스크에서 지우지 않는다** — `data_source` 는 연구책임자 지정 원본. `select_ncs_documents` 가 버리고 `EXPECTED["dedup"]`·`meta.run.dedup` 이 기록 | Do 에서 확정 (계획 §2.1 "로컬에서 제거" 대체) |
| 정본 산출물 날짜 | `20260914` (실행일) | 계획의 `<날짜>` |
| `test_semantic_keyword_recount.py` CI | openpyxl 설치 단계 뒤에 CI 마지막 스텝으로 추가 | 계획 NFR "기존 하니스 전부 통과" |
| 키워드 등록 워크북 | `data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx` (NCS 등급 워크북 겸용, 현행 기본값) | 연구책임자 2026-09-13 |
| 원본 루트 | `data_source/markdown/{ncs,school-text}` | 연구책임자 2026-09-13 |
| 새 2권 마커 | +1 시프트, `_meta.json` 불변, TOC 재유도 안 함 | 1.3 실측(밀도 25~28행/마커) |
| 중복 선택 | 마커 수 → 밑줄 경로 → 사전순 | MI 장비 운영 실측 |
| LM 코드 없는 파일 | 오류로 중단(무시 아님) | 코퍼스 오염을 조용히 넘기지 않기 위해 |
| 분리 분석 HTML 파일명 | 날짜 제거, 고정 이름 | 링크·하니스 안정 |
| `previous_basis` | reseg 값을 payload 에 복사, 하니스가 원본과 대조 | 렌더러가 데이터만 보게 |
| 계층 토큰(m2) | 새 토큰 없음 — 등급 토큰을 계층에 쓰던 코드는 죽은 스크립트라 삭제 (§3.7) | v1.1 |

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 1.0 | 2026-09-13 | 초안 | Claude (Opus 5) |
| 1.1 | 2026-09-14 | Do 확정 사항 반영 — m2 는 죽은 스크립트 삭제로, 중복 파일 보존, 산출물 날짜, CI 스텝 | Claude (Opus 5) |
| 1.2 | 2026-09-14 | Check 갭 반영 — `not-found` 키, `previous_basis.date` 상수, §4/§6 토큰 문구 정정, 혼재 마커 거부(R8q) | Claude (Opus 5) |
