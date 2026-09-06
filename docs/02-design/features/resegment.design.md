# resegment Design Document

> **Summary**: `resegment.py` — PDF 쪽 텍스트에 마크다운 줄을 단조 DP 로 정렬하고(쪽 단위 마커가 있는 교재는 마커를 그대로 씀), 워크북 검출 행을 실제 쪽으로 옮겨 페이지 단위 등급을 재집계한다.
>
> **Plan**: `docs/01-plan/features/resegment.plan.md`
> **Date**: 2026-09-06 (Act-1 동기화: Gap 분석 G3·G4·G6·G8~G11 반영)
> **Status**: Implemented — 결과 `docs/03-analysis/resegment-results.analysis.md`, Gap 분석 `docs/03-analysis/resegment.analysis.md`

---

## 1. 데이터 흐름

```
PDF (84권)  ──PyMuPDF get_text──▶ 쪽별 텍스트 ─┐
                                              ├─▶ align_lines(): 줄→쪽 (단조 DP) ─┐
마크다운 (84권) ──split('\n')──▶ 줄 목록 ─────┘                                 │  마커가 PDF 쪽수의 80% 이상(23권)이면
                       │                                                         │  marker_pages() 가 줄→쪽을 대신하고
                       └── 마커 밀도 판정 (DENSE_MARKER_RATIO=0.8) ───────────────┤  정렬 결과는 check_alignment() 검증에만 쓴다
                                                                                 ▼
                                                  propagate(): 전 줄 쪽 ─▶ page_texts(): 쪽→본문
                                                                                 │
워크북 7,769행 ──load_rows()──▶ (시트, 영역, 교재, contents, 라벨, 사고사례, 구등급, 사유) ─▶ match_rows(): 행→줄 ─▶ 행→실제 쪽
                                                                                 │           (미매칭 행은 구 라벨을 쪽으로, source='label')
                                                         regrade_page(본문) 기준선 ◀──────────┘
                                                                                 ▼
                                   aggregate(): (교재, 실제 쪽) 고유 → 등급·사고사례·영역·kw_pages·지문 ─▶ check_expected() 가드 ─▶ CSV / JSON / 대응표
```

마크다운이나 PDF 가 없는 교재(2권)는 `unresolved_pages()` 로 구 라벨·구 등급(행 최저)을 그대로 쓰고 `status='unresolved'` 로 센다.

## 2. 함수 계약 (`resegment.py`, 표준 라이브러리 + `regrade`/`recount_grades`/`page_utils` 임포트 — 앞의 둘은 임포트 시 openpyxl 가드가 있어 하니스는 `openpyxl` 을 스텁한다; PyMuPDF 는 `main()` 안에서만)

