# NCS 교재별 등급 3 집중·편차 보강 설계 (ncs-book-concentration)

> **Summary**: 정본 payload 에 교재 단위 집계 `corpora.*.books[]` 를 넣고(정본 재실행, 2026-09-17), 그 값에서 `hwpx_methods_bridge.ConcentrationFacts` 를 파생해 기초보고서 제3장 2절에 " 5) 교재별 집중과 편차"(문단 2 · 표 12-3 집중도 · 표 12-4 상위 10권)를 3단계로 삽입하며(소결 → 6)), 대시보드(NCS)에 "교재별 현황" 표를 그린다. 손 숫자 0, 장부·감사·결정론은 2단계 규약 그대로.
>
> **Project**: SearchInMD
> **Feature**: ncs-book-concentration
> **Plan**: `docs/01-plan/features/ncs-book-concentration.plan.md` (Approved — D1 (b)·D2 (a)·D3 (b)·D4 (a)·D5 (a)·D6 (b))
> **Author**: Claude (Opus 5)
> **Date**: 2026-09-17
> **Status**: Draft
> **Level**: Starter

---

## 1. 설계 목표

1. **한 출처**: 교재별 수치는 `semantic_summary.json` 의 `corpora.*.books[]` 하나에서 나오고, 보고서·대시보드·하니스가 모두 그것을 읽는다(D1 b). 파생 집계(전용 교재 제외, 평균·중앙값, 상위 교재)는 저장하지 않고 소비자가 `books[]` 에서 계산한다 — 저장하면 두 출처가 된다.
2. **정본 규약 유지**: 재실행은 같은 입력·같은 사전이라 manifest 해시 4종과 총계·등급이 그대로여야 하고(`EXPECTED` 가드), `books[]` 의 합은 말뭉치·분야 집계와 맞아야 쓴다.
3. **2단계 규약 승계**: 삽입은 원형 복제, 표는 표 12(4열) 복제, 손댄 문단 장부·`check_untouched`·숫자 감사(`value_index` 키)·줄 배치 캐시 제거·재실행 결정론.
4. **데이터 분기 서술은 양쪽 테스트**: 전용 교재 수, 제외 후 비율 방향, 분야 과반, 0건 과반.
5. **연쇄를 명시**: 실행일 변경이 닿는 파일을 목록으로 두고(§2.4) 하니스로 확인한다.

---

## 2. 아키텍처

### 2.1 구성

```
semantic_keyword_recount.py ─ run_census ─▶ semantic_summary.json ──┬─▶ docs/semantic_recount_data.js ─▶ semantic_grade_dashboard.js (NCS 교재별 현황 절)   [D6 b]
   dashboard_payload: corpora.*.books[]  (신규)                        │
   summary_metrics/EXPECTED: books, books_digest (신규)                 ├─▶ hwpx_methods_bridge.load_concentration_facts ─▶ ConcentrationFacts ─▶ 템플릿(문단 2·표 12-3·표 12-4)
                                                                        │        └─ Facts.value_index() 에 value_pairs 합류 (숫자 감사)
                                                                        └─▶ hwpx_results_refresh.refresh_methods_bridge  (3단계: 2절 삽입·소결 6)·목차)
                                                                                 └─▶ …_20260917_정본.hwpx · hwpx_results_refresh_20260917.json · review.html
outputs/test-dashboard-data.js  S3p(books ↔ corpora/groups) · S1r/S1s(렌더 절)
```

### 2.2 데이터 흐름 (3단계 실행 순서, 기존 `refresh()` 안)

1단계(제3장 1~3절) → 2단계(5절·표 4·목차·2절 4)) → **3단계**(2절 5)·소결 6)·목차) → 줄 배치 캐시 제거 → `check_untouched` → 감사 → 쓰기. 3단계는 2단계가 `_Ledger.insert` 로 넣은 마지막 원소(표 12-2 블록의 끝 빈 문단)를 **장부에서** 받아 그 뒤에 삽입한다 — 파일에서 다시 찾지 않는다.

### 2.3 의존

- `reseg_summary.json per_book.pdf_pages`(교재 쪽수) — 이미 `run_census` 가 읽는다(`pdf_pages_from_previous_basis`).
- `page_utils.EXCEL_MAX_CHARS` 등 코드 상수는 새로 쓰지 않는다.
- 새 외부 의존 없음.

