# HWPX 보고서 제3장 연구 결과(1~3절) 정본 수치 갱신 설계

> **Summary**: `hwpx_results_refresh.py` 가 정본 JSON(`semantic_summary.json` — D1·D2 로 확장, `accident_case_pages.json` 신설)을 읽어 `data/반도체 기초보고서_20260911.hwpx` 제3장 1~3절의 문단·표 7개·그림 3개를 다시 쓰고, 새 파일·변경 대조 JSON·검토 HTML 을 낸다. 절 탐지는 제목 텍스트, 문단은 템플릿 + 데이터 조건 분기, 표는 셀 텍스트 교체(표 13 만 행 증감), 그림은 SVG → 원본 형식·크기. 다른 절·ZIP 항목은 바이트 동일.
>
> **Project**: SearchInMD
> **Feature**: hwpx-ncs-section-refresh
> **Plan**: `hwpx-ncs-section-refresh.plan.md` (Approved — D1~D5)
> **Author**: Claude (Opus 5)
> **Date**: 2026-09-14
> **Status**: Draft

---

## 1. 설계 목표

1. **정본 단일 출처.** 보고서에 들어가는 숫자는 전부 추적 파일(`semantic_summary.json`, `accident_case_pages.json`)에서 온다. 스크립트 상수는 "문장 틀"과 "교재→분야 대응표"뿐이다.
2. **재현·검증.** 같은 입력이면 `section0.xml` 이 같다. 대조 JSON 이 문단/셀마다 구 값 → 새 값 → 출처 키를 남기고, 숫자 감사가 잔존 구 수치 0 을 증명한다.
3. **최소 침습.** 1~3절 밖의 XML 노드·ZIP 항목은 바이트 동일. 문단·표의 서식(`paraPrIDRef`·`charPrIDRef`·`borderFillIDRef`·셀 크기)은 승계한다.
4. **원본 보존.** 입력 파일은 읽기만 한다. 출력은 새 이름, 임시 파일 + `os.replace`.

## 2. 아키텍처

```
semantic_keyword_recount.py ──summary_payload(D1·D2 확장)──▶ docs/03-analysis/data/semantic_summary.json
                                                              ├─ corpora.*.groups[].pages           (교재 실제 쪽수 = 마커 최대값 합)
                                                              └─ keywords[].corpora.*.groups[]      (키워드×그룹 총계·등급)
docs/03-analysis/resegment-results.analysis.md §3.4 ──손으로 옮김──▶ docs/03-analysis/data/accident_case_pages.json (13행, 판정)
                                                                        ▲ test: ncs_pages_reseg.csv 사고사례=예 13쪽과 일치

hwpx_results_refresh.py
  load_summary / load_cases ──▶ Facts (dataclass: NCS·교과서 총계·등급·분야·키워드·쪽수·사고사례 집계)
  Section.locate(root, start_heading, end_heading)      ── 제목 텍스트로 절 경계
  PARAGRAPHS: [Locator(regex on old text) → template(facts) → new text]  ── 1절 13 · 2절 18 · 3절 6
  TABLES:     [caption → TableSpec(rows(facts))]        ── 표 7~12 셀 교체, 표 13 행 증감
  FIGURES:    [binaryItemIDRef → svg(facts) → magick → bytes]  ── image1.PNG 702×391, image2.BMP 1160×750, image3.BMP 1160×724
  write_hwpx(src, out, section_xml, bindata)            ── ZIP 재작성, 나머지 항목 바이트 복사
  diff.json (문단/셀/그림별 old→new·source key·조건 분기 결과), review.html (표·그림만)
  audit_numbers(section_texts, facts, allow)            ── 숫자 토큰 전수 대조 → 실패 시 exit 1
```

## 3. 상세 설계

### 3.1 정본 JSON 확장 — D1·D2 (`semantic_keyword_recount.py summary_payload`)

- `corpora.<corpus>.groups[i].pages`: 그룹에 속한 문서의 `max(block.page for block in split_pages(doc))` 합(마커 없는 문서는 0). NCS 는 4개 분야, 교과서는 교재별 9개 그룹(기존 그대로).
- `keywords[i].corpora.<corpus>.groups`: `[{"name", "total", "grades": {"1","2","3","unpaged"}}]` — 그룹 순서는 `corpora.*.groups` 와 같다. 합이 그 키워드의 `total`·`grades` 와 일치(테스트).
- `summary_sha256` 은 `result.summary`(SummaryRow) 해시라 JSON 필드 추가로 바뀌지 않는다 → `EXPECTED` 재고정 없이 정본 재실행(가드 통과). `semantic_recount_data.js` 도 같이 갱신.
- 하니스 `S3`: 키워드×그룹 합 = 키워드 총계, 그룹 `pages` > 0(마커 있는 문서), 교과서 9그룹 `pages` 합 = 2,055(recount `summary.json textbook.total_pages` 와 대조 — 교과서 마커가 쪽 단위이므로 같아야 한다).

