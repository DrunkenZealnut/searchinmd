# 의미 출현을 실제 PDF 쪽에 얹기 설계

> **Feature**: occurrence-real-pages
> **Plan**: [occurrence-real-pages.plan.md](../../01-plan/features/occurrence-real-pages.plan.md) (Approved 2026-09-15 — D1~D6 전부 A)
> **Author**: Claude (Opus 5)
> **Date**: 2026-09-15
> **Status**: Implemented (Do 2026-09-15, Check 90.8% → Act-1 100%)
> **Level**: Starter

---

## 1. 설계 목표

1. **사전의 의미는 건드리지 않는다.** 매칭·동음이의 제외·보류·동반어 창(같은 줄 ±1, 표식 블록 안)은 지금처럼 **표식 블록** 위에서 돌고, 출현 총계 11,517 / 1,207 은 그대로다. 실제 쪽은 매칭이 끝난 레코드에 **덧씌우는 속성**이다(`page`) — 계획 §1.3 의 실측이 바로 이 방식(스캔 불변, 쪽·등급만 재배정)으로 나온 값이다.
2. **등급 규칙 하나.** NCS 출현의 등급은 실제 쪽 본문(그 쪽에 대응된 줄 전부)에 `regrade.grade_page(word_boundary=False, normalize=False)` — 이전 기준 `resegment.py` 와 같은 호출. 2026-04 워크북 라벨 상속(`existing`)은 NCS 에서 끊는다(D1). 교과서는 현행 유지.
3. **이전 기준과의 결속을 실행이 증명한다.** 공유 쪽의 등급 일치율을 계산해 manifest 에 남기고 `EXPECTED` 가 100% 를 고정한다(FR-04).
4. **입력은 있는 것을 재사용한다.** `data/markdown/ncs_paged/*.pages.json`(84권)과 `reseg_summary.json`(이미 `--previous-basis` 입력)만 추가로 읽는다. 대응이 없는 교재는 명시 목록(D2)으로만 허용한다.
5. **모든 산출물이 한 실행에서 나온다** — xlsx·report·`semantic_recount_data.js`·`semantic_summary.json`·분리 HTML 3건, 그리고 새 영향표. HWPX 는 그 정본을 읽어 재생성.

---

## 2. 아키텍처

```
data/markdown/ncs_paged/<LM>.pages.json ──┐            docs/03-analysis/data/reseg_summary.json (--previous-basis, 이미 입력)
   {md, line_pages[]} ×84                 │            docs/03-analysis/data/ncs_pages_reseg.csv (결속 검사)
                                          ▼
run_census ─ load_documents ─ select_ncs_documents ─ aggregate_matches(sources, documents, rules, candidates, page_maps)
                                                         │  scan_document (표식 블록 — 불변)
                                                         │  apply_page_maps(matches, documents, page_maps)   ← 새 단계: page ← line_pages[line-1]
                                                         │  summary rows (page_count 는 실제 쪽)
                                                         ▼
                              assign_match_grades(result, existing_grades, page_maps)
                                                         │  NCS 대응 문서: page_lines[(NCS, rel, 실제 쪽)] ← 대응된 줄들, grade_page 기준선, source "real-page"
                                                         │  NCS 대응 없는 문서(REAL_PAGE_MARKER_BOOKS): 표식 블록(= 실제 쪽) 본문 판정, source "real-page" (워크북 라벨 없음)
                                                         │  교과서: 현행
                                                         ▼
                              reseg_agreement(result, ncs_pages_reseg.csv) ─ manifest ─ EXPECTED(check_expected) ─ 산출물
                                                         │
                              summary_payload: groups[].pages ← per_book.pdf_pages(previous_basis) + 대응 없는 교재 표식 최댓값, meta.page_basis "real"
```

- `PageMaps` 는 `load_page_maps(dir, documents)` 가 만드는 `dict[relative_path, tuple[int, ...]]` — 문서마다 검증을 통과한 `line_pages` 만 담는다.
- `hwpx_results_refresh.py` 는 `facts.page_basis`(`meta.page_basis`) 로 2절·3절 문구를 분기한다(§3.8).