### 2.4 정본 재실행 연쇄 (D1 b) — Do 의 체크리스트

| # | 대상 | 변화 | 확인 |
|---|---|---|---|
| 1 | `docs/03-analysis/data/semantic_summary.json` · `docs/semantic_recount_data.js` | `corpora.*.books[]` 추가, `meta.run.generated_at` 2026-09-17, `git_commit` | S2, S3, `test_committed_summary_json_matches_expected` |
| 2 | `docs/keyword-analysis.html` · `NCS_키워드검색결과.html` · `교과서_키워드검색결과.html` | 같은 실행이 다시 씀(실행일·xlsx 이름 `semantic_keyword_recount_20260917.xlsx`) | S6 |
| 3 | `data/semantic_keyword_recount_20260917.xlsx` · `_report.md` (비추적) | 새 이름; 20260915 판은 남긴다 | — |
| 4 | `data/반도체 기초보고서_20260917_정본.hwpx` (비추적) | `default_out_path` 가 실행일을 따른다; 20260915 정본은 그대로 두고 `.bak` 규약은 새 이름에는 해당 없음(새 파일) | 실행 출력 |
| 5 | `docs/03-analysis/data/hwpx_results_refresh_20260917.json` | 새 추적 대조 JSON; `hwpx_results_refresh_20260915.json` 은 계보로 남김(`CommittedDiffTests` 는 최신 날짜를 고른다) | `CommittedDiffTests` |
| 6 | `docs/03-analysis/hwpx-results-refresh/review.html` | 표 12-3·12-4 추가, 실행일 | — |
| 7 | 본문 출처 문구(1단계 "2026-09-15 정본 … 사전 v2", 표 12-1/12-2 헤더의 `run_date`) | 2026-09-17 | 감사(`STRIP_BEFORE_AUDIT` 가 날짜를 벗긴다) |
| 8 | `docs/03-analysis/data/occurrence_real_pages_impact.json` | 변화 없음 — `load_bridge_facts` 는 지문·사전·총계로 결속(실행일 아님) | `test_impact_input_lineage…` |
| 9 | README(핵심 수치 날짜·재생성 절 xlsx 이름·HWPX 이름), CLAUDE.md(그룹 4·Safety 예외 문단의 "2026-09-15 canonical run" 표현), `docs/03-analysis/data/README.md`, TODOS | 날짜·파일명 갱신 | S7, S8 (숫자 불변) |
| 10 | 메모리·archive `_INDEX.md` | 새 정본 실행일 기록 | — |

수치와 해시는 변하지 않는다: 입력 지문 7종·사전 v2·대응표가 같으므로 `source/rule/detail/summary_sha256`, 총계 11,517/1,207, 등급, `reseg_agreement` 2,035/2,035 그대로 — `EXPECTED` 가드가 그것을 증명한다(`books`·`books_digest` 두 키만 새로 고정).

---

## 3. 상세 설계

### 3.1 정본 payload — `semantic_keyword_recount.py`

**`corpora.<말뭉치>.books[]`** (교재당 1행, 매칭 0건인 교재도 행을 남긴다):

```json
{"code": "LM1903060329", "title": "반도체 장비 안전관리", "group": "반도체장비", "pages": 120,
 "total": 1631, "grades": {"1": 153, "2": 698, "3": 780, "unpaged": 0}, "detected_pages": 41, "grade3_pages": 9}
```

| 필드 | 값 | 출처 |
|---|---|---|
| `code` | NCS: `_document_code(document)`; 교과서: `null` | 기존 |
| `title` | 파일 stem 에서 `\d{8}_\d{6}_` 접두, `LM\d{10}_`, `\d+v\d+_` 판 토큰을 떼고 `_` → 공백, NFC(`_book_title`); 교과서: `_dashboard_group` 의 표시명 | 신규 |
| `group` | `_dashboard_group(corpus, relative_path)` | 기존 |
| `pages` | NCS: `pdf_pages[code]`(이전 기준), 대응 없는 `REAL_PAGE_MARKER_BOOKS`·교과서: 표식 최댓값 — 지금 `pages_by_group` 이 쓰는 규칙을 교재 단위로 내리고, `groups[].pages` 는 `books[].pages` 의 합으로 바꾼다(한 정의) | 기존 규칙 이동 |
| `total`·`grades` | 그 교재의 `included` 레코드 수·`_grade_counts` | 기존 |
| `detected_pages` | `{page}` 고유 수(`page is None` 제외) | `_file_rows` 와 같은 규칙 |
| `grade3_pages` | 등급 3 레코드가 놓인 고유 쪽 수 | 신규 |

