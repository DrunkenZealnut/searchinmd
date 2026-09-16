# HWPX 보고서 제2장 5절·제3장 2절 4) 갱신 설계

> **Summary**: `hwpx_results_refresh.py` 에 **2단계**를 붙인다. 1단계(제3장 1~3절)가 끝난 같은 XML 트리에서 (A) 제2장 5절을 소제목 1)~6) + 표 5·6 으로 다시 쓰고 목차·표 4 를 맞추며, (B3) 제3장 2절에 " 4) 집계 기준의 변경과 이전 결과와의 관계"(문단 2·표 12-1·12-2)를 넣고 소결을 5)로 민다. 사실(숫자)은 새 모듈 `hwpx_methods_bridge.py` 의 `MethodsFacts`·`BridgeFacts` 가 추적 JSON/CSV 8종에서 읽고, 문장은 같은 모듈의 템플릿이 만든다. 새 XML 능력은 문단 복제·삽입·삭제와 표 복제(고유 id)뿐이고, 행 늘리기·셀 채우기·숫자 감사·ZIP 재작성은 1단계 것을 쓴다. 불변 검사는 순번이 아니라 **손댄 원소 집합**으로 한다(삽입·삭제가 있으므로). 출력은 같은 이름, 기존 파일은 `.bak` 로 보존(D1).
>
> **Project**: SearchInMD
> **Feature**: hwpx-methods-bridge-refresh
> **Plan**: `hwpx-methods-bridge-refresh.plan.md` (Approved — D1~D6 모두 (a))
> **Author**: Claude (Opus 5)
> **Date**: 2026-09-16
> **Status**: Implemented (Do 2026-09-16, Check 98.2% → Act-1 100%)

---

## 1. 설계 목표

1. **숫자는 전부 추적 파일에서.** 방법론·연결 소절의 숫자 40여 개가 모두 `Facts.value_index()` 를 거쳐 나오고, 그래서 `audit_numbers` 의 허용 집합에 손으로 넣는 숫자가 없다. JSON 에 없는 값은 문장에서 뺀다(D3).
2. **한 번의 실행.** 원본(2026-09-11) → 1단계 → 2단계 → `…_20260915_정본.hwpx`. 정본 파일은 입력이 될 수 없다(문단 탐지가 원본 첫 단어에 묶임 — 1단계 규약 유지).
3. **최소 침습.** 손대는 문단은 목록으로 고정하고(§3.4·§3.6), 그 밖의 모든 최상위 문단은 구조 동일, 다른 ZIP 항목은 바이트 동일.
4. **서식 승계.** 삽입 문단은 같은 문서의 원형 문단을 깊은 복사한다(`paraPrIDRef`·`styleIDRef`·`charPrIDRef`). 표는 표 12 를 복제한다.
5. **거짓 문장 방지.** 데이터에 묶인 서술(늘었다/줄었다/거의 같다, 모두 일치, 보수적 판정, 몫이 커진다)은 분기하고 양쪽을 테스트한다.

## 2. 아키텍처

```
추적 파일                                              hwpx_methods_bridge.py                    hwpx_results_refresh.py
semantic_summary.json ──(corpora·meta.run·previous_basis)─┐                                         refresh()
occurrence_real_pages_impact.json ─(grades·transition·   ├─▶ MethodsFacts / BridgeFacts ──┐          ├─ 1단계 (기존) 제3장 1~3절
   pages.real_page_grades·pages.교과서 ← FR-12 확장)      │      value_index() 기여          │          └─ 2단계 refresh_methods_bridge(root, facts, diff, text_pairs)
reseg_summary.json ──(pages·page_g·meta.rows·alignment)──┤                                  │                ├─ 표 4 셀·캡션            (제2장 1절)
ncs_pages_reseg.csv ──(구라벨 → 표식 하나의 최대 쪽 폭)──┤                                  │                ├─ 목차 5절 8→6 · 2절 4)/5)
regrade_impact.json ──(rule.safety_min/action_min·       ├─ 템플릿: methods_*(), bridge_*() ─┤                ├─ 5절: 표 5·6, 삭제 6, 삽입 20, 재작성 2
   reproduction)                                         │   toc_*()                         │                ├─ 2절: 삽입 15, 소결 4)→5), 소결 문장
recoding_scores.json ──(population·C/B baseline)─────────┤                                  ▼                └─ 숫자 감사(5절+표 4+제3장 재탐지) · 불변 검사(손댄 집합)
expression_review_{key,scores,impact}.json ──────────────┤                       Facts(ncs, school, cases, run, page_basis,
summary.json ──(ncs.truncated_pages)─────────────────────┘                              methods, bridge)
page_utils.EXCEL_MAX_CHARS                                                                     │
                                                                                               ▼
                       data/반도체 기초보고서_20260915_정본.hwpx (+ .bak) · docs/03-analysis/data/hwpx_results_refresh_20260915.json
                       docs/03-analysis/hwpx-results-refresh/review.html (표 4·5·6·12-1·12-2 추가) · data/hwpx-results-refresh/review_text.html
```

- 모듈 분리 이유: `hwpx_results_refresh.py` 는 이미 1,267줄이다. 사실 적재·템플릿(≈450줄)은 새 모듈에, XML 일반 능력(복제·삽입·삭제·복제 표·손댄 집합 검사, ≈120줄)과 2단계 조립(≈150줄)은 기존 스크립트에 둔다. 새 모듈은 `hwpx_results_refresh` 의 `fmt`·`pct`·`Facts` 를 import 하지 않고 순수 함수로 두어 순환 import 를 피한다 — `Facts` 가 `methods`·`bridge` 필드로 새 모듈의 dataclass 를 품고, `value_index()` 가 `methods.value_pairs()`·`bridge.value_pairs()` 를 합친다.
- stdlib 만. openpyxl 불필요(D2(a): xlsx 를 읽지 않는다).

## 3. 상세 설계

### 3.1 데이터 출처 확장 — FR-12 (`occurrence_real_pages_impact.py`)

`compute_impact` 의 `pages` 블록에 두 필드를 더한다.

```python
real_page_grades = Counter()                       # NCS: (교재, 실제 쪽) → 그 쪽 등급 (등급은 쪽 속성 — 같은 쪽 출현이 다른 등급을 들고 오면 `_fold_page_grade` 가 ValueError 로 멈춘다, 최솟값 병합 없음 — ship 리뷰 반영)
school_pages: dict[tuple, int] = {}                # 교과서: (교재, 쪽) → 그 쪽 등급 (충돌은 같은 ValueError; page None 은 제외 — 정본은 0건)
...
"pages": {"block_pages": ..., "real_pages": ..., "real_page_grades": {"1": 1825, "2": 524, "3": 143},
          "교과서": {"detected_pages": 388, "page_grades": {"1": 335, "2": 45, "3": 8}},
          "block_width_of_occurrences": {...}}
```