### 3.2 사고사례 판정 데이터 — `docs/03-analysis/data/accident_case_pages.json`

```json
{"source": "resegment-results.analysis.md §3.4 · ncs_pages_reseg.csv 사고사례=예", "date": "2026-09-06",
 "verdicts": {"case": "실제 사고 서술 (반도체 산업재해)", "case_other": "실제 사고 서술 (반도체 산업재해 아님)", "false_positive": "오탐"},
 "pages": [
   {"book": "LM1903060329_19v1_반도체_장비_안전관리", "title": "반도체 장비 안전관리", "area": "장비", "page": 33,  "old_label": "46",  "gist": "구미 H사 불산 가스 누출", "verdict": "case"},
   {"book": "LM1903060411_23v3_반도체_재료_안전관리", "title": "반도체 재료 안전관리", "area": "재료", "page": 27,  "old_label": "28",  "gist": "같은 사건 (중복 게재)", "verdict": "case"},
   {"book": "…재료_안전관리", "page": 33, "gist": "2014년 공연장 환풍구 붕괴", "verdict": "case_other"},
   {"book": "…장비_안전관리", "page": 53, "gist": "무재해운동 정의", "verdict": "false_positive"},
   {"…": "97·103·105·107·110·112 보호구 착용 지침 6쪽", "verdict": "false_positive"},
   {"…리소그래피_재료_제조": 69, "…포토_공정_재료_제조": 67, "…트랙_공정_재료_제조": 78, "gist": "톨루엔 물성/유해성/인화성", "verdict": "false_positive"}
 ]}
```

- `gist` 는 10~15자 요지(교재 본문 문장이 아님). 본문 인용 없음.
- 테스트 `test_accident_case_pages_match_reseg_csv`: `(book, page)` 집합 == CSV 의 사고사례=예 13행; 집계 `case` 2쪽(사건 1건, 교재 2권)·`case_other` 1·`false_positive` 10; `cases_books` 5 == `reseg_summary.json`.
- 파생 수치(스크립트가 계산): 자동 판정 13쪽·5권, 그중 『반도체 장비 안전관리』 8쪽, 실제 사고 서술 3쪽(장비 1·재료 2), 반도체 산업재해 사건 1건(2권 중복), 오탐 10쪽(지침 6·정의 1·물성 3).

### 3.3 절 탐지 — FR-01

- 최상위 `hp:p`(표 셀 안 문단 제외)에서 `direct_text(p)` 가 제목과 정확히 일치하는 첫 문단을 찾는다. 목차(문단 27~150 부근)에도 같은 제목이 있으므로 **두 번째 일치**가 아니라 "제3장 연구 결과" 본문 제목(두 번째 출현) 이후의 첫 일치를 쓴다. 경계: 1절 = "1. 반도체고등학교 전공교과서의 안전보건 키워드 분석 주요 결과" ~ "2. NCS …", 2절 = ~ "3. NCS 반도체 교과서의 사고, 부상, 질병 사례 분석", 3절 = ~ "4. 학생 대상 화학물질·안전보건 교육의 필요성과 효과".
- 절 안에서 문단은 `Locator`(원문 시작 20자 또는 정규식)로 찾는다. 찾지 못하거나 둘 이상이면 실패(exit 1) — 조용히 건너뛰지 않는다.

### 3.4 문단 재작성 — FR-03