| 함수 | 입력 | 출력 | 규칙 |
|---|---|---|---|
| `norm_text(s)` | 문자열 | 정규화 문자열 | NFC → 공백·마크다운 기호(`#*_>\|[]()!\`-–·•○●◆◇■□▶▷※,.:;`) 제거 |
| `grams(s, n=3)` | 문자열 | 3-gram 집합 | |
| `align_lines(lines, pages_text, min_len=12, min_contain=0.5, window=6, jump_pen=0.06, far_pen=1.0)` | 마크다운 줄, 쪽 텍스트 목록 | `{줄 idx: 쪽(1-based)}` | 정규화 길이 ≥ `min_len` 이고 최대 포함률 ≥ `min_contain` 인 줄만 후보. 마커 줄 제외. DP: 같은 쪽 유지 0, 앞으로 d쪽(≤ window) 점프 `jump_pen·d`, 그 밖의 앞 점프 `far_pen`, 뒤로는 불가. 첫 후보 줄은 동점이면 앞 쪽(`-1e-3·p`). `jump_pen` 기본 0.06 — 마커 보유 22권(Check-1 실행, Act-2 이전 — 현재 23권) 스윕에서 0.06~0.25 가 정확도 83.3~84.1% 로 둔감했고, 0.12 는 이웃 쪽에 거의 같은 문장이 반복될 때 이동을 막았다(R16i 픽스처) |
| `propagate(n, assigned)` | 줄 수, 정렬 결과 | 줄별 쪽 목록 | 미정렬 줄은 직전 정렬 줄의 쪽, 앞에 없으면 다음 정렬 줄의 쪽. 정렬 줄이 없으면 전부 None |
| `marker_pages(lines)` | 줄 목록 | 줄별 쪽 목록 | `<!-- page: N -->` 마커로 줄→쪽. 첫 마커 앞 줄은 첫 마커의 쪽 |
| `page_texts(lines, line_pages)` | | `{쪽: 본문}` | 마커 줄 제외, 쪽별 줄을 `\n` 으로 이어붙임 |
| `check_alignment(lines, assigned)` | 마커 보유 교재 | `{lines, exact, near}` | 마커로 만든 정답과 정렬 결과 비교(정확, ±1) — DP 후보 줄만 |
| `check_alignment_all(lines, line_pages)` | 마커 보유 교재 | `{all_lines, all_exact, all_near}` | `propagate` 까지 마친 줄→쪽을 마커와 대조 — 본문이 있는 모든 줄이 분모(빈 줄·마커 줄·첫 마커 앞 줄 제외). 후보 줄만 세는 값보다 낮다(실측 77.6% / 90.3%) |
| `sentence_key(contents)` | 워크북 contents | `(짧은 키, 전체 키)` | 짧은 키 = 마지막 줄(제목 맥락 제거) 정규화, 전체 키 = contents 전체 정규화. 어느 쪽을 쓸지는 `match_rows` 가 정한다 |
| `match_rows(rows, lines, stats=None)` | 행 목록(문서 순서), 줄 목록, (선택) 집계 dict | 행별 줄 idx 또는 None; `stats` 에 overflow(적중보다 행이 많아 마지막 적중 재사용)·ambiguous(적중 둘 이상)·partial(긴 줄의 일부로 적중) | 짧은 키가 10자 이상이면 그 키의 전체→80→50→30자 접두로 줄 검색. 10자 미만(‘안전 · 유의 사항’ 같은 정형구)이면 줄 전체가 같은 줄만 적중으로 보고, 없으면 전체 키로 검색. 같은 (시트, 키) 의 행들은 문서 순서로 서로 다른 적중에 1:1 배정, 적중이 모자라면 마지막 적중 재사용. 못 찾으면 None |
| `regrade_page(text)` | 본문 | (등급, 안전수, 조치수, 사유) | `regrade.grade_page(text, word_boundary=False, normalize=False)` 기준선 |
| `unresolved_pages(rows)` | 한 교재의 행 | `{라벨: rec}` | 라벨을 쪽으로, 등급은 행 최저(recount 규칙), 사유는 첫 행, 사고사례 OR, `source='label'` |
| `resegment_book(rows, lines, pages_text, prefer_markers=False, stats=None)` | | `(pages, moved, unmatched, line_pages, assigned, idx)` 또는 None | `prefer_markers` 면 `marker_pages`, 아니면 `propagate(align_lines)`. 쪽 레코드 `source`: `text`(매칭 행이 놓인 쪽) / `text-fallback`(매칭 행은 없고 미매칭 행의 구 라벨로만 왔지만 본문이 있어 `regrade_page` 로 채점) / `label`(본문도 없어 행 최저 등급, 사유는 그 최저 등급 행의 것). `md_chars`·`pdf_chars` 는 쪽에 붙은 마크다운·PDF 본문의 정규화 길이. `stats` 는 `match_rows` 로 전달 |
| `page_grade_digest(books)` | 책별 결과 | 16자리 sha256 | 정렬된 (교재, 쪽, 등급) 전체의 지문 — 순서 무관, 한 쪽의 등급만 바뀌어도 달라짐 |
| `check_expected(summary, expected=EXPECTED)` | 요약 | 불일치 문자열 목록 | pages·books·page_g·unresolved_pages·digest 에 더해 expected 가 가진 cases_pages·cases_books·moved_rows·unmatched_rows·label_fallback_pages 대조(지문이 못 잡는 수치). `digest` 가 None 이면 지문은 비교하지 않음 |
| `aggregate(books)` | 책별 결과 | summary dict | `pages, books, page_g, cases_pages, cases_books, areas{books,pages,page_g}, unresolved{books,pages,rows}, moved_rows, unmatched_rows, label_fallback_pages, kw_pages, page_grade_digest, alignment_check{books, overall, per_book}`. `per_book`(page_g 포함)·`method_books`·`case_pages`·`meta` 는 `main()` 이 붙인다 |
| `load_rows(path, loader=None)` | 워크북 경로 | 행 dict 목록 | 열은 위치(`COL_*`)로 읽는다. 헤더 행과 `filename` 잡행 스킵, 라벨·등급은 int 또는 None, 사고사례는 `'예'` → True. `loader` 는 시험용 주입점 |
| `index_files(root, pattern)` / `pick_md(code, filename, md_index)` | | | 파일명의 `LM\d{10}` 코드로 색인. 같은 코드가 여럿이면 워크북 파일명과 공통 접두가 가장 긴 것, 동점이면 마커가 많은 것(공백/밑줄만 다른 중복 파일) |