- 불변식(스크립트 안에서 검사): `sum(real_page_grades) == real_pages`, `sum(교과서.page_grades) == 교과서.detected_pages`.
- 재실행: `python3.13 occurrence_real_pages_impact.py` (README 의 정본 명령; `BLOCK_BASIS_V2` 가드 통과). `meta.git.commit` 만 바뀐다.
- 테스트: `ImpactScriptTests` 에 fixture 실행 후 두 합계 불변식과 키 존재; `outputs/test-dashboard-data.js` `S3o` 에 `Object.values(I.pages.real_page_grades)` 합 `=== I.pages.real_pages` 와 `I.pages['교과서'].detected_pages === T.detected_pages` 를 **같은 check 에** 덧붙인다(assertion 수 79 유지 — README/CLAUDE.md 인용 수 변경 없음).
- `CorpusFacts` 에 `detected_pages: int` 추가(`corpora.*.detected_pages`; 없으면 `ValueError` — 2026-09-14 이후 정본 요구).

### 3.2 사실 — `hwpx_methods_bridge.py`

```python
@dataclass(frozen=True)
class MethodsFacts:            # 제2장 5절 (출처 키 → 정본 값)
    dedup_books: int           # summary meta.run.dedup (len)                       1
    keyword_names: tuple[str]  # summary keywords[].name                              30개
    review_targets: int        # expression_review_key.targets (len)                 22
    review_per_expression: int # expression_review_key.per_expression                30
    review_items: int          # expression_review_key.items (len)                   618
    review_n: int; review_agree: int; review_kappa: float; review_disagreements: int   # scores.overall: n 612, n−disagreements 595, kappa 0.9648, 17
    review_alpha: float; review_floor: float                                         # scores.meta.alpha 0.05 → "95%", floor 0.8
    review_coders: tuple[str, str]                                                   # scores.meta.coders A/B → 계열 라벨(§3.5)
    held: tuple[str]; conditional: tuple[str]                                        # impact.meta.v2_overrides (held / conditional, 키워드:표현의 표현 부분)
    totals_v1fix: dict[str, int]; totals_v2: dict[str, int]                          # expression_review_impact.totals — 12,310/1,272 → 11,517/1,207
    max_label_width: int       # ncs_pages_reseg.csv: (교재, 구라벨) 별 실제 쪽 수의 최댓값   58 (구라벨은 ";" 로 여러 라벨을 잇는다)
    truncated_pages: int       # summary.json ncs.truncated_pages                     16
    excel_max_chars: int       # page_utils.EXCEL_MAX_CHARS                           32,767
    page_maps: int             # summary meta.run.page_maps.files                     84
    align_books: int; align_lines: int; align_exact: int; align_near: int             # reseg alignment_check.books/overall — 23 · 21,711 · 18,142 · 20,613
    safety_min: int; action_min: int                                                 # regrade_impact.rule                                6 · 5
    repro_pages: int; repro_agree: int                                               # regrade_impact.reproduction total/agree            1,847 · 1,839
    sample_pages: int; census_pages: int; recall_pages: int; recall_pool: int         # recoding_scores.population.strata — 538 · 238(44+85+109) · 300 · 1,609
    precision: tuple[float, float]; recall: tuple[float, float]                       # recoding_scores C/B .variants.baseline.precision/recall — (0.802, 0.843) · (0.132, 0.208)
    inputs: int                # summary meta.run.inputs (len)                        7
    repo_url: str = "github.com/DrunkenZealnut/searchinmd"                           # 숫자 없음 — 상수

@dataclass(frozen=True)
class BridgeFacts:             # 제3장 2절 4)
    run_date: str              # summary meta.run.generated_at[:10]                   2026-09-15
    total: int                 # impact.totals.NCS                                    11,517
    block_grades: dict[int,int]; real_grades: dict[int,int]                          # impact.grades.block/real.NCS — 4,378/4,614/2,525 · 3,788/5,227/2,502
    block_pages: int; real_pages: int                                                 # impact.pages — 1,785 · 2,492
    moved: int; unchanged: int; matrix: dict[str,int]                                # impact.transition — 4,016 · 7,501 · 6종
    groups: dict[str, tuple[int,int]]                                                # impact.groups[*].block/real 등급 3 — 개발 236→122 …
    existing_occurrences: int; existing_kept_pct: float                              # impact.by_source.existing — 6,292 · 52.8
    real_page_grades: dict[int,int]                                                  # impact.pages.real_page_grades — 1,825/524/143
    school_detected: int; school_page_grades: dict[int,int]                          # impact.pages.교과서 — 388 · 335/45/8
    prev_date: str; prev_pages: int; prev_page_g: dict[int,int]                      # summary meta.previous_basis — 2026-09-06 · 2,189 · 1,519/525/145 (reseg_summary.pages/page_g 와 같아야 한다 — 다르면 ValueError)
    prev_rows: int             # reseg_summary meta.rows                              7,769
    shared_pages: int; shared_agree: int                                              # summary meta.run.reseg_agreement — 2,035 · 2,035
```

- `load_methods_facts(paths)` / `load_bridge_facts(paths)` 는 경로 묶음(`MethodsPaths` dataclass, 기본값은 `docs/03-analysis/data/…`)을 받고, 키가 없으면 어느 파일의 어느 키인지 말하는 `ValueError`. `load_facts()` 가 둘을 호출해 `Facts(methods=…, bridge=…)` 를 채운다(새 kwargs 는 기본값이 있어 기존 호출부·테스트는 그대로).
- 정합 가드(적재 시): `impact.totals.NCS == corpora.NCS.total`, `impact.grades.real.NCS == corpora.NCS.grades`, `impact.pages.real_pages == corpora.NCS.detected_pages`, `previous_basis.pages/page_g == reseg_summary.pages/page_g`, `sum(real_page_grades) == real_pages`, `impact.meta.inputs.page_maps.sha256 == run.page_maps.sha256` — 하나라도 어긋나면 멈춘다(계보가 다른 파일을 섞지 않는다).
- `value_pairs()` — `(값 문자열, 키 경로)` 목록. 정수는 `fmt`(콤마), 비율은 `pct`(소수 1자리 %), 다음 파생값도 낸다: 정밀도·재현율의 반올림 정수 `round(100*p)` (80·84·13·21), 일치율 `pct(agree, n)` 97.2%, `f"{kappa:.3f}"` 0.965, `str(round(100*(1-alpha)))` 95, `str(floor)` 0.8, 정렬 정확 `pct(exact, lines)` 83.6% · `pct(near, lines)` 94.9% · `pct(lines-near, lines)` 5.1%, 재현 `pct(agree, total)` 99.6%, 임계 파생 `safety_min-1` 5 · `action_min-1` 4, 등급 차이 `real-block` (−590 → "590", 613, 23), 비율 `pct(g, total)` 양 기준, `pct(moved, total)` 34.9%, 쪽 비율 `pct(page_g[g], pages)` 양 기준, `pct(shared_agree, shared_pages)` 100.0%, 등급 3 출현 비율 `pct(2502, 11517)`.

### 3.3 XML 능력 추가 — `hwpx_results_refresh.py`