- `set_text(p, text)`: 첫 `hp:run` 의 `charPrIDRef` 를 승계해 `hp:t` 하나로 만든다. 나머지 run 중 `hp:t` 만 가진 것은 제거, `hp:ctrl`·`hp:secPr`·`hp:tbl`·`hp:pic` 을 가진 run 은 그대로 둔다(본문 문단은 전부 텍스트 run 뿐임을 실측). 원문에 서식 run 이 둘 이상이면 대조 JSON 에 `"format_collapsed": true`.
- 템플릿은 함수 `def p_903(f: Facts) -> str` 형태로 원문 문장을 그대로 두고 숫자·조건절만 데이터로 채운다. 조건 분기 예:
  - 903: 등급1 이 최대이면 "등급 1이 N건(p%)으로 가장 많았고", 아니면 최대 등급을 말한다.
  - 913: 등급2+3 비율 ≥ 60% 이면 "60%를 넘었다", 아니면 "p% 였다".
  - 917·1229: 공정안전관리 등급3 이 전부이면 "모두 등급 3", 아니면 "N건 중 M건(p%)이 등급 3".
  - 1139: 안전 비중이 분야 중 2위이면 "재료 분야 다음으로 높아", 아니면 순위를 말한다. 사고 사례 문장은 §3.2 파생 수치로 교체.
  - 561: 검출 키워드 수 = 30 − (총계 0 인 키워드 수); 상위 6 을 정렬해 나열(동률은 원본 순서).
  - 1274~1284: 3절은 "2권·9건" 서술을 "자동 판정 13쪽·5권 → 실제 사고 서술 3쪽 → 반도체 산업재해 1건(2권 중복) → 오탐 10쪽" 구조로 다시 쓴다. 유형 문단(1278)은 불산 누출·환풍구 붕괴만 사례로 남기고, TMAH·아르신·방사선은 "자동 판정이 사례로 잡았으나 원문은 보호구 착용 지침·물질 유해성 설명" 으로 정정. 서술 길이 문단(1280)은 두 사례의 원문 길이를 말하지 않는다(본문 인용 없음) — "한두 문장의 간략한 서술" 로 일반화.
- D3: 909 의 "같은 용어이므로 643건" → "같은 개념(물질안전보건자료)을 가리키지만 워크북 키워드가 달라 독립 집계했다(MSDS 453건, 물질안전보건자료 155건)".
- 분야 문단의 쪽수(D2)는 `groups[].pages`; 교과서 분야 쪽수는 교재→분야 대응표로 교재 `pages` 를 합산.

### 3.5 표 교체 — FR-04

- `find_table(section, caption)`: 캡션 문단("표 10. …") 다음 최상위 문단의 `hp:tbl`; 표 13 은 첫 셀 텍스트가 "표 13." 인 `hp:tbl`.
- `set_cell(tc, text)`: `hp:subList/hp:p` 첫 문단에 `set_text`. 열 수·행 수는 검사(불일치 시 실패).
- 표 7·10: 데이터 30행을 총계 내림차순(동률 원본 순서)으로 채움. 열 = 키워드·전체·등급1·2·3·등급합계(= 전체, 미확정 0). 합계 행 = 정본 총계.
- 표 8·11: 분야 4행(개발·제조·장비·재료) + 합계. 열 = 분야·권수(파일수)·전체·등급1·2·3·(등급합계)·출현비율. NCS 분야는 `groups` 이름(반도체개발→개발 …), 교과서 분야는 대응표 합산.
- 표 9·12: 등급 3행 + 합계, 비율 = 등급/총계.
- 표 13: 헤더(교재 이름·분야·주요 내용·페이지·판정) — 마지막 열 제목을 "문장 수(글자 수)" → "판정" 으로 바꾸고, 데이터 행 13개(`accident_case_pages.json` 순서: 실제 사고 → 산업재해 아님 → 오탐), 표 끝의 빈 간격 행은 유지. 행 증감: 첫 데이터 행 `hp:tr` 을 `deepcopy` 해 모든 데이터 행을 같은 서식으로 만들고(레드팀 지적 — 마지막 행을 복제하면 빈 간격 행이 늘어난다) `cellAddr.rowAddr` 와 `hp:tbl@rowCnt` 를 다시 매긴다. 요약 문장은 표 아래 문단(1286 뒤)이 아니라 1274 에 둔다.
- 표 12·9 의 주(1257): "분모: 11,517건 (정본 2026-09-14, 사전 v2). 등급은 페이지의 등급을 출현마다 연결한 값".

### 3.6 그림 재생성 — FR-05