정렬: NCS 는 `code`, 교과서는 `title` — 결정적. 교과서의 `books[]` 는 `groups[]` 와 1:1(이름·총계·등급 같음) 이며 S3p 가 그것을 단언한다.

**가드(`run_census`, 쓰기 전)**: 말뭉치마다 `len(books) == documents`, `sum(total) == total`, 등급 합 == `grades`, 분야별 합 == `groups[]`(total·grades·pages·documents) — 어긋나면 ValueError(쓰지 않음).

**`summary_metrics` / `EXPECTED`**: `"books": {"NCS": 86, "교과서": 9}`, `"books_digest": _canonical_hash(books 목록 전체)` (총계가 같아도 교재 간 재배분을 잡는다 — `page_grade_digest` 와 같은 뜻). `check_expected` 의 `STRICT_GROUPS` 에 `books` 는 넣지 않는다(키는 말뭉치 2개로 고정). `test_committed_summary_json_matches_expected` 가 커밋된 JSON 에서 `books_digest` 를 다시 계산해 `EXPECTED` 와 견준다.

**크기**: 95행 × 9필드 ≈ +20 KB (64 → ≈ 85 KB). `write_dashboard_data` 는 그대로.

### 3.2 파생 사실 — `hwpx_methods_bridge.py`

```python
@dataclass(frozen=True)
class BookRow: code: str | None; title: str; group: str; pages: int; total: int; g: dict[int, int]; detected_pages: int; grade3_pages: int

@dataclass(frozen=True)
class ConcentrationFacts:
    run_date: str; total: int; grade3: int; books: int                       # summary corpora.NCS
    rows: tuple[BookRow, ...]                                                # NCS 교재 전부 (code 순)
    dedicated: tuple[BookRow, ...]                                           # D4: title 에 "안전관리" 포함 — DEDICATED_TITLE_RULE
    dedicated_total: int; dedicated_g3: int                                  # 2,238 / 965
    rest_books: int; rest_total: int; rest_g3: int                           # 84 / 9,279 / 1,537
    group_rows: tuple[GroupConcentration, ...]                               # 전용 교재가 있는 분야마다: (분야, 교재 수, total, g3, 전용 제외 교재 수/total/g3, 전용 교재의 g3 몫)
    mean_pct: float; median_pct: float; zero_books: int                     # 8.5 / 0.0 / 57 — 분모 0 교재는 제외(현재 0권)
    top: tuple[BookRow, ...]                                                 # 등급 3 내림차순(동률: total, code) 상위 TOP_BOOKS=10
```

`load_concentration_facts(summary)`:
- `corpora.NCS.books` 가 없으면 "정본을 2026-09-17 이후 스크립트로 다시 만드십시오" 힌트로 정지(`_get` hint).
- 가드: `len(books) == corpora.NCS.documents`, `sum(total) == corpora.NCS.total`, `sum(g3) == corpora.NCS.grades.3`, 분야별 합 == `groups[]`; **전용 집합 == `DEDICATED_EXPECTED_CODES = ("LM1903060329", "LM1903060411")`** (D4: 규칙이 다른 집합을 내면 정지 — 문장 수사가 두 권 전제).
- `value_pairs()`: 총계·등급 3·교재 수, 전용 합계와 비율(`pct(dedicated_g3, grade3)` 38.6%, `pct(dedicated_total, total)` 19.4%, `pct(dedicated_g3, dedicated_total)` 43.1%), 제외 집계와 비율, 분야 행 값(`pct` 포함, 전용 교재 몫 74.1%), 평균·중앙값(`f"{x:.1f}%"`), 0건 교재 수·비율, 상위 10권의 total·g3·pct, 표 12-4 의 10권 합과 몫 — 키 접두 `books.*`.

임계: `CONCENTRATION_SAME_PP = BRIDGE_SAME_PP`(0.5pp — 제외 후 비율이 "같다" 인 폭), 과반 = `> 50.0%`.

### 3.3 템플릿 — `concentration_paragraphs(f) -> list[Piece]`