| 함수 | 동작 |
|---|---|
| `clone_paragraph(proto, text) -> Element` | `copy.deepcopy(proto)` 뒤 `set_text` (원형이 빈 문단이면 `text=""` 허용 — 빈 run 에 `hp:t` 를 만들지 않고 그대로 둔다) |
| `insert_after(root, ref, elements)` | `root` 의 자식 순서에서 `ref` 다음에 순서대로 삽입(`list(root).index(ref)`) |
| `remove_paragraphs(root, elements)` | 최상위 `hp:p` 제거 — 없으면 `ValueError` |
| `next_object_id(root)` | 모든 `hp:tbl`·`hp:pic` 의 `id` 최댓값 + 1, `zOrder` 도 같은 방식 — 문서에서 결정적 |
| `clone_table_paragraph(proto_p, rows, first_data_row, header, ids)` | 표를 담은 문단을 깊은 복사 → `hp:tbl` 의 `id`·`zOrder` 를 새 값으로 → `resize_table` → `fill_table`; 문단 안 글 run 은 비운다 |
| `locate_range(root, start_text, end_text, occurrence=1)` | 제목 텍스트의 n번째 일치(`occurrence=0` 은 목차) 부터 다음 제목까지 `Section` — 5절: ("5. 키워드 기반 문서 분류·분석 방법론", "제3장 연구 결과", 1) |
| `locate_toc_block(root, entry_prefix, next_prefix)` | 최상위 문단 중 `entry_prefix` 로 시작하는 **첫** 문단(목차 사본)부터 `next_prefix` 첫 문단 앞까지 — 5절 목차: ("5. 키워드 기반", "제3장"), 2절 목차: ("2. NCS", "3. NCS") |
| `set_cell_paragraph(tc, prefix, text)` | 셀 안 여러 문단 중 `prefix` 로 시작하는 하나의 글만 바꾼다(표 4 의 "반도체제조 14종") — 0·2+ 개면 `ValueError` |
| 손댄 집합 검사 | `refresh()` 시작 시 `snapshot = {id(p): ET.tostring(p) for p in tops}`; 모든 편집 경로가 `touched.add(id(p))`, 삽입은 `inserted.add(id(new))`; 끝에 `[snapshot[id(p)] for p in new_tops if id(p) not in touched|inserted] == [snapshot[id(p)] for p in tops if id(p) not in touched and p not in removed]` 이고 삭제된 것은 `removed` 에만 있어야 한다. 1단계의 순번 기반 검사(`inside` 범위)를 이 검사로 대체한다 |

`set_text` 의 `ctrl` 혼합 문단 한계(각주 run 이 있는 문단은 글 run 만 갈아끼워 각주 위치가 끝으로 밀린다)는 그대로 두고, 그런 문단에는 쓰지 않는다 — 소결 마지막 문단(`#00551`, `ctrl` run 있음)에 문장을 **붙이지 않고** 새 문단을 뒤에 삽입하는 이유(§3.6).

### 3.4 A — 제2장 갱신 절차 (실행 순서)

원형 문단(같은 문서에서 복제):

| 이름 | 원형 | 근거 |
|---|---|---|
| `H` 소제목 | 제3장 2절 " 1) 사고, 부상, 질병 관련 30개 키워드 분석" (`#00441`, paraPr 10 · charPr 13) | 5절에는 소제목이 없다 |
| `P` 본문 | 5절 `#00334`(paraPr 24 · charPr 13) — 삭제 전에 복제 | 5절 본문 서식 |
| `B` 빈 문단 | 5절 `#00317`(paraPr 25 · charPr 22, `hp:t` 없음) | 5절 문단 간격 |
| `C` 캡션 / `N` 주 / `T` 표 문단 | 표 12 캡션 `#00536` / 주 `#00538` / 표 문단 `#00537` | B3 에서 사용 |

1. **표 4** (`locate_range("1. 국내 반도체고등학교 교과서와 한국산업인력공단 NCS 교과서 분석", "2. 해외 기술 고등학교 교과서 비교·분석", 1)`): 캡션 `find_paragraph(…, "표 4.")` → `"표 4. 국내 반도체고등학교 교과서({school.documents}종)와 한국산업인력공단 NCS 교과서({ncs.documents}종)"`; 표 `find_table_after_caption` → 둘째 열·셋째 행 셀에서 `set_cell_paragraph(tc, "반도체개발", f"반도체개발 {n}종")` … 4개(`corpora.NCS.groups[].documents`, 이름 순서는 표의 문단 순서). 셀 첫 문단("한국산업인력공단 NCS 교과서")은 그대로.
2. **목차 5절** (`locate_toc_block("5. 키워드 기반", "제3장")`): 블록 안 `^\s*\d\)\s` 문단 8개 → 앞 6개를 `toc_methods_entries()` 로 `set_text`, 뒤 2개 `remove_paragraphs`. 8개가 아니면 `ValueError`(문서가 바뀐 것).
3. **5절 본문** (`locate_range(…, 1)`, 끝은 "제3장 연구 결과" 두 번째 일치):
   - 표 5: `find_table_after_caption(sec, "표 5.")` → `resize_table(tbl, 1, 7)` → `fill_table(tbl, methods_table5_rows(f), 1, ["단계", "무엇을 하는가", "주요 결과"])`; 캡션 → "표 5. 키워드 기반 분석의 이해하기 쉬운 7단계".
   - 표 6: `resize_table(tbl, 1, 7)` → `fill_table(…, ["구분", "쉽게 말하면", "예시·기준"])`; 캡션 → "표 6. 검색·쪽 배치·등급 판정 기준".
   - 삭제: `find_paragraph` 로 "분석 자료는 반도체고등학교 교과서와", "먼저 파일을 읽어", "파일과 검색어는", "검색 결과는 단순히" 4개와 그 사이 빈 문단 2개(각 글 문단 **바로 다음** 최상위 문단이 빈 문단이면 함께) → `remove_paragraphs`.
   - 재작성 2: "안전보건 수준은 각 출현이 속한" → §3.5 R1; "이 등급은 문장 하나의 완성도를" → R2.
   - 삽입 ①: 표 6 문단 다음 빈 문단(`#00332`) 뒤에 `[H1, P1, B, H2, P2a, B, P2b, B, H3, P3, B, H4]`.
   - 삽입 ②: R2 문단 뒤에 `[B, P4, B, H5, P5, B, H6, P6]`.
   - 삽입 위치는 삭제 뒤에 계산한다(`insert_after` 는 참조 원소 기준이라 순번 무관).
4. 5절의 `section_texts` 는 재탐지(`locate_range` 다시)로 얻어 감사에 넣는다.

### 3.5 A — 템플릿 (`methods_paragraphs(f) -> list[tuple[kind, text, conditions]]`, kind ∈ {"H","P"})

`m = f.methods`, `n = f.ncs`, `s = f.school`, `b = f.bridge`. `{…}` 는 값, `⟨…⟩` 는 분기.