---

## 3. 상세 설계

### 3.1 대응 로딩·검증 — FR-01·02 (`load_page_maps`)

```python
REAL_PAGE_MARKER_BOOKS = ("LM1903060408", "LM1903060424")   # D2: 대응 없음이 허용되는 교재 — 2026-09-13 변환, 표식이 실제 쪽(25~28줄/쪽)

def load_page_maps(directory: Path, documents: list[Document]) -> dict[str, tuple[int, ...]]:
```

- NCS 문서마다 `_NCS_CODE_RE` 로 LM 코드를 뽑아 `directory/<코드>.pages.json` 을 찾는다.
- 있으면 검증: (a) `md` == 문서 파일 이름(`Path(document.path).name`) — 다른 판·다른 쌍둥이 파일의 대응 거부, (b) `len(line_pages) == len(document.text.split("\n"))`, (c) 모든 값이 1 이상의 정수. 실패는 `ValueError`(어느 교재, 무엇이 어긋났는지).
- 없으면 코드가 `REAL_PAGE_MARKER_BOOKS` 에 있어야 한다. 아니면 `ValueError("줄→쪽 대응이 없습니다 — resegment.py 로 만들거나 REAL_PAGE_MARKER_BOOKS 에 넣으십시오")`. 목록에 있는데 대응이 **있으면** 대응을 쓴다(목록은 예외 허용일 뿐).
- 목록에 있는 문서는 표식이 실제 쪽이어야 하므로 표식 값이 1..N 으로 빠짐·중복 없이 이어지는지만 검사한다(빈 쪽은 블록이 없어도 된다) — 어긋나면 오류.
- 반환값 외에 manifest 용 `page_maps_manifest = {"dir": public_path, "files": n, "sha256": sha256(정렬된 (코드, 파일 sha256) 목록)}` 를 같이 돌려준다(`PageMapsInfo` 데이터클래스).
- 교과서 문서는 대응 대상이 아니다(무시).

### 3.2 쪽 덧씌우기 — FR-01 (`apply_page_maps`)

```python
def apply_page_maps(matches, page_maps) -> list[MatchRecord]:
    # record.corpus == "NCS" and record.relative_path in page_maps → replace(record, page=page_maps[rel][record.line - 1])
```

- `aggregate_matches(..., page_maps=None)` 가 `scan_document` 직후, 요약 행 계산 **전**에 호출한다 — `page_count`(검출 쪽 수)·`unpaged_file_count` 가 실제 쪽 기준이 된다. `with_summary=False`(영향표 경로)에서도 적용.
- 대응 없는 문서·교과서·`page is None` 레코드는 그대로.
- 제외(`excluded`)·보류 레코드도 같은 규칙으로 쪽을 받는다(xlsx 상세·문맥근거 시트의 쪽 열이 일관되게).

### 3.3 등급 판정 분기 — FR-03 (`assign_match_grades(result, existing_grades, page_maps=None)`)