순서: `B, H(" 5) 교재별 집중과 편차"), B, P1, B, C(표 12-3), T(표 12-3), N, B, C(표 12-4), T(표 12-4), N, B, P2, B` — 2단계 `bridge_paragraphs` 와 같은 골격이라 원형 `protos2` 를 그대로 쓴다.

**P1 (집중)**: "NCS 등급 3 출현 {g3}건은 {books}권에 고르게 있지 않다. 제목에 '안전관리'를 둔 전용 교재 {두} 권({제목 나열})이 출현 {2,238}건(전체의 {19.4%})에 등급 3 {965}건({38.6%})을 차지하며, 두 권을 제외한 {84}권의 등급 3 비율은 {21.7%}에서 {16.6%}로 {내려간다}(표 12-3). {분야 문장} 이 제외 집계는 자료를 버린 결과가 아니라 집중도를 보기 위한 보조 비교이다."
- 분야 문장(전용 교재가 있는 분야마다, 몫이 큰 순): 몫 > 50% → "{반도체장비} 분야에서는 {반도체 장비 안전관리} 한 권의 등급 3 {780}건이 분야 등급 3 {1,052}건의 {74.1%}로 과반이며, 이 교재를 제외하면 분야 비율은 {32.5%}에서 {16.9%}가 된다."; 몫 ≤ 50% → "…{14.8%}이며, 제외하면 {21.4%}에서 {20.3%}가 된다." (과반 수사 없음).
- 분기 `conditions`: `dedicated_count`(수사 `KOREAN_COUNT`), `rest_rate_direction`(내려간다/올라간다/같다), `group_majority`{분야: bool}.

**표 12-3** "표 12-3. NCS 교재별 등급 3 집중" — 헤더 `["구분", "교재 수", "출현 (등급 3)", "등급 3 비율"]`, 행: `NCS 전체 | 86 | 11,517 (2,502) | 21.7%` / `안전관리 전용 교재 | 2 | 2,238 (965) | 43.1%` / `전용 교재 제외 | 84 | 9,279 (1,537) | 16.6%` / 분야마다 `{분야} 분야 | 19 | 3,239 (1,052) | 32.5%` 와 `{분야} 분야(전용 제외) | 18 | 1,608 (272) | 16.9%` → 현재 7행. 주: "주: 단위: 건. 등급 3 비율의 분모는 각 행의 출현. 안전관리 전용 교재는 제목에 '안전관리'를 포함하는 {두} 권({제목 나열})이다."

**표 12-4** "표 12-4. NCS 등급 3 출현 상위 10권" — 헤더 `["교재 (분야)", "출현", "등급 3", "등급 3 비율"]`, 행 10개 `{title} ({분야 약칭})` — 분야 약칭은 `NCS_GROUP_TO_AREA`. 주: "주: 단위: 건. 상위 10권의 등급 3 합은 {N}건으로 NCS 등급 3의 {NN.N%}이다."

**P2 (분포)**: "교재 단위로 보면 등급 3 비율의 {86}권 평균은 {8.5%}, 중앙값은 {0.0%}이고, 등급 3 출현이 한 건도 없는 교재가 {57}권({66.3%})으로 {과반이다|과반에 못 미친다}(표 12-4는 상위 {10}권). 합산 {21.7%}는 소수 교재에 몰린 값이므로, 본 보고서는 합산값과 교재별 분포를 함께 제시한다. 전문 안전관리 교재의 내용을 개별 작업 교재의 해당 단원과 어떻게 연결할지는 후속 검토 대상이며, 이 수치만으로 교재 사이의 교육 전이가 이루어진다고 볼 수는 없다." — `conditions.zero_majority`.

상수: `CONCENTRATION_HEADING = " 5) 교재별 집중과 편차"`, `CONCLUSION_HEADING_NEW = " 6) 소결"`(2단계 상수 값 변경 — 목차·본문 둘 다), `TABLE12_3_CAPTION/LABEL`, `TABLE12_4_CAPTION/LABEL`, `TOP_BOOKS = 10`, `DEDICATED_TITLE_RULE = "안전관리"`.

### 3.4 3단계 삽입 — `hwpx_results_refresh.py`