- **H1** ` 1) 자료 정제`
- **P1** `분석 자료는 한국산업인력공단 NCS 학습모듈 {n.documents}권(반도체개발 {개발}권·반도체제조 {제조}권·반도체장비 {장비}권·반도체재료 {재료}권, 총 {n쪽수합:,}쪽)과 반도체고등학교 전공교과서 {s.documents}권(총 {s쪽수합:,}쪽)의 본문이다. PDF를 변환한 마크다운 파일에서 문장·표·제목을 구분하고, 파일 이름의 학습모듈 코드로 같은 자료를 확인하였다. 코드가 없는 파일은 자료로 세지 않았고, ⟨dedup_books>0: 같은 코드의 파일이 둘인 {dedup_books}권은 쪽 표식이 많은 파일만 남겼다.⟩ 파일과 검색어는 한글의 자모 결합 방식이나 띄어쓰기가 달라도 같은 말로 인식되도록 정규화한 뒤 검색하였으며, 표 안의 글자와 제목도 검색 대상에 포함하였다.`
- **H2** ` 2) 의미 표현 사전`
- **P2a** `검색 대상은 {keyword_names 를 '·' 로 이은 목록} 의 {len}개 주제어이다. 각 주제어는 (1) 정확 일치, (2) 동음이의 제외(예: ‘안전’에 포함된 ‘안전성’, ‘안전 마진·여유·재고·율·계수’는 제외), (3) 동등 표현(예: ‘화재’–‘fire’), (4) 구체 표현(예: ‘보호구’–‘장갑·보호안경·안전화’)의 네 층으로 정의한 의미 표현 사전으로 찾았다. ‘MSDS’와 ‘물질안전보건자료’는 워크북의 주제어가 다르므로 각각 집계하였다. 영문 약어(PSM, MSDS)는 단어 경계에서만 일치시켰다.`
- **P2b** `사전은 세 차례 개정하였다(v1 → v1fix → v2). v2는 도메인 검토의 결과이다. 출현이 많은 비정확 표현과 외부 감사가 지목한 표현을 합한 {review_targets}개 표현에서 표현당 최대 {review_per_expression}건, {review_items}건의 문맥을 층화 추출하고, 서로 다른 계열의 AI 코더 둘({계열 A}, {계열 B})이 각 문맥에서 그 표현이 노동자 안전·보건을 뜻하는지를 판정하였다. 유효 판정 {review_n}건 중 두 코더가 일치한 것은 {review_agree}건({일치율}, κ {kappa:.3f})이었고, 불일치 {review_disagreements}건은 연구책임자가 재정하였다. 표현별 정밀도의 {95}% 신뢰구간 하한이 {floor} 미만인 표현은 보류({held 목록}) 또는 조건부 포함({conditional 목록}: 같은 줄이나 앞뒤 한 줄에 안전 동반어가 있을 때만 집계)으로 처리하였다. 이 개정으로 NCS 출현은 {v1fix.NCS:,}건에서 {v2.NCS:,}건으로, 교과서는 {v1fix.교과서:,}건에서 {v2.교과서:,}건으로 ⟨둘 다 감소: 줄었다 / 아니면: 바뀌었다⟩.`
  - 계열 라벨: 코더 id 의 첫 토큰(`-` 앞)을 `{"claude": "Claude", "gpt": "GPT"}` 로 — 없는 접두는 id 그대로(숫자가 들어가면 감사가 멈춰 눈에 띈다).
- **H3** ` 3) 쪽 배치: 실제 PDF 쪽 대응`
- **P3** `2026-04 검색에 쓴 마크다운의 쪽 표식은 대부분 목차에서 유도한 값이어서 한 표식이 실제 여러 쪽을 덮었고, 넓게는 {max_label_width}쪽에 이르렀다(워크북 셀의 {excel_max_chars:,}자 한도에 걸린 쪽 {truncated_pages}개가 그 예이다). 이를 바로잡기 위해 마크다운의 각 줄을 PDF 각 쪽의 본문과 문자 3-gram 포함도로 비교하고, 쪽 순서가 뒤바뀌지 않도록 동적 계획법으로 대응시켜 NCS {page_maps}권의 줄→쪽 대응표를 만들었다. 쪽마다 표식이 있는 {align_books}권은 표식을 우선 쓰고 대응표는 검증에 썼는데, 대응 후보 {align_lines:,}줄 중 정확히 같은 쪽이 {정확률}, ±1쪽 이내가 {근접률}였다. 변환 시 쪽 표식이 실제 쪽인 나머지 {len(marker_books)}권과 교과서 {s.documents}권은 표식을 그대로 썼다. 모든 NCS 출현은 이 대응으로 실제 PDF 쪽에 놓였으며, 그 효과는 제3장 2절 4)에 정리하였다.`
- **H4** ` 4) 쪽 등급 판정` — 다음에 기존 목록(`#00339`~`#00347`)이 온다.
  - **R1** (`#00340` 재작성) `안전보건 수준은 각 출현이 놓인 실제 PDF 쪽(교과서는 쪽 표식이 가리키는 쪽)의 본문을 기준으로 세 등급으로 나누었다.`
  - **R2** (`#00347` 재작성) `이 등급은 문장 하나의 완성도를 직접 평가한 값이 아니라 해당 출현이 놓인 쪽의 판정값이며, 같은 쪽의 모든 출현이 같은 등급을 갖는다.`
- **P4** `이 규칙(안전 용어 {safety_min-1}건 이하 → 등급 1, {safety_min}건 이상이면서 조치 용어 {action_min}건 이상 → 등급 3, 그 사이 → 등급 2)은 2026-04 워크북에 기록된 등급 사유에서 복원한 것으로, 워크북 {repro_pages:,}쪽의 원 판정을 {재현율}({repro_agree:,}쪽) 재현한다. 규칙의 타당성은 워크북 쪽 {sample_pages}쪽(규칙 변형 간 판정이 갈린 쪽과 등급 3 후보 전수 {census_pages}쪽, 나머지 {recall_pool:,}쪽에서 무작위 {recall_pages}쪽)을 서로 다른 계열의 AI 코더가 독립 판정한 결과로 확인하였다. 규칙이 등급 3이라 한 쪽은 {prec_lo}~{prec_hi}%가 코더도 등급 3이었고(정밀도), 코더가 등급 3이라 한 쪽 가운데 규칙이 등급 3으로 잡은 비율은 {rec_lo}~{rec_hi}%였다(재현율). ⟨rec_hi<50: 즉 이 규칙의 등급 3은 보수적인 판정이며, 규칙이 등급 3으로 잡지 않은 쪽에도 구체적 대책이 있을 수 있다.⟩ 교과서는 2026-04 판정이 있는 쪽은 그 등급을 쓰고({existing:,}건), 없는 쪽은 같은 규칙으로 판정하였다({new}건).`
  - 범위 표기: 두 코더 값의 반올림 정수를 정렬해 `lo~hi%`; 같으면 `N%`.