- `page_lines` 를 만들 때 NCS 대응 문서는 `split_pages` 대신 대응으로 묶는다: 줄 i(1-based)의 본문을 `page_lines[(NCS, rel, line_pages[i-1])]` 에 넣되 표식 줄(`PAGE_MARKER_RE`)은 뺀다. 나머지 문서는 현행 블록 묶기.
- 대응 문서의 레코드와 **목록 교재(`REAL_PAGE_MARKER_BOOKS`, 표식 = 실제 쪽)의 레코드**는 `existing_grades` 를 보지 않고 곧장 실제 쪽 본문 판정: `GradeAssignment(grade, GRADE_LABEL[grade], reason, "real-page")`(목록 교재는 표식 블록 본문); 본문이 비면 현행대로 `unpaged-fallback`(등급1) — 정본에서는 0건이어야 하고 `EXPECTED` 가 `unpaged` 0 을 고정한다. `page_maps` 가 비어 있으면(대응 없는 실행) 목록 교재도 현행(워크북 상속/블록 판정) 그대로다.
- **줄 규약(갭 G-1)**: 매칭의 `record.line` 은 `text.splitlines()` 번호이고 대응 파일은 `text.split("\n")` 번호라, `\x0c` 같은 줄 구분자가 있는 파일(정본 코퍼스 1권 `LM1903060128` 430행)에서는 그 뒤가 한 줄씩 어긋난다. `load_page_maps` 가 `_to_matching_lines` 로 대응을 매칭 규약으로 옮겨 싣고(같은 쪽을 k 번, 파일 끝 개행 뒤 빈 원소는 뺌; 결과 길이 = `splitlines()` 길이가 아니면 오류), `page_lines` 도 `splitlines()` 로 묶는다. 길이 검사는 대응 규약(`split("\n")`) 그대로.
- `GRADE_SOURCES` 에 `"real-page"` 추가, `GRADE_SOURCE_LABEL["real-page"] = "실제 쪽 판정"`. `STRICT_GROUPS` 의 `grade_sources` 는 새 키를 `EXPECTED` 에 적어야 통과한다(의도된 마찰).
- 판정 캐시 `newly_graded[(corpus, rel, page)]` 는 그대로 — 같은 실제 쪽의 출현은 한 번만 판정.

### 3.4 이전 기준과의 결속 — FR-04 (`reseg_agreement`)

```python
def reseg_agreement(result, csv_path) -> dict:   # {"pages": n, "agree": n, "disagree": [...최대 20건]}
```

- `ncs_pages_reseg.csv`(추적)를 `utf-8-sig` 로 읽어 (LM 코드, 페이지) → 등급 — `출처 == label` 행(마크다운이 없던 2권의 라벨 쪽, 실제 쪽이 아님)은 뺀다. 결과의 NCS 레코드 중 `grade_source == "real-page"` 인 (코드, 쪽) 집합과 교집합의 등급을 비교.
- manifest `run["reseg_agreement"] = {"pages": …, "agree": …}`; `summary_metrics` 가 `reseg_agreement` 를 싣고 `EXPECTED["reseg_agreement"] = {"pages": 2035, "agree": 2035}`(정본 실행 값으로 고정 — 계획 §1.3 예측치, 실측으로 확정). 불일치는 `check_expected` 의 일반 규칙(값 비교)으로 잡힌다.
- 결속 검사가 100% 가 아니면 원인은 둘뿐 — 대응 파일이 바뀌었거나 `regrade` 규칙이 바뀌었다 — `run_census` 의 가드 출력이 `reseg_agreement` 불일치일 때 그 문장과 `disagree` 상위 5건을 덧붙인다.

### 3.5 분야별 쪽수 — FR-05 (D4)

- `dashboard_payload(result, pdf_pages=None)`: `pdf_pages: dict[LM코드, int]` 가 주어지면 NCS 그룹의 `pages` 는 문서별 `pdf_pages[코드]`(없으면 표식 최댓값 — D2 교재) 의 합; 교과서는 현행(표식 최댓값). `run_census` 는 `load_previous_basis` 가 읽는 `reseg_summary.json` 의 `per_book[*].pdf_pages` 에서 `pdf_pages` 를 만든다(키는 `per_book` 이름의 LM 코드).
- `meta.page_basis = {"NCS": "real", "교과서": "marker"}` 와 `meta.run.page_maps` 를 payload 에 싣는다. 하니스 `S3n`: NCS `groups[].pages` 합 == `reseg_summary.per_book.pdf_pages` 합 + D2 교재 표식 최댓값.

### 3.6 manifest · EXPECTED · metrics — FR-06