- `_Ledger.insert` 가 `self.last_inserted = elements` 를 남긴다(반환값은 그대로 records).
- `refresh_methods_bridge` 2절 부분: `records = L.insert(ref, bridge_pieces, protos2, "bridge")` 직후 `ref3 = L.last_inserted[-1]`(블록 끝 빈 문단) → `records3 = L.insert(ref3, MB.concentration_paragraphs(facts), protos2, "concentration")` → `out["concentration"] = {"inserted": records3, "tables": [12-3, 12-4 (rows·cols·table_id)], "conditions": …, "dedicated": [codes]}`, `out["tables"] += …`, `out["review_tables"] += [("concentration", 표 12-3…), ("concentration", 표 12-4…)]`.
- 소결 재번호: 기존 `L.rewrite(concl, MB.CONCLUSION_HEADING_NEW, …)` 가 " 6) 소결" 을 쓴다(상수 변경); `out["bridge"]["renumbered"] = {"4) 소결": "6) 소결"}`.
- 목차: 2절 블록에서 " 4) 소결" → bridge heading 재작성(기존) 뒤 삽입 목록을 `[H(CONCENTRATION_HEADING), H(CONCLUSION_HEADING_NEW)]` 로 — `out["bridge"]["toc"] = {"rewritten": 1, "inserted": 2}`; `audit_texts` 에 두 제목 추가.
- `Facts`: `concentration: MB.ConcentrationFacts` 필드 추가, `load_facts` 가 `MB.load_concentration_facts(summary)` 로 채우고 `value_index` 에 `value_pairs` 합류. `SECTION_LABEL["concentration"] = "교재별 집중"`(검토 HTML 절 이름). `write_text_review` 절 순서에 `concentration` 추가.
- 표 원형: `protos2["T"]`(표 12, 4열) — 표 12-3·12-4 모두 4열이라 `resize_table` 의 행 조정만 쓴다(열 능력 추가 없음).
- 사전 점검: 이미 3단계 산출물(" 5) 교재별 집중과 편차" 가 있는 파일)을 입력으로 주면 기존 "이미 2단계 산출물" 검사에 문구를 더해 거부.

### 3.5 숫자 감사 — FR-06·FR-08

- 새 문단·셀의 숫자는 `value_pairs` 로 전부 키가 생긴다: 교재 수(86·84·19·18·2·10·57), 출현·등급 3(총계·전용·제외·분야·상위 10권 각 값), 비율(21.7·43.1·16.6·32.5·16.9·74.1·19.4·38.6·8.5·0.0·66.3 + 상위 10권 비율), 표 12-4 의 10권 합·몫.
- `STRIP_BEFORE_AUDIT` 는 그대로(`표 12-3`·`12-4` 는 `(?:표|그림)\s*\d+(?:-\d+)?` 로 벗겨진다; " 5) "·" 6) " 는 단일 자릿수 목록 번호).
- 교재 제목 안의 숫자(예: "반도체 기초기술 1") 는 NCS 상위 10권에는 없어야 한다 — 있으면 `ALLOWED_TOKENS` 가 아니라 제목 토큰으로 처리하는 규칙이 필요: `audited_numbers` 는 제목을 모른다 → 표 12-4 셀 텍스트에서 제목 부분은 감사 전 `f.concentration.titles` 로 제거하는 `STRIP` 확장(제목 문자열 리터럴 제거) 을 둔다. 현재 NCS 상위 10권 제목에 숫자 없음(실측 필요 — Do 에서 확인, 있으면 규칙 적용).

### 3.6 대시보드 — `docs/semantic_grade_dashboard.js` (D6 b)

- `books(name)`: `name !== 'NCS'` → `''`. NCS: `<section><h2>교재별 현황</h2>` + 리드 문단(`books[]` 에서 JS 로 계산: 등급 3 0건 교재 수/비율, 제목에 '안전관리' 를 포함하는 교재의 등급 3 몫 — 규칙은 파이썬과 같은 `'안전관리'` 리터럴) + `.card > .scroll-x[tabindex=0][role=region][aria-label]` 표: 교재 / 분야 / 쪽수 / 출현 / 등급1 / 등급2 / 등급3 / 등급3 비율 / 검출 쪽, **등급 3 내림차순**(동률 출현), 86행 전부. 글자 색은 `--fg-*` 규칙, 막대 없음(숫자만).
- `render()` 에서 "NCS 영역별 현황" 절 뒤에 `books(activeCorpus)` 를 붙인다. `insights()` 4 번 문단에 한 문장(등급 3 0건 교재 수) 추가는 하지 않는다 — 리드 문단이 담당.
- `docs/index.html` 정적 부분은 손대지 않는다(`.ctn` 은 renderer 가 그림).