- **H5** ` 5) 집계 단위`
- **P5** `제3장의 등급 비율은 출현건수를 분모로 한다. 하나의 출현이 하나의 등급을 가지며, 같은 쪽에 출현이 여럿이면 그 수만큼 센다. ⟨출현비율>쪽비율: 등급 3 쪽은 정의상 안전·조치 용어가 많은 쪽이어서 출현이 몰리므로, 출현 기준 등급 3 비율(NCS {출현비율})은 쪽 기준 비율({쪽비율})보다 크다. / 아니면: 출현 기준 등급 3 비율(NCS {출현비율})과 쪽 기준 비율({쪽비율})은 분모가 다른 값이다.⟩ 두 값은 같은 판정의 두 분모이며, 쪽 기준 값과 {prev_date} 에 먼저 발표한 쪽 단위 이전 기준({prev_pages:,}쪽, 등급 3 {이전등급3비율})과의 관계는 제3장 2절 4)에 정리하였다. 본 보고서의 모든 비율에는 분모를 함께 적었다.`
- **H6** ` 6) 재현성과 한계`
- **P6** `모든 수치는 공개 저장소({repo_url})의 스크립트가 같은 입력에서 다시 만든다. 실행 기록에는 입력 파일 {inputs}종의 해시, 줄→쪽 대응표 {page_maps}개의 해시, 사전 버전, 코드 커밋이 남으며, 재실행 결과가 기록된 기대값과 다르면 산출물을 쓰지 않는다. 한계는 다음과 같다. {한계 문장들을 첫째·둘째·… 로 번호 매김}` — 한계 목록: ① `줄→쪽 대응의 오차(±1쪽 밖 {5.1%})는 등급에 그대로 전해진다.` ② `등급은 쪽의 용어 밀도 규칙이므로 문장 하나의 완성도를 뜻하지 않으며, 표나 목록으로 용어를 나열한 쪽은 출현이 많아진다.` ③ ⟨rec_hi<50⟩ `규칙의 재현율이 낮아 등급 3 건수는 하한에 가깝다.` ④ `사고사례 자동 판정은 원문 확인이 필요하다(3절).`

표 5 행(7): `1. 자료 수집 | NCS 학습모듈 {n.documents}권과 교과서 {s.documents}권의 PDF와 변환 마크다운, 파일 정보를 모은다 | 분석 자료` · `2. 내용 정리 | 문장·표·제목을 구분하고, 같은 자료는 한 파일만 남긴다 | 검색 가능한 본문` · `3. 키워드 검색 | {len(keyword_names)}개 주제어와 그 동등·구체 표현(의미 표현 사전 v2)을 찾는다 | 출현 목록` · `4. 문맥 확인 | 동음이의어는 제외하고, 조건부 표현은 앞뒤 문맥으로 판정한다. 표현 사전 자체를 외부 코더가 검토한다 | 근거 문맥` · `5. 쪽 배치 | 출현이 놓인 줄을 실제 PDF 쪽에 대응시킨다 | 출현별 실제 쪽` · `6. 등급 부여 | 그 쪽의 본문을 규칙으로 1~3등급 판정하고 출현에 연결한다 | 등급 연결 결과` · `7. 결과 정리·검증 | 파일·분야·주제어별로 집계하고, 실행 기록과 기대값을 대조한다 | 비교 가능한 통계`

표 6 행(7): `검색 표현 | 같은 주제의 여러 표현을 함께 찾는다 | 화재–fire / 보호구–장갑·보호안경·안전화` · `문맥 확인 | 단어가 아니라 실제 의미를 확인한다 | ‘안전성’·‘안전 마진’은 ‘안전’에서 제외, {conditional 목록}은 같은 줄 ±1줄에 안전 동반어가 있을 때만 집계` · `쪽 기준 | 출현이 놓인 실제 PDF 쪽 | NCS {page_maps}권은 줄→쪽 대응표, NCS {len(marker_books)}권과 교과서 {s.documents}권은 쪽 표식` · `등급 1 | 관련 내용이 없거나 매우 부족하다 | 쪽 본문의 안전 용어 {safety_min-1}건 이하` · `등급 2 | 위험은 언급하지만 예방 방법이 불충분하다 | 안전 용어 {safety_min}건 이상, 조치 용어 {action_min-1}건 이하` · `등급 3 | 위험과 구체적인 예방 방법·대응 절차를 제시한다 | 안전 용어 {safety_min}건 이상, 조치 용어 {action_min}건 이상` · `집계 단위 | 출현건수 | 한 쪽에 출현이 여럿이면 그 수만큼 센다. 쪽 단위 값은 제3장 2절 4) 참조`

목차 5절 항목(6): ` 1) 자료 정제` ` 2) 의미 표현 사전` ` 3) 쪽 배치: 실제 PDF 쪽 대응` ` 4) 쪽 등급 판정` ` 5) 집계 단위` ` 6) 재현성과 한계` — 본문 H1~H6 과 같은 문자열(한 상수 목록 `METHODS_HEADINGS` 에서 둘 다 만든다).

### 3.6 B3 — 제3장 2절 갱신 절차

1. `sections = locate_sections(root)` 를 1단계 뒤 **다시** 호출(1단계는 문단 수를 바꾸지 않지만 같은 원소를 다시 쓰는 것이 안전).
2. 2절 `find_paragraph(ncs, " 4) 소결")` 는 공백 시작 locator — `find_paragraph` 는 `strip()` 뒤 비교이므로 `"4) 소결"` 로 찾는다(정확히 1개). 그림 4 캡션 `find_paragraph(ncs, "그림 4.")`.
3. 삽입(그림 4 캡션 뒤; 캡션 다음 빈 문단이 있으면 그 뒤): `[B2, H, B2, Q1, B2, C1, T1, N1, B2, Q2, B2, C2, T2, N2, B2]` — `B2` 는 2절 빈 문단 원형(`#00542`, paraPr 10 · charPr 13, `hp:t` 없음), `H`·`Q` 원형은 각각 " 4) 소결" 문단·소결 첫 문단(`#00545`, 글 run 만), `C/T/N` 은 표 12 캡션·표 문단·주. 표 문단 `T` 는 `clone_table_paragraph(proto_T, rows, 1, header, ids)`.
4. " 4) 소결" → ` 5) 소결` (`set_text`); 목차 2절 블록(`locate_toc_block("2. NCS", "3. NCS")`)의 " 4) 소결" → ` 4) 집계 기준의 변경과 이전 결과와의 관계`, 그 뒤에 ` 5) 소결` 삽입(원형 = 그 목차 문단).
5. 소결 문장: 소결 마지막 문단(`find_paragraph(ncs, "본 연구 결과는 반도체산업 특성을 반영한")`) **뒤**에 `Q` 원형으로 새 문단 S1 삽입(그 문단에는 `ctrl` run 이 있어 `set_text` 를 쓰지 않는다).
6. 1절 문장: 1단계 템플릿 `textbook_paragraphs` 의 "본 연구에서는 9권의 반도체 교과서를" 문단 끝에 ⟨f.ncs_real_pages⟩ ` 교과서는 변환 시 쪽 표식이 실제 쪽이어서 쪽 배치 기준의 변경에 영향을 받지 않았다({s.total:,}건; {school_detected}쪽 가운데 등급 3 {school_page_grades[3]}쪽).` 를 붙인다(조건 `page_basis` 를 `conditions` 에 기록 — 기존 `RealPageBasisTests` 패턴).