- SVG 를 문자열로 만들고 `magick -font AppleGothic.ttf svg:- PNG24:-` 또는 `BMP3:-` 로 렌더. 크기는 원본 `BinData` 헤더에서 읽어(PNG IHDR, BMP `biWidth/biHeight`) SVG `width/height` 에 넣는다 — 하드코딩 없음.
- 그림 2(image1.PNG 702×391): 교과서 등급별 가로 막대 3개 — 제목 "교과서 안전보건 등급별 출현건수", 부제 "등급 판정 1,207건 · 출현건수 기준 · 정본 2026-09-14(사전 v2)".
- 그림 3(image2.BMP 1160×750): NCS 분야별 등급 1/2/3 가로 막대(4분야 × 3) — 범례·값 라벨, 하단 주 "원자료 폴더 기준 · 정본 86권 11,517건 · 사전 v2".
- 그림 4(image3.BMP 1160×724): NCS 등급별 가로 막대 3개 — 부제 "등급 판정 11,517건", 하단 주 "등급: 페이지의 판정값을 각 키워드 출현에 연결 · 미확정 0".
- 색: 기존과 같은 `#64748b / #c87a05 / #087f75`. 폰트 크기·여백은 원본 그림을 따른다. 렌더 결과 sha256 을 대조 JSON 에 기록; 테스트는 크기·형식·비트 깊이만 검사(`magick` 이 없으면 그림 단계 skip + 경고, 실문서 실행에는 필수).

### 3.7 ZIP 재작성 — FR-06·07

- `zipfile.ZipFile(src)` 의 항목을 순서대로 복사하되 `Contents/section0.xml` 과 교체 대상 `BinData/*` 만 새 바이트. `mimetype` 은 첫 항목·무압축 유지(원본 방식 그대로 — `ZipInfo` 복사).
- 출력 경로가 입력과 같으면 거부. 존재하면 `--force` 없이는 거부.
- 테스트: 재작성 뒤 `section0.xml` 을 파싱해 1~3절 밖 최상위 문단의 `ET.tostring` 이 원본과 같고, `BinData/image4~6`·`header.xml`·`content.hpf` 바이트 동일.

### 3.8 대조 JSON · 검토 HTML · 숫자 감사 — FR-08·09·11

- `hwpx_results_refresh_20260914.json`: `{"source": {"hwpx_sha256", "summary_run": meta.run 요약, "cases_date"}, "paragraphs": [{"section", "locator", "old_numbers": [...], "new_numbers": [...], "keys": ["corpora.NCS.total", …], "conditions": {"psm_all_grade3": false}, "format_collapsed": bool}], "tables": [{"caption", "rows", "cols", "changed_cells"}], "figures": [{"item", "size", "sha256"}], "audit": {"tokens": n, "unmatched": []}}` — 문장 본문은 넣지 않고 숫자 목록만.
- 검토 HTML(`docs/03-analysis/hwpx-results-refresh/review.html`): 표 7~13 과 그림 3장(PNG 로 변환해 인라인 data URI). 본문 문장 없음. 구/신 문장 병기본은 `data/hwpx-results-refresh/review_text.html`(비추적).
- 숫자 감사: 1~3절 문단·셀 텍스트에서 `\d[\d,]*(?:\.\d+)?%?` 토큰을 뽑아 정본 값 집합(총계·등급·분야·키워드·쪽수·비율(소수 1자리)·순위·권수·사고사례 집계·실제 쪽 번호)에 있는지 검사. 허용 목록: 연도(2014·2026), 등급 번호 1~3, "30개 키워드", "4개 분야", 목차 번호. 미일치 토큰이 있으면 exit 1 — **구 수치 잔존을 기계적으로 차단**.

### 3.9 문서·데이터 계보

- `docs/03-analysis/data/README.md`: `accident_case_pages.json`·`hwpx_results_refresh_20260914.json` 행 추가.
- `CLAUDE.md` 그룹 4: `hwpx_results_refresh.py` 항목(절 탐지·템플릿·표·그림·감사·비추적 산출물), `summary.json` 의 `groups[].pages`·`keywords[].corpora.*.groups` 설명.
- `TODOS.md` 5번(hwpx 구 수치) 갱신 — 기초보고서 제3장 1~3절 종결, 나머지 hwpx 파생본·PDCA 문서 5건은 그대로 이월.

## 4. 테스트 설계

| FR | 테스트 (`test_hwpx_results_refresh.py` = H, `test_semantic_keyword_recount.py` = T, 하니스 = S) |
|---|---|
| FR-10 | T `summary_payload_has_keyword_groups_and_group_pages`(fixture: 2그룹·마커 최대값 합·키워드×그룹 합 = 총계); S3h 키워드×그룹 합·pages 대조 |
| FR-12 | H `accident_case_pages_match_reseg_csv`(13쪽·5권·판정 집계 2/1/10) |
| FR-01 | H `locate_sections_by_heading_skips_toc`(fixture 에 목차 제목 중복) |
| FR-03 | H `paragraph_templates_branch_on_data`(공정안전관리 전부 등급3 / 아닐 때 두 문장; 보호구 60% 경계); H `set_text_keeps_first_run_format` |
| FR-04 | H `table_cells_replaced_structure_kept`(행·열·`borderFillIDRef` 불변, 내림차순), H `table13_rows_grow_and_addresses_renumbered` |
| FR-05 | H `figure_bytes_replaced_with_same_dimensions`(magick 있으면), `svg_has_all_values` |
| FR-06·07 | H `zip_rewrite_keeps_other_entries_and_refuses_overwrite` |
| FR-08·09 | H `audit_finds_stale_numbers`(구 수치 심은 fixture → unmatched), `diff_json_has_no_body_text` |
| 전체 | H `end_to_end_on_fixture_hwpx`(3절 있는 소형 hwpx → 새 파일 → 재파싱) |