`main()` 인자: `--pdf-root`(기본 `$NCS_PDF_ROOT`), `--md-root`, `--workbook`, `--out`, `--paged-dir`, `--limit`, `--force`. 가드 순서: `--limit` 인데 `--out` 이 기본 추적 경로이거나 `--paged-dir` 가 기본 대응표 디렉터리(부분 실행이 추적 산출물·대응표를 덮어쓰거나 섞지 않도록) → 워크북 없음 → PDF 루트 없음 → 마크다운 루트 없음 → PyMuPDF 없음 → 각각 한 줄 종료. `--limit` 없이 `EXPECTED` 와 어긋나면 `--force` 없이는 쓰지 않는다. `index_files` 는 glob 결과를 정렬해 파일시스템 순서에 기대지 않는다.

## 3. 산출물

| 파일 | 내용 | 추적 |
|---|---|---|
| `docs/03-analysis/data/ncs_pages_reseg.csv` | 영역, 교재, 페이지(PDF 1-based), 등급, 등급명, 사고사례, 등급사유, 상태(resolved/unresolved), **출처(text / text-fallback / label)**, md자수, pdf자수(정규화 길이; 미해결·본문 없는 쪽은 빈 칸), 구라벨(세미콜론 구분, 마지막 열). 교재·쪽 순 | 추적(본문 없음) |
| `docs/03-analysis/data/reseg_summary.json` | `aggregate()` 키 전부 + `per_book`(status, method, rows, old_pages, new_pages, moved_rows, unmatched_rows, pdf_pages, md_markers, aligned_lines, align(후보 줄 lines/exact/near + 전체 줄 all_lines/all_exact/all_near), match_stats, **page_g**), `match_stats`(overflow·ambiguous·partial 합), `fallback_rows_on_text_pages`(매칭 행이 있는 쪽에 구 라벨 번호로 합류한 미매칭 행 — kws·case 에는 안 들어감), `method_books`, `case_pages`(교재·쪽·구라벨·등급), `meta`(workbook, workbook_sha256, pdf_root·md_root 는 `public_path()` 로 — 저장소 안이면 상대 경로, 홈 아래면 `~/…`, 그 밖은 마지막 이름만, rows, md_files, pdf_files, expected, rule, run_at) | 추적 |
| `data/markdown/ncs_paged/<코드>.pages.json` | `{md, pdf, line_pages}` — 줄→쪽 대응(재현·검증용) | gitignore(data/) |
| `data/markdown/ncs_paged/rows_map.csv` | 교재, 시트, 구라벨, 새쪽, 구등급, 사고사례 — 행 단위 구→신 대응표(계획 FR-05) | gitignore |