### 3.7 B3 — 템플릿 (`bridge_paragraphs(f)`, `bridge_table1_rows(f)`, `bridge_table2_rows(f)`)

- **H** ` 4) 집계 기준의 변경과 이전 결과와의 관계`
- **Q1** `본 절의 수치는 모든 NCS 출현을 실제 PDF 쪽에 놓고 그 쪽의 본문으로 등급을 판정한 {run_date} 정본이다. 그 이전의 집계는 같은 사전과 같은 판정 규칙을 쓰되 출현의 위치를 마크다운의 쪽 표식 블록으로 잡았는데, 이 표식은 대부분 목차에서 유도한 값이어서 한 블록이 여러 쪽을 덮었다. 두 집계의 차이는 표 12-1과 같다. 출현 총계 {total:,}건은 변하지 않았고, 출현이 놓인 단위는 {block_pages:,}개 블록에서 {real_pages:,}쪽으로 ⟨늘었으며/줄었으며⟩, 등급이 바뀐 출현은 {moved:,}건({moved 비율})이었다. 등급 1은 {b1:,}건({b1비율})에서 {r1:,}건({r1비율})으로 {v1}, 등급 2는 {b2:,}건({b2비율})에서 {r2:,}건({r2비율})으로 {v2}, 등급 3은 {b3:,}건({b3비율})에서 {r3:,}건({r3비율})으로 {v3}. 여러 쪽을 덮던 블록이 실제 쪽으로 나뉘면서, 용어가 없는 쪽에 있던 출현은 등급 1로, 용어가 모인 쪽의 출현은 등급 2·3으로 다시 판정된 결과이다. 분야별 등급 3 출현은 {분야별 "이름 b건→r건" 을 ', ' 로}이다. 워크북의 2026-04 판정을 승계하던 출현 {existing_occurrences:,}건은 실제 쪽에서 다시 판정했을 때 {existing_kept_pct:.1f}%만 같은 등급이었으므로, 본 정본은 NCS의 등급을 승계하지 않고 모두 실제 쪽에서 판정하였다.`
  - `v(delta_pp)`: `|Δ| ≤ 0.5` → "거의 같았다", `Δ<0` → "줄었다", `Δ>0` → "늘었다"; 연결형(등급 1·2)은 "거의 같고/줄고/늘었으며", 종결형(등급 3)은 그대로. `BRIDGE_SAME_PP = 0.5` 상수.
  - 분야별 문자열은 `AREA_ORDER`(개발·제조·장비·재료) 순, 그룹 이름은 `NCS_GROUP_TO_AREA` 역매핑으로 "반도체개발" 형.
- **표 12-1** 캡션 `표 12-1. 쪽 배치 기준에 따른 NCS 출현 등급 분포`; 헤더 `구분 | 목차 블록 기준 | 실제 PDF 쪽 기준({run_date} 정본) | 차이`; 행 6: `출현 총계 | {total:,} | {total:,} | 0` · `등급 g | {b:,} ({비율}) | {r:,} ({비율}) | {부호}{|r−b|:,}` ×3 · `출현이 놓인 단위 | {block_pages:,} 블록 | {real_pages:,} 쪽 | —` · `등급이 바뀐 출현 | — | {moved:,} ({비율}) | —`. 주 `주: 단위: 건. 비율의 분모는 {total:,}건. 등급 변화의 내역: 1→2 {m}건, 1→3 {m}건, 2→1 {m}건, 2→3 {m}건, 3→1 {m}건, 3→2 {m}건, 불변 {unchanged:,}건.`
- **Q2** `쪽 단위로 보면 정본의 출현은 {real_pages:,}쪽에 놓이고 그 가운데 등급 3은 {rp3:,}쪽({rp3비율})이다. {prev_date} 에 먼저 발표한 쪽 단위 이전 기준은 2026-04 검색 결과 {prev_rows:,}행을 같은 방법으로 실제 쪽에 재배치한 값으로, {prev_pages:,}쪽 가운데 등급 3이 {prev3:,}쪽({prev3비율})이었다(표 12-2). 두 집계는 같은 줄→쪽 대응과 같은 판정 규칙을 쓰므로, 둘 다 검출한 {shared_pages:,}쪽의 등급은 ⟨agree==pages: 모두 일치한다 / {agree:,}쪽에서 일치한다({비율})⟩. 쪽의 집합이 다른 것은 검출 방식의 차이(문자열 검색 대 의미 표현 사전) 때문이고, 등급 3 비율이 출현 기준 {출현비율}와 쪽 기준 {rp3비율}로 다른 것은 분모 때문이다. ⟨출현비율>쪽비율: 등급 3 쪽은 정의상 안전·조치 용어가 많은 쪽이어서 출현이 몰리므로, 출현을 세면 쪽을 셀 때보다 등급 3의 몫이 커진다.⟩ 따라서 출현 기준 비율을 쪽 기준 비율의 개선으로 읽어서는 안 되며, 본 보고서는 두 값을 분모와 함께 제시한다.`
- **표 12-2** 캡션 `표 12-2. 쪽 단위로 본 이전 기준과 정본의 관계`; 헤더 `구분 | 이전 기준(쪽 단위, {prev_date}) | 정본(쪽 단위, {run_date}) | 정본(출현 단위)`; 행 6: `검출 방식 | 문자열 검색(2026-04 워크북 {prev_rows:,}행) | 의미 표현 사전 v2 | 의미 표현 사전 v2` · `단위 수 | {prev_pages:,}쪽 | {real_pages:,}쪽 | {total:,}건` · `등급 g | {pg:,} ({비율}) | {rp:,} ({비율}) | {r:,} ({비율})` ×3 · `두 집계가 공유하는 쪽 | {shared:,} | {shared:,} (등급 일치 {agree:,}, {비율}) | —`. 주 `주: 쪽 비율의 분모는 각 열의 단위 수. 쪽 배치와 판정 규칙은 세 열이 같고 검출 방식만 다르다.`
- **S1** (소결 뒤 새 문단) `이상의 수치는 출현건수를 분모로 한 값이며, 쪽 단위로 보면 등급 3은 검출 {real_pages:,}쪽 중 {rp3:,}쪽({rp3비율})으로 이전 기준({prev_pages:,}쪽 중 {prev3:,}쪽, {prev3비율})과 ⟨|Δ|≤1.0pp: 같은 수준이다 / 차이가 있다⟩(4) 참조).` — `BRIDGE_LEVEL_PP = 1.0`.

### 3.8 숫자 감사 — FR-08