커버리지 목표: fixture 로 로직 80%; 실문서 실행은 CI 밖(`data/` 비추적) — 대조 JSON 의 `audit.unmatched == []` 를 커밋 산출물 테스트(`CommittedArtifactsTests` 방식)로 확인.

## 5. 구현 순서 (Do)

1. T 테스트 → `summary_payload` 확장 → 정본 재실행(가드 통과) → S3h → 커밋.
2. `accident_case_pages.json` + H 테스트 → 커밋.
3. `hwpx_results_refresh.py` 골격: 절 탐지·`set_text`·표 교체·ZIP 재작성 (H 테스트 먼저) → 커밋.
4. 문단 템플릿 37개 + 표 7개 + 그림 3개 + 숫자 감사 → fixture e2e → 커밋.
5. 실문서 실행 → `data/반도체 기초보고서_20260914_정본.hwpx`, 대조 JSON, 검토 HTML → 숫자 감사 통과 → 커밋(추적 산출물만).
6. 문서·계보(§3.9) → `/pdca analyze` → report → ship.

## 6. 결정 기록

| 항목 | 결정 | 근거 |
|---|---|---|
| D1 키워드×분야 | `summary.json` 확장 | 연구책임자 2026-09-14 |
| D2 분야 쪽수 | 마커 최대값 합 (`groups[].pages`) | 연구책임자 2026-09-14 |
| D3 MSDS 합산 문장 | 독립 집계로 고쳐 씀 | 연구책임자 2026-09-14 (키워드 독립 원칙) |
| D4 구현 | 새 추적 스크립트, 이전 스크립트 import 안 함 | 연구책임자 2026-09-14 |
| D5 범위 | 1절·3절(사고사례) 포함 | 연구책임자 2026-09-14 |
| 표 13 판정 열 | "문장 수(글자 수)" → "판정" | 본문 인용·길이 서술 회피, 판정이 핵심 정보 |
| 출력 파일명 | `반도체 기초보고서_20260914_정본.hwpx` | 원본 보존, 날짜 = 정본 실행일 |
| 그림 2 탐지 | 캡션이 없어 `binaryItemIDRef`(image1)로 찾는다 (`find_picture(item=)`) | 실측 — 1절 그림에는 캡션 문단이 없다 |
| 문단 수 37 → 45 | 계획 실측표에 없던 숫자 문단 8개(1221·1225 등 2026-04 워크북 행 수치)도 재작성 | FR-09 전수 감사가 요구 |
| `--no-render` | 그림 없이 점검만 — 출력 HWPX·추적 대조 JSON 을 쓰지 않는다(`docs/` 경로 거부, 기본은 temp) | 저장소 관례(변형·부분 실행은 추적 경로 거부) |
| 대조 JSON `keys`·`conditions` | `keys` 는 값→키 역색인(`Facts.value_index`)으로 자동 산출(등급 번호 같은 작은 수는 제외), `conditions` 는 템플릿이 돌려주는 조건 결과 | FR-08, 갭 분석 G-1·G-2 |
| 구/신 문장 병기본 | `data/hwpx-results-refresh/review_text.html`(비추적, `--text-review-dir`) | 갭 분석 G-3, 계획 위험표 완화책 |
| `accident_case_pages.json` | `date` 2026-09-06(판정일), `event`(같은 사건 묶음)·`kind`(오탐 유형) 키, `gist` ≤ 30자 | 사건 수·오탐 유형 집계의 근거 |
| 2장 5절 범위 밖 숫자 | `audit.out_of_scope` 에 기록만(실패 아님) — 정본 실행에서 stale 0 | 계획 §2.2 |
| 렌더 결정론 | `magick` 버전·폰트에 묶이므로 sha256 기록까지 — 재현은 "같은 magick" 조건 | §3.6 |

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 0.1 | 2026-09-14 | 초안 | Claude (Opus 5) |