### 3.7 하니스 — `outputs/test-dashboard-data.js`

- `S3p` books ↔ corpora: 말뭉치마다 `books.length === documents`, total·등급 합, 분야별 합 == `groups[]`(total·grades·pages·documents), NCS 모든 행 `code` `/^LM\d{10}$/`·`title`·`pages > 0`, 교과서 `books[]` ≡ `groups[]`(이름·total·grades·pages), `grade3_pages <= detected_pages <= pages`, 본문 텍스트·`/Users/` 없음(`title` 길이 ≤ 40).
- `S1r` NCS `.ctn` 에 "교재별 현황", 등급 3 최다 교재 제목, `0건 교재 N권` 문구(Node 에서 books 로 재계산한 값); `S1s` 교과서 `.ctn` 에 "교재별 현황" 없음.
- `S6` 실행일·xlsx 이름 검사가 있으면 새 값으로.
- README/CLAUDE.md 인용 단언 수는 하니스 출력으로 갱신(S9/R17).

### 3.8 대조 JSON · 검토 HTML

`diff["concentration"] = {"inserted": [...], "tables": [{"section": "concentration", "caption": "표 12-3.", "rows": 8, "cols": 4, "table_id"}, {"표 12-4.", 11, 4}], "conditions": {...}, "dedicated": ["LM1903060329", "LM1903060411"]}`; `diff["bridge"]["toc"] = {"rewritten": 1, "inserted": 2}`, `diff["bridge"]["renumbered"] = {"4) 소결": "6) 소결"}`. `review.html` 에 두 표(헤더 행 포함). 본문 텍스트 없음(교재 제목은 파일명 유래).

### 3.9 문서·데이터 계보

- CLAUDE.md 그룹 4: `semantic_keyword_recount.py` 항목에 `corpora.*.books[]`(필드·규칙·`books_digest`), `hwpx_results_refresh.py` 항목에 3단계(교재별 집중, 표 12-3/12-4, 소결 6), 대시보드 항목에 교재별 절; Testing/Test Coverage 갱신; "2026-09-15 canonical run" 표현은 "2026-09-17 정본 실행(수치 동일)" 로.
- README: 핵심 수치 문단(정본 실행일), 재생성 절(xlsx 이름·HWPX 이름), 교재별 집중 한 문장.
- `docs/03-analysis/data/README.md`: `semantic_summary.json` 행에 `books[]`, 대조 JSON 행 `hwpx_results_refresh_20260917.json`(20260915 는 계보).
- TODOS: 후속 1 닫기, 2(B2)는 `books[].pages` 를 가리키도록, 5 한글 확인에 표 12-3/12-4 추가.

---

## 4. 테스트 설계

| 파일 | 테스트 | 확인 |
|---|---|---|
| `test_semantic_keyword_recount.py` `OutputTests`/`RealPageTests` | `test_payload_books_rows_and_sums` | fixture 문서(매칭 있음/없음)의 `books[]` 필드·정렬·`groups[].pages == Σ books.pages`·합 불변식; `_book_title` 4형(접두·판 토큰·교과서 표시명) |
| 〃 | `test_metrics_and_expected_pin_books` | `summary_metrics` 의 `books`·`books_digest`, `EXPECTED` 키 존재, `check_expected` 가 교재 수 불일치를 잡음 |
| 〃 | `test_run_census_refuses_book_sum_mismatch` | 가드(합 어긋남 → 쓰지 않음) — payload 를 몽키패치해 재현 |
| 〃 `test_committed_summary_json_matches_expected` | 확장 | 커밋된 JSON 에서 `books_digest` 재계산 == `EXPECTED` |
| `test_hwpx_methods_bridge.py` `ConcentrationFactsTests` | 정본 값(86·2권·965·38.6%·16.6%·74.1%·8.5/0.0/57·상위 10권), 가드(교재 합·수·분야 합·전용 집합 불일치·`books` 없음 힌트) | |
| 〃 `ConcentrationTemplateTests` | P1/P2/표 12-3/12-4/주의 문구·키; 분기 양쪽(전용 1권·3권 수사, 제외 후 올라감·같음, 분야 몫 ≤ 50%, 0건 과반 미만) — `with_concentration(f, …)` 도우미 | |
| 〃 `Stage2EndToEndTests` 확장 | 3단계: 2절에 " 5) 교재별 집중과 편차"·표 12-3·12-4·" 6) 소결"(본문·목차 각 1), 표 id 유일, `diff["concentration"]`, 감사 미일치 0, 손대지 않은 문단 불변, 재실행 결정론, 캐시 제거 포함 | fixture 의 `DEFAULT_SUMMARY` 가 `books[]` 를 가진다(정본 재실행 뒤) |
| `test_hwpx_results_refresh.py` `CommittedDiffTests` | `concentration` 블록·표 2개·`renumbered` 6)·toc inserted 2, 파일명 20260917 | |
| `outputs/test-dashboard-data.js` | S3p·S1r·S1s | §3.7 |