- `STRIP_BEFORE_AUDIT` 확장: `(?:표|그림)\s*\d+(?:-\d+)?\.?`(표 12-1), `\d{4}-\d{2}(?!\d)`(2026-04), `\bv1fix\b|\bv[12]\b`, `3-gram`, `±1쪽`, `\d\)\s*참조`. `\(\d+\)` 는 이미 있다(문맥의 (1)~(4)).
- 감사 범위: 1단계 3개 절(재탐지) + 5절(`locate_range` 재탐지) + 표 4 캡션·바뀐 셀 4개 + 목차 편집 문단 + 삽입 문단 전부(`inserted` 집합의 `direct_text`, 표는 셀 텍스트). 허용 집합 = `facts.all_numbers() | ALLOWED_TOKENS` — 변경 없음(새 값은 전부 `value_index` 경유).
- 대조 JSON 의 `keys` 는 `facts.keys_for(numbers)` 그대로(새 키 경로가 붙는다: `methods.*`, `bridge.*`).
- `out_of_scope_numbers` 삭제(FR-14) — `audit.out_of_scope` 키도 없앤다. `CommittedDiffTests` 의 두 단언(`found`, `in audit`)은 "5절이 감사 범위에 있다(`diff["methods"]["audited_tokens"] > 0`)" 로 바꾼다.

### 3.9 대조 JSON · 검토 HTML — FR-09

```json
"methods": {"toc": {"rewritten": 6, "removed": 2}, "table4": {"changed_cells": 5},
            "removed_paragraphs": 6, "inserted": [{"kind": "H", "numbers": [], "keys": []}, {"kind": "P", "numbers": ["86", ...], "keys": ["corpora.NCS.documents", ...], "conditions": {...}}, ...],
            "rewritten": [{"locator": "안전보건 수준은", "old_numbers": [], "new_numbers": []}, ...],
            "tables": [{"caption": "표 5.", "rows": 8, "cols": 3, "changed_cells": n}, {"caption": "표 6.", ...}]},
"bridge":  {"inserted": [...], "tables": [{"caption": "표 12-1.", "rows": 7, "cols": 4}, {"caption": "표 12-2.", "rows": 7, "cols": 4}],
            "toc": {"rewritten": 1, "inserted": 1}, "renumbered": {"4) 소결": "5) 소결"}, "conditions": {"grade_verbs": [...], "shared_all_agree": true, "occurrence_share_exceeds_page_share": true, "level_same": true}},
"source": {...}   // ship 리뷰(레드팀·적대적): 백업 이름·sha·동일 여부는 실행 환경 — 화면에만, 추적 JSON 에는 넣지 않는다
```

- 본문 문장은 담지 않는다(`numbers`·`keys`·`conditions`·개수만). `review.html` 의 `table_specs` 에 `("methods", "표 4.", …)`, `표 5.`, `표 6.`, `("bridge", "표 12-1.", …)`, `표 12-2.` 추가. `review_text.html` 에 절 "methods"·"bridge" 를 추가하고 삭제 문단은 (구, "") / 삽입 문단은 ("", 신)으로 병기.

### 3.10 출력·백업 — FR-10 (D1)

`write_hwpx(src, out, …, force)`: `out` 이 있고 `force` 면 먼저 `out` 을 `out.with_name(out.name + f".{sha256(out)[:16]}.bak")` 로 복사(같은 내용이면 같은 이름 — 재실행에 안전; 설계 시점은 8자리였고 ship 리뷰에서 16자리로), 대조 JSON `source.backup`·`source.previous_hwpx_sha256` 에 기록. `.bak` 은 `data/`(비추적). `--no-render` 점검 실행은 백업도 만들지 않는다.

### 3.11 문서·데이터 계보

- `docs/03-analysis/data/README.md`: `occurrence_real_pages_impact.json` 행에 `pages.real_page_grades`·`pages.교과서` 설명, `hwpx_results_refresh_20260915.json` 행에 `methods`·`bridge` 블록.
- `CLAUDE.md` 그룹 4 `hwpx_results_refresh.py` 항목: 2단계(제2장 5절·표 4·목차·제3장 2절 4)), 새 모듈, 손댄 집합 불변 검사, `.bak`, 감사 범위. README 산출물 재생성 절: 실행 명령에 `--force` 와 백업 설명.
- `TODOS.md`: 제안서 B1·B2·B4·B5·C·D·E·F 를 후속 목록으로.

## 4. 테스트 설계 (`test_hwpx_methods_bridge.py`, CI 의 unittest 목록에 추가; fixture 도우미는 `test_hwpx_results_refresh` 에서 import)

fixture: `build_fixture_hwpx(path, body, chapter2=True)` 확장 — 목차(제2장 5절 항목 8개 + 2절 항목 " 4) 소결" 포함), 제2장 1절(표 4 캡션 + 3×2 표, 셀에 문단 4개 "반도체개발 30종"…"반도체재료 22종"), 5절(제목·도입·표 5(7×3)·표 6(6×3)·설명 4문단(+빈 2)·목록 8문단), 2절 꼬리(그림 4 캡션·빈·" 4) 소결"·소결 4문단, 마지막은 `ctrl` run 포함).

| 그룹 | 테스트 |
|---|---|
| Facts | `load_methods_facts`/`load_bridge_facts` 가 정본 파일에서 §3.2 의 값을 읽는다(86·22·618·612·17·0.9648·58·16·84·23·21,711·6·5·1,847·1,839·538·(0.802,0.843)·7 / 11,517·1,785·2,492·4,016·6,292·52.8·1,825/524/143·388·335/45/8·2,189·7,769·2,035); 키 누락·계보 불일치(총계·등급·real_pages·page_maps sha·previous_basis≠reseg) 각각 `ValueError` 에 파일·키 이름 |
| value_pairs | 파생값 문자열(80·84·13·21·97.2%·0.965·95·0.8·83.6%·94.9%·5.1%·99.6%·5·4·590·613·23·34.9%·73.2%·5.7%·69.4%·6.6%·100.0%·21.7%) 이 `all_numbers()` 에 있다; 정밀도 범위가 같은 값이면 "N%" |
| XML | `clone_paragraph` 서식 승계·빈 원형; `insert_after` 순서; `remove_paragraphs` 없는 원소 거부; `next_object_id` 결정적(최댓값+1, pic 포함); `clone_table_paragraph` 고유 id·행 수·헤더; `locate_range` 목차/본문 구분(occurrence); `locate_toc_block` 경계; `set_cell_paragraph` 0·2+ 거부 |
| 불변 검사 | 손댄 집합 검사가 삽입·삭제가 있어도 통과하고, 범위 밖 문단을 몰래 바꾸면 `RuntimeError` |
| A 절차 | 목차 8→6(항목 문자열 = `METHODS_HEADINGS`), 8개가 아니면 오류; 표 4 캡션·셀 4개; 표 5 8행·표 6 8행·캡션; 삭제 6·삽입 20(H6·P7·B7)·재작성 2; 목록 8문단 원소 동일(재작성 2 제외) |
| A 템플릿 | 분기: dedup 0 → 절 생략; 감소/변화; rec_hi<50 양쪽(한계 번호가 셋째·넷째로 이어짐); 출현비율>쪽비율 양쪽; 계열 라벨 매핑·미지 접두; 범위 "N~M%"/"N%" |
| B3 절차 | 삽입 15(H·Q2·C2·T2·N2·B5)·표 id 고유·소결 " 5) 소결"·목차 재작성 1+삽입 1·S1 이 마지막 문단 **뒤**에(ctrl 문단 불변)·1절 문장(page_basis real 에서만) |
| B3 템플릿 | 동사 분기(±0.5pp 경계·연결형/종결형), 늘었/줄었(블록→쪽), 공유 쪽 모두/일부, 몫 문장, S1 같은 수준/차이(1.0pp 경계), 분야 문자열 순서, 표 12-1 차이 부호·합 0, 표 12-2 행·열, 주 문장 6종 합 = moved |
| 감사 | 5절·표 4·삽입 문단·표 셀이 감사 범위에 들고 모두 통과; 5절에 "12,875"·"85종"·"813" 을 심으면 실패하고 HWPX 를 쓰지 않는다; STRIP 확장(표 12-1·2026-04·v1fix·3-gram·±1쪽) |
| E2E | fixture 전체 실행: 문단·표·그림 수, `diff["methods"]`·`diff["bridge"]` 스키마, `review.html` 에 표 5·6·12-1·12-2, `review_text.html` 에 methods/bridge 절, ZIP 항목 동일, `--no-render` 는 HWPX·백업 없음, `--force` 로 덮어쓸 때 `.bak`(설계 시점 sha8, 최종 sha16) 생성·`source.backup` 기록(최종: 화면 출력만, 추적 JSON 제외), 정본 파일을 입력으로 주면(첫 단어 불일치) 명시적 오류 |
| 영향표 | `ImpactScriptTests`: `pages.real_page_grades` 합 = `real_pages`, `pages.교과서.page_grades` 합 = `detected_pages`; 하니스 `S3o` 확장 |
| 커밋 산출물 | `CommittedDiffTests`: 추적 대조 JSON 에 `methods`·`bridge` 가 있고 `audit.status == "ok"`, 인용 수치가 정본 파일과 같다 |