- `run_manifest(..., page_maps=PageMapsInfo)` → `"page_maps": {"dir", "files", "sha256"}`, `"real_page_marker_books": [...]`, `"reseg_agreement"`.
- `summary_metrics` 에 `page_basis`, `reseg_agreement`, `page_maps_sha256` 추가; `EXPECTED` 재고정 항목: `totals`(불변 11,517/1,207), `grades`, `grade_sources`(`real-page`/`new`/`existing`/`unpaged-*`), `reseg_agreement`, `page_maps_sha256`, `detail_sha256`, `summary_sha256`(`rule_sha256`·`source_sha256` 불변 — 사전·입력 본문이 안 바뀌므로 그 불변이 자기 검증이 된다).
- `test_committed_summary_json_matches_expected` 는 새 키를 자동으로 본다(metrics 를 payload 에서 다시 만든다).
- 변형 실행(`--dictionary v1|v1fix`)도 대응을 쓴다 — 영향표 비교가 같은 쪽 기준이 되게. `--no-page-maps` 는 두지 않는다(블록 기준 실행은 영향표 스크립트가 내부적으로만 만든다, §3.7).

### 3.7 영향표 — FR-07 (`occurrence_real_pages_impact.py` → `docs/03-analysis/data/occurrence_real_pages_impact.json`)

- 같은 코퍼스·같은 사전(v2)으로 두 번 집계: (A) 블록 기준 = `aggregate_matches` + `assign_match_grades` 를 대응 없이(현 정본 방식), (B) 실제 쪽 기준 = 대응 적용. 워크북 등급 상속은 (A) 에만 적용(현 정본 재현). 
- 기록: `totals`(같아야 함), `grades`(A/B, 말뭉치별), `transition`(A→B 등급 이동 행렬 6칸 + 불변), `by_source`(A 의 `existing`/`new` 별 불변율), `by_book_kind`(실제 쪽/목차 블록 교재별), `keywords`(키워드별 A/B 등급), `groups`(분야별 A/B), `pages`(검출 쪽 수 A/B, 블록 폭 분포), `meta`(입력 sha256, 실행 시각, git). 본문·절대 경로 없음.
- (A) 가 옛 정본(상수 `BLOCK_BASIS_V2` = 2026-09-14 정본의 등급 4,378/4,614/2,525 · 633/459/115)과 같은지 실행이 스스로 확인한다(계보 검증) — 다르면 멈춘다. 레코드 짝짓기는 같은 줄에 같은 표현이 여럿이라 (corpus, 파일, 줄, 키워드, 표현, 매칭 문자열) 순서 검증 뒤 위치로 한다. 추가 필드: `grade3_share`, 교재 3분류(`real-marker` / `toc-block` / `real-marker-nomap`, 블록 수 / 대응의 실제 쪽 수 ≥ 0.8), `meta.alignment_self_check`(`--previous-basis` 의 `alignment_check.overall`·`hybrid_lines` — 정렬 오차 병기), `--school-grade-workbook`; 쓰기는 `SKR._write_text_atomic`.

### 3.8 발표면 · HWPX — FR-08·09