`EXPECTED`(모듈 상수): `pages 2173, page_g {1: 1502, 2: 524, 3: 147}, books 86, unresolved_pages 51, digest 39d00effeb0dfe6c, cases_pages 13, cases_books 5, moved_rows 4316, unmatched_rows 94, label_fallback_pages 27, alignment_overall {21711/18142/20613, all 32486/25219/29329}, match_stats {293/1118/118}`. 대응표(`<코드>.pages.json`·`rows_map.csv`)는 이 검사를 지난 뒤(또는 `--force`)에만 쓴다 — 거부된 실행이 추적본과 어긋난 대응표를 남기지 않게. 입력이 정당하게 바뀌면 `--force` 로 쓰고 `EXPECTED` 를 갱신한다. `--force` 로 어긋난 채 쓰면 `meta.expected` 는 null 이고 `meta.expected_mismatch` 에 불일치 목록이 남는다; `meta.limit` 은 부분 실행 표시.

## 4. 테스트 (`outputs/test-recount-grades.py` R16, 픽스처만 — PDF·워크북 없음)

| ID | 검증 |
|---|---|
| R16a | `norm_text` 가 공백·기호를 지우고 NFC 로 통일 |
| R16b | `align_lines` 가 3쪽짜리 합성 문서에서 줄을 제 쪽에 놓고 단조를 지킨다(양쪽에 있는 문장은 앞 쪽 우선, 뒤에서는 뒤 쪽) |
| R16c | 포함률 미달·짧은 줄은 정렬되지 않고 `propagate` 가 직전 쪽을, 첫머리는 다음 쪽을 물려준다 |
| R16d | `match_rows` — 같은 시트 같은 문장 2회 → 다른 줄, 다른 시트 같은 문장 → 같은 줄, 없는 문장 → None, 적중 부족 → 마지막 적중 |
| R16e | `page_texts` + `regrade_page` = `grade_page` 기준선, 블록을 쪼개면 등급이 오르지 않는다 |
| R16f | `aggregate` 가 미해결 책을 세고 `page_g` 합 = `pages`, `kw_pages`·`alignment_check` 를 낸다 |
| R16g | `check_alignment` 정확·±1 |
| R16h | `main` 가드: 워크북·PDF 루트 없음 → 한 줄 종료 |
| R16i | `marker_pages`; `prefer_markers` 면 `resegment_book` 이 정렬 대신 마커 쪽을 쓴다 |
| R16j | `write_outputs` CSV 10열·순서·출처, JSON |
| R16k | `load_rows` 열 위치·헤더/잡행 스킵·형 변환·close |
| R16l | `unresolved_pages` 행 최저 등급·OR·첫 행 사유·`source='label'` |
| R16m | `pick_md` 공통 접두 점수, 동점(공백/밑줄만 다른 중복)이면 마커 많은 파일, glob 순서 무관 |
| R16n | `main` 완주(가짜 fitz·행·임시 루트): `EXPECTED` 불일치 시 쓰지 않고 거부, `--force` 면 CSV·JSON·pages.json·rows_map.csv 생성, 미해결 집계, 홈 경로 없음 |
| R16o | `page_grade_digest` 순서 무관·재배정 민감, `check_expected` 가 총계 같아도 지문 불일치를 잡음, `EXPECTED` 키 |
| R16p–R16z14 | 출하 전 커버리지 감사·리뷰 반영(2026-09-06): 정렬 경계·원거리 점프·마커/검증 경계·짧은 키·라벨 폴백·가드 4종·`--limit`·마커 우선 완주·재실행 동일성·추적 산출물 교차검증(R16z4·z5)·`public_path`·출처 3값과 `match_stats`·`check_alignment_all`·`--paged-dir` 가드·매칭 쪽 폴백 행·거부 실행의 대응표 미작성 |

## 5. 보고서 반영 (재수정 목록 [재집계] 항목)

표 11·12, 그림 3·4, 2절 2) 분야별 문장, 2절 3) 신설 단락(방법·정확도), 3절 사고사례 실제 쪽 — `data/교정-교정-반도체 교재_피드백(0905)_…_수정0906.hwpx` 에 반영. 대시보드는 범위 밖.