커버리지: 새 함수 전부 fixture 로 실행(≥ 80%). 한글 렌더링·쪽 넘김은 `[→E2E]`.

## 5. 구현 순서 (Do)

1. `occurrence_real_pages_impact.py` `pages` 확장 + `ImpactScriptTests` + `S3o` → 재실행·커밋 산출물 갱신(하니스 통과 확인).
2. `hwpx_methods_bridge.py`: `MethodsFacts`/`BridgeFacts`/적재/`value_pairs` (테스트 먼저).
3. `hwpx_results_refresh.py`: `CorpusFacts.detected_pages`, `Facts.methods/bridge`, `value_index` 합치기, XML 능력(§3.3), 손댄 집합 검사로 교체, `write_hwpx` 백업.
4. 템플릿(§3.5·§3.7) + 분기 테스트.
5. `refresh_methods_bridge` 조립(§3.4·§3.6) + fixture E2E; `out_of_scope` 제거·`CommittedDiffTests` 갱신; 1절 문장(1단계 템플릿).
6. 실문서 실행: `python3 hwpx_results_refresh.py --force` → 대조 JSON·`review.html` 갱신, `review_text.html`(비추적) 검토, `.bak` 확인.
7. 문서(§3.11)·CI unittest 목록·`/pdca analyze`.

## 6. 결정 기록

| 항목 | 결정 |
|---|---|
| D1~D6 (계획) | 모두 (a) — 연구책임자 2026-09-16 |
| 모듈 분리 | 사실·템플릿은 `hwpx_methods_bridge.py`, XML 능력·조립은 `hwpx_results_refresh.py` |
| 임계 6·5 | `regrade_impact.json.rule` 에서 읽는다(계획 FR-13 의 상수 이동 불필요) |
| 날짜 | ISO(`2026-04`, `2026-09-15`, `2026-09-06`)만 — 정본 `generated_at`·`previous_basis.date` 에서; 사전 개정 날짜·"4건"·"출현 50건 이상" 은 문장에서 뺌 |
| 소결 문장 | 새 문단(마지막 소결 문단에 `ctrl` run) |
| 1절 문장 | 1단계 템플릿에 `page_basis` 분기로 |
| 백업 이름 | `<out>.<sha16>.bak` — 같은 내용이면 같은 이름 (설계 v1.0 은 `<sha8>`, ship 리뷰에서 16자리로) |
| 표 12-2 4열 | 이전 기준 쪽 / 정본 쪽 / 정본 출현 — 세 분모를 한 표에 |
| 빈 문단 | 삽입 문단 사이에 그 절의 빈 문단 원형을 끼운다(문서의 간격 규칙 유지); 소결 문장 S1 앞에도 빈 문단 하나 |
| 5절 삭제 범위 (Act-1 기록) | 첫 locator("분석 자료는 반도체고등학교 교과서와")~끝 locator("검색 결과는 단순히") 사이의 연속 최상위 문단 전부(빈 문단 포함, 6개) — "각 문단 뒤 빈 문단" 규칙과 결과가 같고 구현이 단순 |
| 표 4 셀 탐지 (Act-1 기록) | 행·열 위치가 아니라 "반도체개발" 로 시작하는 문단을 가진 셀(정확히 1개) — 표 구조가 조금 바뀌어도 견고 |
| 최대 표식 폭 58 (Act-1 기록) | `ncs_pages_reseg.csv` `구라벨` 을 `;` 로 나눈 (교재, 라벨) 별 행 수의 최댓값. `|` 로 나누면 53 이 나오는데 그건 라벨 결합 기호를 잘못 본 값 |
| 목차 5절 가드 (Act-1, 갭 G1) | 구고 소제목이 정확히 8개(`OLD_METHODS_TOC_ENTRIES`)가 아니면 ValueError — 다른 문서·2단계 산출물 재입력 방지 |
| 산출물 재입력 (Act-1, 갭 G6) | `refresh()` 시작에서 5절 소제목 " 1) 자료 정제" 또는 2절 " 4) 집계 기준…" 이 이미 있으면 "이미 2단계 산출물" 로 선제 거부(1단계 locator 실패 메시지보다 먼저) |
| 대조 JSON `bridge.conclusion` (Act-1, 갭 G4) | 소결 문장의 숫자·출처 키·조건을 기록 |
| `grade_sources` 부재 (Act-1, 갭 G5) | `load_facts` 가 ValueError — 0 으로 채우지 않는다 |
| 문장 보정 | P1 "…세지 않았다.⟨dedup 절⟩"(절이 없어도 문장이 닫힘); Q2 일부 일치는 계획 FR-07 문구 "{쪽} 중 {일치}쪽에서 일치한다"; 등급 1·2·3 동사는 "-고 / -으며 / 종결형" |

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 0.1 | 2026-09-16 | 초안 — 사실 모델·XML 능력·A/B3 절차와 전체 템플릿·감사·대조 JSON·백업·테스트 설계 | Claude (Opus 5) |
| 1.0 | 2026-09-16 | 구현 반영 — 표 12-2 4열×6행(+헤더), 58 산출 규칙, Act-1 결정 기록(G1·G4·G5·G6·G8) | Claude (Opus 5) |