- `docs/semantic_grade_dashboard.js`: 브리지 절에 `meta.page_basis` 가 `real` 이면 제 문단으로 "출현은 이전 기준과 같은 실제 PDF 쪽에 놓이며 … 공유 쪽 등급 일치 N/N (100.0%) … 두 수치는 같은 쪽 모집단을 집계 단위(출현건수 vs 쪽)만 달리해 센 것이라, 차이는 집계 단위와 그에 따른 가중뿐이다" 를 넣고(출고 전 리뷰 Codex·design: "분모뿐" 은 분자·분모가 함께 바뀌므로 느슨한 표현 — 집계 단위·가중으로 고침, 일치율은 히어로와 같은 N/N (100.0%) 형식), 데이터 주는 0건인 등급 출처를 적지 않으며(NCS 는 실제 쪽 판정 N건만), 마커 없는 출현 문장은 현행. `index.html` 의 정적 `.ctn` 값은 하니스 `S5` 가 잡는 대로 갱신.
- `hwpx_results_refresh.py`: `Facts.run` 에 `page_basis` 를 읽어(`load_facts` 가 필수로 요구) 2절 도입 "총 N쪽(교재 마크다운의 쪽 표식 최댓값 합)" ↔ "총 N쪽(PDF 쪽수; 표식이 실제 쪽인 2권은 표식 기준)", 3절 "표 13 의 쪽 번호는 재세그먼트로 확인한 실제 PDF 쪽이다(1·2절의 분야별 쪽수는 마크다운 쪽 표식 최댓값)" ↔ "(1·2절의 분야별 쪽수도 PDF 쪽수)" 로 분기; `DEFAULT_OUT`/`DEFAULT_DIFF` 의 날짜를 정본 실행일에서 만든다(`…_{YYYYMMDD}_정본.hwpx`, `hwpx_results_refresh_{YYYYMMDD}.json`) — 하드코딩 20260914 제거. 옛 대조 JSON 은 `docs/03-analysis/data/` 에 그대로 두고 data README 가 계보로 적는다.
- README·CLAUDE.md: 재생성 절에 `--page-maps data/markdown/ncs_paged`, 예외 문단 수치(등급3 비율·분모), 그룹 4 문단(대응·결속·D2 목록·`real-page`), `docs/03-analysis/data/README.md` 계보 행.

### 3.9 CLI

- `semantic_keyword_recount.py --page-maps DIR`(기본 `DEFAULT_PAGE_MAPS_DIR` = `data/markdown/ncs_paged`; `run_census` 가 디렉터리 부재를 `FileNotFoundError` 로 멈춘다 — 정본은 대응 없이 만들 수 없다), `--reseg-csv PATH`(기본 `DEFAULT_RESEG_CSV` = `docs/03-analysis/data/ncs_pages_reseg.csv`). `run_census(page_maps_dir=None)` 은 라이브러리 호출(테스트·영향표)용 — 그 실행은 `page_basis` 가 `marker` 라 정본 `EXPECTED` 와 어긋난다.
- `occurrence_real_pages_impact.py --source-workbook … --ncs-root … --school-root … --page-maps … --out docs/03-analysis/data/occurrence_real_pages_impact.json`.

---

## 4. 테스트 설계

| 대상 | 테스트(`test_semantic_keyword_recount.py` `RealPageTests`) |
|---|---|
| 3.1 로딩·검증 | fixture 문서 2개(대응 있음/없음) + `pages.json`: 정상 로딩; `md` 이름 불일치 거부; 길이 불일치 거부; 값 0 거부; 대응 없고 목록에 없으면 거부; 목록 교재는 통과, 표식 결손이면 거부; `PageMapsInfo.sha256` 결정론 |
| 3.2 덧씌우기 | 블록 표식 5 인 줄이 대응으로 쪽 12 를 받는다; `page_count` 가 실제 쪽 기준; 교과서·대응 없는 문서 불변; 제외 레코드도 쪽을 받는다; 총 출현 수 불변(매칭은 블록에서) |
| 3.3 판정 | 한 블록(3쪽 폭)의 출현이 쪽별 본문으로 다른 등급을 받는다; `grade_source == "real-page"`; `existing_grades` 에 그 (교재, 쪽) 이 있어도 무시; 대응 없는 교재는 현행(`new`) |
| 3.4 결속 | fixture CSV 와 100% 일치 / 1건 불일치 시 metrics 가 `EXPECTED` 와 어긋나 `run_census` 가 쓰지 않는다 |
| 3.5 쪽수 | `pdf_pages` 가 주어지면 NCS 그룹 pages 가 그 합, D2 교재는 표식 최댓값; 교과서 불변; `meta.page_basis` |
| 3.6 manifest | `page_maps`·`reseg_agreement`·`real_page_marker_books` 기록; `summary_metrics` 키; `check_expected` 가 새 키를 본다; 같은 fixture 두 번 → 같은 해시 |
| 3.7 영향표 | fixture 로 (A)/(B) 이동 행렬이 맞는다; (A) 가 정본과 다르면 멈춘다 |
| 3.8 HWPX | `page_basis` 분기 문구 양쪽; `load_facts` 가 `page_basis` 없는 정본을 거부; 날짜 접미 |
| 하니스 | `test-dashboard-data.js`: `S3n`(쪽수 합 = reseg pdf_pages + D2 표식), `S2`(run.page_maps 존재), 브리지 문구; README/CLAUDE.md 인용(`S7`/`S8`) 은 새 수치로 |
| 커밋 산출물 | `test_committed_summary_json_matches_expected`(자동), 영향표 JSON 의 (A) 열 == 옛 정본 등급(4,378/4,614/2,525) — 계보 고정 |