커버리지 목표 ≥ 80%(변경 문장 기준).

---

## 5. 구현 순서 (Do, TDD)

1. `semantic_keyword_recount.py`: `_book_title` → `books[]`(pages 규칙 이동) → 가드 → `summary_metrics`/`EXPECTED`(`books` 고정, `books_digest` 는 실행 뒤 값 기입) — 테스트 RED→GREEN.
2. 정본 재실행(README 명령, `--xlsx-out …_20260917.xlsx --report-out …_20260917_report.md`): 첫 실행은 `books_digest` 가 `None`(미고정)이라 통과 → 값을 `EXPECTED` 에 적고 다시 실행해 가드 통과 확인(2026-09-14 규약). 연쇄 산출물 커밋 단위 분리.
3. 하니스 S3p·S1r/S1s·S6 조정 → 79 → N 갱신(README·CLAUDE.md 인용 수는 출력 복사).
4. `hwpx_methods_bridge.py`: `ConcentrationFacts`·`load_concentration_facts`·템플릿·상수(" 6) 소결") — 테스트 RED→GREEN.
5. `hwpx_results_refresh.py`: `Facts.concentration`, `_Ledger.last_inserted`, 3단계 삽입·목차·재번호·검토 HTML·대조 JSON — E2E RED→GREEN; 실문서 실행 → `…_20260917_정본.hwpx`·`hwpx_results_refresh_20260917.json`·`review.html`; 재실행 동일 확인.
6. 대시보드 renderer 절 + 하니스.
7. 문서(CLAUDE·README·data README·TODOS)·Polaris 확인·`/pdca analyze`.

---

## 6. 결정 기록

| # | 결정 | 근거 |
|---|---|---|
| D1 (b) | `books[]` 를 정본 payload 에 | 한 출처; 대시보드가 같은 파일을 읽는다. 연쇄는 §2.4 로 관리 |
| D2 (a) | 2절 신설 " 5) 교재별 집중과 편차" | 4) 뒤가 "집계 기준" 다음의 자연스러운 자리 |
| D3 (b) | 표 12-3 + 표 12-4 | 집중도(집합 비교)와 개별 교재(상위 10권)를 따로 |
| D4 (a) | 제목 "안전관리" 규칙 + 기대 집합 고정 | 규칙은 설명 가능, 집합 고정은 수사(두 권) 보호 |
| D5 (a) | 교과서는 JSON 행만 | 교과서 `groups[]` 가 이미 교재별; 문안은 제안 C |
| D6 (b) | NCS 교재별 표(차트 없음) | 표는 `books[]` 그대로, 차트는 토큰·접근성 검토가 더 필요 |
| 설계 | 파생 집계는 저장하지 않는다 | 저장하면 `books[]` 와 두 출처; 소비자(파이썬·JS)가 같은 규칙으로 계산, 하니스가 대조 |
| 설계 | 표 12-3·12-4 모두 4열 | 표 12 원형 복제(열 능력 추가 없음) — 표 12-4 는 "교재 (분야)" 한 셀 |
| 설계 | `_Ledger.last_inserted` | 3단계가 2단계 원소를 장부로 받는다(파일 재탐지 금지 규약) |

---

## 버전 이력

| 버전 | 날짜 | 내용 | 작성 |
|---|---|---|---|
| 1.0 | 2026-09-17 | 초안 — D1~D6 결정 반영 설계 | Claude (Opus 5) |