---

## 5. 구현 순서 (Do)

1. `load_page_maps`·`PageMapsInfo`·`REAL_PAGE_MARKER_BOOKS`(테스트 먼저) → `apply_page_maps` → `aggregate_matches(page_maps=)`.
2. `assign_match_grades(page_maps=)` + `GRADE_SOURCES` → `reseg_agreement` → `dashboard_payload(pdf_pages=)`·`summary_payload`(page_basis) → `run_manifest`·`summary_metrics`·CLI.
3. 정본 실행: `--force` 로 측정 → `EXPECTED` 재고정(totals 불변·grades·sources·agreement·해시) → 가드 통과 실행(커밋 산출물). 결속 100% 확인.
4. `occurrence_real_pages_impact.py` + JSON.
5. 발표면: 대시보드 문구·`index.html`·README·CLAUDE.md·data README·`semantic-occurrence-grades.report.md` 브리지 표 → 하니스 통과.
6. `hwpx_results_refresh.py` 분기·날짜 → 원본에서 재생성(`…_20260915_정본.hwpx`, 대조 JSON·검토 HTML) → 테스트.
7. `TODOS.md` 2·3·1(d) 종결 → 갭 분석(`/pdca analyze`) → ship.

---

## 6. 결정 기록

| # | 결정 | 근거 |
|---|---|---|
| 1 | 매칭은 표식 블록 위에서, 쪽은 매칭 뒤 덧씌운다 | 사전 v2 의 동반어 창·총계를 바꾸지 않는다(총계 11,517 불변이 검증 가능) — 계획 §1.3 실측과 같은 방식 |
| 2 | NCS 워크북 라벨 상속 폐기(D1) | 라벨은 목차 블록이라 실제 쪽에 대응되지 않는다; 실제 쪽 판정은 이전 기준과 100% 같은 규칙 |
| 3 | 대응 없는 교재는 명시 목록(D2), 자동 판별 없음 | 자동 임계(0.8)는 새 교재에서 이질성을 다시 들일 수 있다 — 사람이 넣는 목록이 안전 |
| 4 | 변형 실행(v1·v1fix)도 대응 적용 | 영향표·연구 비교가 같은 쪽 기준이어야 의미가 있다 |
| 5 | 이전 기준 결속을 `EXPECTED` 에 고정 | "같은 규칙" 이 이 기능의 전제 — 규칙이나 대응이 바뀌면 실행이 멈춰야 한다 |
| 6 | `expression_review_impact.json` 은 그대로(블록 기준, 역사) | 사전 점검 기능의 산출물 — 다시 만들지 않고 data README 에 기준 차이를 적는다 |
| 7 | HWPX 산출물 날짜 접미를 정본 실행일에서 | 하드코딩 20260914 제거(ship 리뷰 D1 자문의 일부) |
| 8 | 목록 교재(대응 없는 2권)도 `real-page` 출처 | 표식이 실제 쪽이므로 블록 라벨 상속은 모집단을 다시 섞는다 — 계획 §4 성공 기준 1 의 첫 선택지(갭 G-2) |
| 9 | `reseg_agreement` 는 `label` 출처 쪽을 제외 | 라벨 쪽은 실제 쪽이 아니고, 그 2권은 지금 표식(실제 쪽)으로 판정된다(갭 G-3) |
| 10 | 대응을 매칭 줄 규약(`splitlines`)으로 옮겨 싣는다 | `\x0c` 가 든 1권에서 줄 번호가 밀리는 잠재 결함(갭 G-1) — 정본 수치는 바뀌지 않았고(경계 줄 출현 0건) 규약만 통일 |
| 11 | 설계 밖 추가: `AnalysisResult.run`(main 의 metrics 출력용 manifest 사본), `page is None` 레코드는 덧씌우지 않음, 표식 없는 NCS 문서는 대응 대상 아님, 2절 "주" 문단도 `page_basis` 분기, 목록 교재 표식은 1..N 이어야, `pdf_pages` 를 모르는 대응 교재는 오류, `Facts.page_basis` 별도 필드 | 갭 G-9 기록 |
| 12 | 출고 전 리뷰(2026-09-15, review army 6 + red team + Codex) 반영: `load_page_maps` 가 `--marker-correct` 변형의 대응(`marker_correct`·`moved_markers`)을 거부하고 대응이 하나도 안 읽히면 실행을 거부, manifest `real_page_marker_books` 는 실제로 대응이 없던 목록 교재의 `[{code, pages}]`(대응 없는 실행은 null — 하니스 `S3n` 이 하드코딩 239 대신 여기서 읽음), `--reseg-csv` 지문을 입력 7번째로 기록, `_to_matching_lines` 가 줄 끝 `\x0c`(조각 + 개행) 를 세는 방식으로 고침, `_page_basis`·`_grade_page_text`·`PageMapsInfo.as_manifest` 로 중복 유도 제거, `dashboard_payload` 는 `pdf_pages` 에 있는 교재를 우선(목록 교재도 대응이 생기면 PDF 쪽수), 영향표는 스캔 1회 + 덧씌우기(21.7 → 14.0 s, 산출물 동일), `DENSE_MARKER_RATIO`·`NCS_PAGED_DIR` 를 `page_utils` 로, HWPX 는 page_basis 로 갈리는 문단 셋 모두 `conditions` 기록. 레드팀 6건도 반영: 대응은 이전 기준의 마크다운 판(`meta.md_corpus_sha256`, 같은 조리법 `mapped_corpus_digest`)과 PDF 쪽수(`max(line_pages) ≤ per_book.pdf_pages`)에 묶여야 통과(`check_page_maps_against_previous_basis`), payload `corpora.*.detected_pages`(출현이 놓인 (교재, 쪽) 수 — NCS 2,492 = 영향표 `pages.real_pages`, 교과서 388)로 브리지 문구를 "같은 쪽 기준·같은 규칙이지 같은 쪽 집합은 아니다(닿은 쪽 2,492 vs 2,189, 공유 2,035 전부 일치; 집합 차이는 검출 사전, 비율 차이는 집계 단위·가중)" 로 고침(CLAUDE.md 도), HWPX 2절 "대응이 없는 N권" 은 manifest `real_page_marker_books` 수로 분기(`Facts.marker_books`, conditions), `--previous-basis` 기본값 = 추적 `reseg_summary.json`(최소 호출로 정본 실행), `main()` 은 입력 오류를 traceback 대신 한 줄로, 결과 HTML meta 줄에 "페이지 열: NCS 는 실제 PDF 쪽 · 교과서는 표식" 명시 | 수치·해시 불변(정본 재실행 가드 통과, 출력 HWPX sha 동일), 테스트 171 → 175, 하니스 72 → 79 |

---

## 버전 이력

| 버전 | 날짜 | 변경 | 작성자 |
|---|---|---|---|
| 0.1 | 2026-09-15 | 초안 | Claude (Opus 5) |
| 0.2 | 2026-09-15 | 갭 분석 Act-1 — G-1 줄 규약, G-2/G-3/G-9 결정 행 8~11, G-4 CLI 기본값, G-7 영향표 필드·원자적 쓰기, G-8 결속 안내, G-10 정렬 수치 병기 | Claude (Opus 5) |
