# Gap 분석: resegment — **Check-2** (Act-1 이후 재검사)

> 대상: 설계 문서 vs 구현 · 분석일: 2026-09-06 · 기준: 작업트리(미커밋)
> 이전: Check-1 (2026-09-06, Overall 79%) — `docs/03-analysis/resegment.analysis.md`
> **Act-2 (2026-09-06) 이후 주의**: 아래 Check-2 본문이 인용하는 `EXPECTED`(2,174쪽 · 1,503/524/147 · digest `d01970f1a6e9d1e8`)와 방식별 62/22/2권은 Act-2 **이전** 값이다. Act-2 가 G16(`pick_md` 동점 → 마커 수 2차 기준, R16m 동점 픽스처)을 해소해 현재 값은 2,173쪽 · 1,502/524/147 · digest `39d00effeb0dfe6c` · 정렬 61 / 마커 23 / 미해결 2권이다. 전후 비교는 「계획 기준 대 실측」의 Act-2 표를 보라. 출하 전 리뷰(2026-09-06) 뒤에는 CSV 가 10열→12열(`md자수`·`pdf자수`), `출처` 가 `text`/`text-fallback`/`label` 3값, `label_fallback_pages` 4→27, `public()` 람다→`public_path()`, R16 범위 a–o→a–z21 으로 더 바뀌었고, Act-3(마커 결손 하이브리드 배정, 연구 책임자 결정 ②) 뒤 현재 값은 2,189쪽 · 1,519/525/145 · digest `adb736e25db0c400` 이므로 아래 본문의 그 수치·이름은 검사 시점 기록으로만 읽어야 한다.

## Match Rate

| Category | Check-1 | Check-2 | 변화 |
|---|---|---|---|
| **Design Match** | 72% (25중 PASS 18 / CHANGED 7) | **97%** (30중 PASS 29 / 부분 1) | +25%p |
| **Architecture Compliance** | 86% (7중 6) | **100%** (7중 7) | +14%p |
| **Convention Compliance** | 78% (9중 7) | **100%** (10중 10) | +22%p |
| **Overall** | **79%** ⚠️ | **99%** ✅ | +20%p |

Check-1 의 CHANGED 7건은 전부 해소됐다. 설계 문서가 실행 결과를 따라잡았고, 하니스와 회귀 가드가 붙었다. Design Match 분모가 25→30 으로 는 것은 Act-1 이 이전에 "설계 초과 구현" 으로만 잡혀 있던 5개 계약(`marker_pages`, `unresolved_pages`, `page_grade_digest`, `check_expected`, `index_files`/`pick_md`)을 설계 §2 표에 편입했기 때문이다. 그중 `pick_md` 하나만 부분 인정이다(신규 G16).

## Act-1 항목별 확인

### G1 — 하니스 보강 ✅ 해소

`outputs/test-recount-grades.py` 에 R16j·R16k·R16l·R16m·R16n·R16o 6건이 추가됐다(요청은 j~o 6건, 전건 존재). R16 그룹은 총 15건이고 두 번째 소제목 `[R16] 재세그먼트 — Act-1: 산출물 쓰기·행 읽기·미해결·마크다운 선택·회귀 가드·main 완주` 아래 묶여 있다.

```
python3 outputs/test-recount-grades.py  →  결과: 340/340 PASS   (KNOWN ISSUE 0)
```

커버리지 재측정(Check-1 과 같은 `sys.settrace` + AST 로 함수 본문 실행가능 문장, 문서화 문자열 제외):

| | Check-1 | Check-2 |
|---|---:|---:|
| 실행가능 문장 | 334 | 363 |
| 하니스 실행 | 185 | **332** |
| **커버리지** | **55.4%** ❌ | **91.5%** ✅ |

함수별로 0% 였던 6개가 전부 올라왔다.

| 함수 | Check-1 | Check-2 |
|---|---:|---:|
| `write_outputs` | 0/14 | **14/14 (100%)** |
| `unresolved_pages` | 0/10 | **10/10 (100%)** |
| `pick_md` | 0/14 | **14/14 (100%)** |
| `index_files` | 0/6 | **6/6 (100%)** |
| `load_rows` | 0/17 | **17/19 (89%)** |
| `sha256_file` | 0/5 | **4/5 (80%)** |
| `main` | 12/77 | **78/86 (91%)** |
| `resegment_book` | — | 24/31 (77%) |

최저는 `resegment_book` 77%, `sha256_file` 80% 다. CLAUDE.md 최소선 60%·목표 80% 를 모두 통과한다.

### G2 — 회귀 가드 ✅ 해소

`resegment.py:56` 에 `EXPECTED = {'pages': 2174, 'page_g': {'1': 1503, '2': 524, '3': 147}, 'books': 86, 'unresolved_pages': 51, 'digest': 'd01970f1a6e9d1e8'}`. `page_grade_digest()`(`:243`)는 정렬된 (교재, 쪽, 등급) 전체의 sha256 앞 16자라 총계가 같아도 쪽→등급 재배정을 잡는다. `check_expected()`(`:249`)가 5개 항목을 대조하고, `main()`(`:555-559`)은 불일치 시 `sys.exit` 로 **쓰기 전에** 거부하며 `--force` 로만 넘어간다. `--limit` 실행에서는 가드를 건너뛴다(부분 실행이므로 정당).

`reseg_summary.json` 에 `page_grade_digest` 와 `meta.expected` 가 모두 실려 있고 값이 일치한다.

**실행 재현 검증(스크래치패드로 산출, 저장소 파일 미변경):**

```
python3.13 resegment.py --pdf-root … --out <scratch> --paged-dir <scratch>
→ 27.3초, EXPECTED 통과, 정상 기록
CSV  : diff 결과 추적본과 바이트 동일
JSON : run_at·pdf_root 제외 전 항목 동일
digest d01970f1a6e9d1e8 == meta.expected.digest == 추적본
```

### G3·G4·G8~G11 — 설계 문서 ✅ 전건 해소

| Gap | 확인 위치 | 결과 |
|---|---|---|
| G3 `jump_pen` | design.md:37 | `jump_pen=0.06` 으로 정정. 스윕 근거("0.06~0.25 에서 83.3~84.1%", "0.12 는 이웃 쪽 반복 문장에서 이동을 막았다")까지 기재. `resegment.py:70` 시그니처와 문자 단위 일치 |
| G4 마커 우선 경로 | design.md:16-18, 39, 46, 49 | §1 흐름도에 `DENSE_MARKER_RATIO=0.8` 분기 추가, §2 에 `marker_pages` 계약 추가, `resegment_book` 에 `prefer_markers` 명시 |
| G8 `sentence_key`·짧은 정형구 | design.md:42-43 | 튜플 `(짧은 키, 전체 키)` 반환과 "10자 미만이면 줄 전체 일치 우선, 없으면 전체 키" 분기 기재. `resegment.py:195, 202` 와 일치 |
| G9 `aggregate`·`meta` | design.md:49 | `label_fallback_pages`·`unmatched_rows` 포함 전 키 나열, "`per_book`·`method_books`·`case_pages`·`meta` 는 `main()` 이 붙인다" 명시 |
| G10 `pages.json`·`rows_map` | design.md:61-62 | 파일명이 `<코드>.pages.json`, 내용 `{md, pdf, line_pages}`, `rows_map.csv` 6열이 §3 표에 등재 |
| G11 `per_book.page_g` | design.md:60 / `resegment.py:541` | 설계에 **page_g** 표기, 구현이 실제로 붙임. JSON 86/86 교재 전부에 `page_g` 존재 |

설계 §2 표의 나머지 계약도 구현과 대조했다: `norm_text` 기호 목록, `propagate` 양방향 전파, `page_texts` 마커 줄 제외, `check_alignment` 반환 키, `regrade_page` 위임, `load_rows(path, loader=None)`, `main()` 가드 순서(워크북→PDF 루트→마크다운 루트→PyMuPDF), `meta` 10개 키, `per_book` 12개 키 — 전부 일치.

사소한 표기 차이 1건: 설계는 `check_expected(summary, expected=EXPECTED)`, 구현은 `expected=None` 후 내부에서 `EXPECTED` 대입. 동작은 동일하므로 갭으로 세지 않는다.

### G5·G6·G13 — 결과 문서 ✅ 전건 해소, 수치 독립 검증 완료

- **G5**(results:91): "정렬로 결과를 만든 **62권의 정확도는 직접 측정된 적이 없다**", "83% 는 62권에 대한 낙관적 추정치일 가능성", "편향 방향은 모른다" 가 §4 에 들어갔다.
- **G6**(results:92): "해결 2,123쪽 중 **27쪽**(등급 1 25·등급 2 2)", "그중 **4쪽**은 본문조차 없어 구 등급(행 최저)", "CSV `출처` 열 `label`", "등급 3 영향 없음".
- **G13**(results:44): "해결 **84권 전부**에서 발생" 으로 정정("81권 중 80권" 삭제).

독립 재계산으로 확인했다.

| 주장 | 재계산 | 출처 |
|---|---|---|
| 폴백으로만 존재하는 쪽 27 | **27** (등급1 25 / 등급2 2) | `rows_map.csv` 7,547행에서 새쪽 공백 94행 → 42교재 78쌍 → 매칭 도달 쪽 제외 |
| 본문 없는 쪽 4 | **4** (`resolved` & `출처=label`) | `ncs_pages_reseg.csv` |
| 미매칭 94행 | **94** | 동일 |
| 정렬 62 / 마커 22 / 미해결 2 | **62 / 22 / 2** | `method_books` |

**등급 규칙 통일**(G6 후반)도 코드에서 확인했다. `resegment.py:421` 이 `elif rec.get('source') == 'label' and … r['grade'] < rec['grade']` 로 행 최저를 적용해 `unresolved_pages()`(`:381`)와 같은 규칙이 됐다. 주석에도 "등급은 행 최저(unresolved_pages 와 같은 규칙)" 라고 적혀 있다. R16l 이 이 규칙을 검증한다.

**CSV `출처` 열**: 10열 헤더 `영역,교재,페이지,등급,등급명,사고사례,등급사유,상태,출처,구라벨`, 2,174행, `text` 2,119 / `label` 55(미해결 51 + 해결 4). `label_fallback_pages: 4` 가 JSON 에 있다.

### G7 — CLAUDE.md·TODOS.md ✅ 해소

`CLAUDE.md:160` 이 전면 재작성됐다.

```
- **16 NCS workbook "pages" hit Excel's 32,767-char cell limit — and they are not
  truncated pages, they are multi-page blocks.** … the old reading — "an under-counting
  defect bounded to 등급3 ∈ [108, 112]" — is retired (audit C1, 2026-09-04).
  `resegment.py` re-places every hit on its real PDF page: 1,847 → 2,174 pages,
  등급3 108 (5.8%) → 147 (6.8%).
```

`TODOS.md:55` 에 "**절단 축은 폐기됐다**(2026-09-06) — 잘린 쪽이 아니라 여러 쪽을 묶은 라벨이었고, 실제 쪽으로 풀면 등급3이 108→147쪽으로 오히려 는다" 가 들어갔다. `TODOS.md:44` 에 재세그먼트 항목이 신설됐다.

`TODOS.md:42` 의 "등급3 108~112쪽(5.8~6.1%)" 은 남아 있으나, 2026-09-04 날짜가 붙은 이력 항목 안이고 바로 아래 :44 항목이 명시적으로 폐기를 선언한다. 이력 보존으로 판단해 잔존 갭으로 세지 않는다.

### G14·G15 — 계획 문서 ✅ 해소 (단, G15 의 **설명이 사실과 다름** → 신규 G16)

- **G14**: `plan.md:90` "84권 전체 10분 이내", `:97` "84권의 행이", design `§1` "PDF (84권)". 83 표기 소멸.
- **G15**: `plan.md:54` 에 "마크다운 89개 중 23개; 워크북 86권 기준 22권 — 나머지 1개는 워크북에 없는 파일" 이라는 설명이 추가됐다. 설명이 붙은 것은 맞으나 **내용이 틀렸다**(아래 G16).

### 컨벤션 ✅

| 항목 | 결과 |
|---|:---:|
| `grep -c "/Users/" docs/03-analysis/data/reseg_summary.json` | **0** |
| CSV 홈 경로 | 0 |
| `meta.expected.digest == page_grade_digest` | ✅ `d01970f1a6e9d1e8` |
| 재실행 산출물 == 추적 산출물 | ✅ CSV 바이트 동일, JSON `run_at` 외 동일 |
| 추적 산출물의 교재 본문 | 없음(등급사유 집계 문자열까지) |
| 본문성 산출물 격리 | `data/markdown/ncs_paged/` 전부 gitignore |
| 산출물 위치 | `docs/03-analysis/data/` ✅ |
| 의존성 격리 | `fitz` 는 `main()` 안, `openpyxl` 은 `load_rows` 안 ✅ |
| 하니스 픽스처 전용 | R16 전 15건이 PDF·워크북·네트워크 없이 실행 ✅ |
| CLAUDE.md·README 하니스 수 | 두 파일 모두 **340** ✅ |
| 하니스 통과 | 340/340, KNOWN ISSUE 0 ✅ |
| 커버리지 ≥60% | **91.5%** ✅ |

## Gap 목록

### 해소 (14건)

G1 · G2 · G3 · G4 · G5 · G6 · G7 · G8 · G9 · G10 · G11 · G13 · G14 · G15 — 위 절별 근거 참조.

### 잔존 (1건)

**G12 (Low, Check-1 에서 "선택").** 입력 sha256 이 워크북 1개뿐이다. `meta` 는 `pdf_root`·`md_root` 를 경로 문자열로만 기록한다. 계획 3.2 재현성 기준의 "입력 파일 sha256" 은 부분 충족이다. PDF 88개·마크다운 89개의 해시를 다 싣는 것이 과한지는 판단 사항이라 Check-1 의 평가를 유지한다.

### 신규 (3건)

**G16 (Medium) — `pick_md` 동점에서 마커 있는 마크다운을 버린다. G15 의 설명도 이 때문에 틀렸다.**

쪽 단위 마커를 가진 마크다운은 89개 중 **23개**이고, 측정해 보면 **23개 전부 워크북에 있는 교재**다. 계획 `:54` 의 "나머지 1개는 워크북에 없는 파일" 은 사실이 아니다. 실제 원인은 `pick_md` 의 동점 처리다.

`LM1903060205` 코드에만 마크다운이 2개 있다(85파일 / 84코드).

| 후보 | 줄 | 마커 | `pick_md` 점수 |
|---|---:|---:|---:|
| `LM1903060205_14v3_MI 장비 운영.md` | 1,975 | **0** | 26 |
| `LM1903060205_14v3_MI_장비_운영.md` | 2,233 | **84** | 26 |

`score()` 가 공백을 `_` 로 바꾼 뒤 비교하므로 두 파일은 정규화 후 같은 이름이 되어 점수가 동점이고, `max()` 가 glob 순서상 앞선 **마커 없는 쪽**을 고른다. 그 결과 이 교재는 `method='alignment'`, `md_markers: 0` 으로 기록된다.

영향을 실측했다.

| | 현재(마커 없는 파일) | 마커 파일 사용 시 |
|---|---|---|
| 이 교재 쪽수 | 20 (등급1 19 / 등급2 1) | 19 (등급1 18 / 등급2 1) |
| 전체 | 2,174쪽 · 1,503/524/147 | 2,173쪽 · 1,502/524/147 |
| 정렬 검증 표본 | 22권 20,888줄 · 정확 83.25% · ±1 94.86% | 23권 21,711줄 · 정확 **83.56%** · ±1 **94.94%** |

등급3 은 변하지 않는다. 총계 변동은 1쪽(0.05%)이지만 `page_grade_digest` 는 바뀌므로 고치려면 `EXPECTED` 갱신이 따라와야 한다. 부수 효과로 자기 검증 표본이 23권으로 늘어 G5 의 "62권 미측정" 이 61권으로 줄고 정확도가 0.3%p 오른다.

하니스도 이 경우를 덮지 않는다. R16m 은 접두 길이가 서로 다른 두 후보, 단일 후보, 후보 없음 세 가지만 검증하고 **동점 케이스가 없다** — 실데이터에서 실제로 발생하는 유일한 케이스가 빠져 있다.

**권고:** ① `pick_md` 동점 시 마커 수(또는 줄 수)로 2차 정렬. ② R16m 에 동점 픽스처 추가. ③ 계획 `:54` 의 23→22 설명을 실제 원인으로 교체. ④ 고칠 경우 `EXPECTED`·`reseg_summary.json`·결과 문서 §3.1 수치 동반 갱신. 고치지 않기로 하면 계획 `:54` 만 정정하고 결정을 기록.

**G17 (Low) — 계획 FR 표의 Status 가 전부 `Pending`.**

`plan.md:74-82` 의 FR-01~FR-08 여덟 줄이 모두 `Pending` 인데, 문서 헤더 `:9` 는 `Status: Done (2026-09-06)` 이고 §4 성공 기준 체크박스는 `[x]`/`[~]` 로 갱신돼 있다. 같은 파일 안에서 상태가 어긋난다.
**권고:** 문서 수정(FR-08 은 `--force`·`EXPECTED` 도입으로 재현 절차가 바뀌었으므로 명령줄도 함께 확인).

**G18 (Low) — 미확보 2권을 PDF 탓으로 적은 곳이 둘.**

측정: PDF 코드 **86개**(워크북 86권 전부 보유, 파일 88개), 마크다운 코드 **84개**(파일 89개). `per_book` 의 미해결 2권은 둘 다 `why: "no md"` 다.

- `plan.md:18` "원본 PDF(**86권 중 84권 확보**)"
- `plan.md:34` "워크북 86권 중 84권 확보(코드 기준)" — 바로 다음 문장의 "마크다운 없는 2권" 과 모순
- `resegment-results.analysis.md:31` "원본 PDF(…, **86권 중 84권 확보**)"

`plan.md:9`, `results:12`, `design.md:29` 는 "마크다운 없음" 으로 옳게 적혀 있다.
**권고:** 문서 수정 세 줄.

## 계획 기준 대 실측

| 기준 | 계획 | Check-1 | Check-2 | 판정 |
|---|---|---|---|:---:|
| 정렬 정확 | ≥ 85% | 83.25% | 83.25% (동일) | 미달 |
| ±1쪽 | ≥ 97% | 94.86% | 94.86% (동일) | 미달 |
| 미매칭 행 | ≤ 10% | 1.21% | 1.21% | 충족 |
| 처리 권수 | 84권 | 해결 84 + 미해결 2 | 동일 | 충족 |
| 성능 | 10분 이내 | 기재만(미재현) | **27.3초 실측** | 충족 |
| 재현성 | 같은 입력 → 같은 출력 | 미검증 | **CSV 바이트 동일** | 충족 |
| 커버리지 | ≥ 60% | 55.4% | **91.5%** | 충족 |
| 회귀 가드 | 타 스크립트 동급 | 없음 | **EXPECTED + digest + --force** | 충족 |

정확도 2건 미달은 변함이 없고 계획·결과 문서에 기록돼 있다. Check-1 이 지적한 "그 설명은 G5 때문에 절반만 성립한다" 는 문제는 결과 문서 §4 의 62권 문단으로 명시됐다.

## 결론

**Overall 79% → 99%.** Act-1 이 요구된 14개 갭을 전부 닫았다. 두 High 갭(하니스 커버리지, 회귀 가드)은 수치로 확인된다: 커버리지 55.4%→91.5%, 하니스 334→340건 전건 통과, 그리고 실제 재실행이 `EXPECTED` 를 통과하며 추적 산출물과 바이트 동일한 CSV 를 냈다. 설계 문서는 마커 우선 경로·`jump_pen` 0.06·10열 CSV·`per_book.page_g` 까지 구현과 일치한다.

신규 3건 중 실질은 G16 하나다. 나머지 둘은 문서 문구다. G16 은 결과 수치를 1쪽 움직이고 등급3 에는 영향이 없으므로 보고서를 다시 쓸 사유는 아니지만, **정확한 자료(마커 84개가 붙은 마크다운)를 가지고도 파일명 정렬 순서 때문에 덜 정확한 경로를 탄 것**이라 성격상 남겨 둘 종류의 결함은 아니다. 고치면 자기 검증 표본이 23권으로 늘어 G5 가 지적한 미측정 편향도 한 권만큼 줄어든다.

권고 순서:

1. **G16 ①②** — `pick_md` 동점 2차 정렬 + R16m 동점 픽스처. 고치면 `EXPECTED` 와 결과 문서 §3.1 을 함께 갱신.
2. **G18** — 세 줄 정정. 다음 독자가 "PDF 2권이 없다" 로 읽는다.
3. **G17** — FR 표 Status 갱신.
4. **G12** — 판단 사항. 유지하려면 계획 3.2 에 "워크북만" 이라고 범위를 좁혀 적는 편이 낫다.

참고 파일(절대경로):
`resegment.py`
`outputs/test-recount-grades.py` (2419~2589행)
`docs/02-design/features/resegment.design.md`
`docs/01-plan/features/resegment.plan.md`
`docs/03-analysis/resegment-results.analysis.md`
`docs/03-analysis/data/reseg_summary.json`
`docs/03-analysis/data/ncs_pages_reseg.csv`

---

<details><summary>Check-1 (2026-09-06, Overall 79%) — Act-1 이전 보고서</summary>

# Gap 분석: resegment
> 대상: 설계 문서 vs 구현 · 분석일: 2026-09-06 · 기준: 작업트리(미커밋, `resegment.py`·산출물·결과 문서 모두 untracked)

## Match Rate

| Category | Score | Status |
|---|---:|---|
| **Design Match** | **72%** (25항목 중 PASS 18 / CHANGED 7 / MISSING 0) | ⚠️ 미달 |
| **Architecture Compliance** | **86%** (7항목 중 6) | ✅ |
| **Convention Compliance** | **78%** (9항목 중 7) | ⚠️ 미달 |
| **Overall** | **79%** | ⚠️ 90% 미만 |

CHANGED 7건을 "구현은 되었으나 계약이 다름"으로 절반 인정하면 Design Match 86%, Overall 83%. 어느 기준으로도 90% 아래다. **MISSING(미구현)은 0건**이고, 어긋난 7건은 전부 구현이 설계보다 앞서 나간 경우다. 즉 이 갭은 코드 결함이 아니라 **설계 문서가 실행 결과를 따라가지 못한 것**이다.

## 설계 항목 검증

### §2 함수 계약 (10항목)

| # | 설계 항목 | 구현 위치 | 상태 | 비고 |
|---|---|---|:---:|---|
| 1 | `norm_text(s)` — NFC + 공백·기호 제거 | `resegment.py:56` `_STRIP` | PASS | 기호 목록이 설계와 문자 단위로 일치 |
| 2 | `grams(s, n=3)` | `resegment.py:61` | PASS | |
| 3 | `align_lines(lines, pages_text, *, …, jump_pen=0.12, …)` | `resegment.py:65` | **CHANGED** | 기본값 `jump_pen=0.06` (설계의 0.12는 코드 어디서도 쓰이지 않음). 키워드 전용 `*` 없음. 첫 후보 줄 동점 처리 `-1e-3*p` 는 설계에 없음 |
| 4 | `propagate(n, assigned)` | `resegment.py:126` | PASS | 정렬 줄 0개 → 전부 None 포함 일치 |
| 5 | `page_texts(lines, line_pages)` | `resegment.py:142` | PASS | |
| 6 | `sentence_key(contents)` → 단일 키 | `resegment.py:190` | **CHANGED** | 튜플 `(짧은 키, 전체 키)` 반환. "10자 미만이면 전체" 판단을 호출부(`match_rows`)로 넘김 |
| 7 | `match_rows(rows, lines)` — 전체→80→50→30 접두, 시트별 1:1, 부족 시 마지막 적중 | `resegment.py:197` | **CHANGED** | 규칙 본체는 일치. 10자 미만 정형구는 **줄 전체 일치**를 먼저 시도하는 분기가 추가됨(설계에 없음). 접두 길이 10자 미만이면 탐색 중단 |
| 8 | `regrade_page(text)` → (등급, 안전수, 조치수, 사유) | `resegment.py:232` | PASS | `RG.grade_page(text, word_boundary=False, normalize=False)`, 반환 형태 `regrade.py:298` 과 일치 |
| 9 | `check_alignment(lines, assigned)` → `{lines, exact, near}` | `resegment.py:169` | PASS | |
| 10 | `aggregate(books)` → summary 키 + `areas`·`unresolved`·`alignment_check`·`moved_rows`·`meta` | `resegment.py:238` | **CHANGED** | `meta` 는 `aggregate` 가 아니라 `main()` 이 붙인다(`resegment.py:511`). 설계 목록에 없는 `unmatched_rows` 를 추가로 낸다 |

### §1 데이터 흐름 (3항목)

| # | 설계 항목 | 구현 위치 | 상태 | 비고 |
|---|---|---|:---:|---|
| 11 | PDF 83권 / 마크다운 84권 | `main()` 실측 | **CHANGED** | 해결 84권(정렬 62 + 마커 22) + 미해결 2권 = 86권. `reseg_summary.json.method_books` |
| 12 | `load_rows()` → (시트, 영역, 교재, contents, 라벨, 사고사례, 구등급) | `resegment.py:283` | PASS | `reason` 추가(상위집합) |
| 13 | align → propagate → page_texts → match_rows → regrade → aggregate 순서 | `resegment_book()` `resegment.py:354` | PASS | |

### §3 산출물 (3항목)

| # | 설계 항목 | 구현 위치 | 상태 | 비고 |
|---|---|---|:---:|---|
| 14 | CSV 9열: 영역·교재·페이지·등급·등급명·사고사례·등급사유·상태·구라벨 | `write_outputs` `resegment.py:408` | PASS | 실제 헤더와 순서까지 일치. 2,174행 |
| 15 | JSON: 집계·영역별·**교재별 등급 분포**·이동·미매칭·alignment_check·사고사례 8쪽·입력 sha256·시각 | `resegment.py:504-514` | **CHANGED** | `per_book` 에 등급 분포가 없다(상태·방식·쪽수·이동·미매칭·정렬 검증만). 사고사례는 8쪽이 아니라 **13쪽**(`case_pages`). sha256 은 워크북 1개만, PDF·마크다운 루트는 경로만 |
| 16 | `data/markdown/ncs_paged/<교재>.pages.json` | `resegment.py:494` | **CHANGED** | 파일명이 `<교재>` 가 아니라 **`<코드>`**(`LM1903060101.pages.json` 등 84개). 내용은 `{md, pdf, line_pages}` 로 설계보다 넓다 |

### §4 테스트 (8항목)

| # | 설계 ID | 구현 위치 | 상태 | 비고 |
|---|---|---|:---:|---|
| 17-24 | R16a~R16h | `outputs/test-recount-grades.py:2419-2483` | PASS ×8 | 검증 내용이 설계 표와 일치. R16d·R16b 는 설계보다 조건이 하나씩 더 많다(적중 부족 시 마지막 적중, 앞쪽 우선). 전체 하니스 **334/334 PASS** |

### §5 보고서 반영 (1항목)

| # | 설계 항목 | 확인 | 상태 | 비고 |
|---|---|---|:---:|---|
| 25 | 표 11·12, 그림 3·4, 분야별 문장, 8쪽 목록, 절단 단락 | `data/교정-반도체 교재_피드백(0905)_수정목록0906.md` 에 "재집계" 7건 | PASS | hwpx 본문 반영 여부는 이 분석에서 검증하지 않음 |

## 설계 초과 구현

| 구현 | 위치 | 판단 |
|---|---|---|
| `marker_pages()` + `prefer_markers` + `DENSE_MARKER_RATIO=0.8` + `method_books` | `resegment.py:152, 354, 474, 506` | **정당하나 설계 누락**. 결과 86권 중 22권이 정렬이 아니라 마커로 만들어졌다. 설계 §1 흐름도에는 이 분기가 아예 없어, 문서만 읽으면 전 권이 DP 정렬 산출물이라고 오해한다 |
| `rows_map.csv` (행→쪽 대응표) | `resegment.py:500` | 계획 FR-05 의 "구→신 대응표" 실체. 설계 §3 산출물 표에 없음 |
| `index_files` / `pick_md` (LM 코드 기반 파일 짝짓기) | `resegment.py:311, 320` | 설계에 없는 입력 해석 계층. 마크다운이 여럿일 때 파일명 공통 접두로 고르는 규칙은 결과를 좌우하는데 문서·테스트 모두 없음 |
| `unresolved_pages` (미해결 교재의 행 최저 등급) | `resegment.py:339` | CLAUDE.md 의 "행이 엇갈리면 최저 등급" 규칙을 지킨다. 설계 §2 표에 없음 |
| `write_outputs` / `sha256_file` / `--limit` / `--paged-dir` | `resegment.py:395, 403, 428-429` | 통상적 I/O·디버그 편의 |
| R16i (마커 우선 경로 테스트) | `test-recount-grades.py:2488` | 설계 §4 에 없으나 위 마커 분기를 덮는 데 필요 |

## Gap 목록

### High

**G1. 하니스 커버리지 55.4% — CLAUDE.md 최소 60% 미달.** `resegment.py` 함수 본문의 실행 가능 문장 334개 중 하니스가 실제로 실행하는 것은 185개다(문서화 문자열 제외, `sys.settrace` 실측).

| 함수 | 실행/전체 |
|---|---:|
| align_lines / propagate / page_texts / aggregate / match_rows / check_alignment / marker_pages / resegment_book | 79~100% |
| `load_rows` | 0/17 |
| `index_files` | 0/6 |
| `pick_md` | 0/14 |
| `unresolved_pages` | 0/10 |
| `write_outputs` | 0/14 |
| `sha256_file` | 0/5 |
| `main` | 12/77 |

특히 `write_outputs` 는 **설계 §3 이 규정한 CSV 9열을 만드는 함수인데 단 한 줄도 실행되지 않는다.** 열 순서가 바뀌어도 하니스는 초록이다. 다른 스크립트에는 같은 목적의 `R13`(I/O·`main()` 경계) 그룹이 이미 있다.
**권고: 구현(하니스) 보강.** `R16j` write_outputs 열·정렬, `R16k` load_rows 열 위치·헤더 스킵, `R16l` unresolved_pages 최저 등급, `R16m` pick_md 접두 점수. 네 건이면 70%대로 올라간다(추정).

**G2. 회귀 가드가 없다.** `recount_grades.py` 와 `regrade.py` 는 내장 `EXPECTED` 검사가 어긋나면 쓰기를 거부하고, `summary.json` 은 `page_grade_digest` 로 총계가 같아도 쪽→등급 재배정을 잡는다. `resegment.py` 에는 둘 다 없다. 보고서가 이미 인용 중인 수치(2,174쪽 / 등급3 147쪽)가 재실행에서 조용히 달라져도 알 방법이 없다.
**권고: 구현 보강.** `EXPECTED` + 쪽→등급 지문을 `reseg_summary.json` 에 추가하고 `R14` 계열 가드로 묶을 것.

### Medium

**G3. `align_lines` 기본 `jump_pen`: 설계 0.12, 구현 0.06.** 호출부(`resegment.py:361`)가 기본값으로 부르므로 설계에 적힌 값은 실행되지 않는다. 결과 문서 §3.1 의 스윕(0.06~0.25에서 83.3~84.1%)이 실측 근거이고, 실행값 83.25%는 그 범위 하단과 일치한다.
**권고: 설계 수정** (0.06 으로 고치고 스윕 근거를 각주로).

**G4. 마커 우선 경로가 설계에 없다.** 위 "설계 초과" 첫 항목. 산출물의 상당 부분이 설계에 기술되지 않은 경로로 만들어진다.
**권고: 설계 수정** (§1 흐름도에 분기 추가, §2 에 `marker_pages` 계약 추가).

**G5. 자기 검증 표본과 산출 표본이 서로 배타적이다.** `alignment_check` 는 마커 보유 22권에서만 계산되는데(`resegment.py:487` `if dense`), 그 22권은 결과에 마커를 쓰므로 정렬 출력을 채택하지 않는다. 반대로 **정렬로 결과를 만든 62권의 정확도는 한 번도 측정되지 않았다.** 정확도가 가장 낮은 두 권(『반도체 장비 안전관리』 58.2%, 『클린룸 시설 운영』 65.8%)이 모두 마커 사용 책이라는 사실도 여기서 나온다. 결과 문서 §4 가 "마커 보유 22권에서만" 이라고 적었지만, 두 표본이 겹치지 않는다는 점과 편향 방향을 모른다는 점은 명시되지 않았다.
**권고: 문서 수정** (결과 문서 §4 한 문단). 판형이 규칙적이라 변환기가 쪽 마커를 찍을 수 있었던 책이 정렬도 쉬울 수 있어, 83.2%는 62권에 대한 낙관적 추정치일 가능성이 있다.

**G6. 미매칭 행이 라벨 공간 값을 쪽 공간에 섞는다.** `resegment_book` 은 매칭 실패 행에 `r['label']` 을 쪽 번호로 쓴다(`resegment.py:375`). 실측: 미매칭 94행이 42권에 걸쳐 78개 (교재, 라벨) 쌍을 만들고, **2,123 해결 쪽 중 27쪽(1.3%)이 이 폴백으로만 존재한다**(등급 1이 25쪽, 등급 2가 2쪽 — 등급3 영향 없음). CSV 의 `상태` 열은 교재 단위라 쪽 단위 출처를 구분할 수 없다. 또 이 폴백 쪽이 본문을 못 얻으면 등급을 **첫 행**에서 가져오는데(`resegment.py:386`), 같은 파일의 `unresolved_pages` 는 **최저 등급** 규칙을 쓴다. 같은 상황에 두 규칙이 있다.
**권고: 설계·구현 양쪽.** 쪽 단위 출처 플래그를 CSV 에 추가하거나, 최소한 결과 문서 §4 에 27쪽 수치를 적을 것. 등급 규칙은 한쪽으로 통일.

**G7. CLAUDE.md 가 폐기된 주장을 유지한다.** `CLAUDE.md:160` 은 여전히 "16 NCS pages were cut … 등급3 ∈ [108, 112]" 라고 단정하는데, 결과 문서 §3.5 와 `truncation-integrity.analysis.md` 배너가 이를 폐기했다. 같은 작업트리에서 CLAUDE.md 에 `resegment.py` 항목은 추가됐다(`CLAUDE.md:125`). `TODOS.md:55` 에도 "절단은 과소계상 축 … 등급3 +0~4쪽으로 유계" 가 같은 항목 안에 "절단 폐기" 와 나란히 남아 있다.
**권고: 문서 수정.** CLAUDE.md 는 에이전트가 규칙으로 읽는 파일이라 우선순위가 높다.

### Low

| ID | 내용 | 권고 |
|---|---|---|
| G8 | `sentence_key` 튜플 반환, 짧은 정형구 줄 전체 일치 분기가 설계에 없음 | 설계 수정 |
| G9 | `aggregate` 가 `meta` 를 내지 않고 `main` 이 붙임, `unmatched_rows` 키 누락 | 설계 수정 |
| G10 | `pages.json` 파일명이 `<교재>` 아닌 `<코드>`, `rows_map.csv` 가 설계 §3 에 없음 | 설계 수정 |
| G11 | `reseg_summary.json` 에 교재별 등급 분포 없음 (CSV 로 유도 가능) | 설계 수정 또는 `per_book.page_g` 추가 |
| G12 | 입력 sha256 이 워크북 1개뿐. PDF·마크다운은 경로만 기록 → 계획 3.2 "입력 파일 sha256" 부분 충족 | 구현 보강(선택) |
| G13 | 결과 문서 §3.1 "81권 중 80권에서 발생" 은 시제품 수치. 이번 실행은 **84권 전권**에서 이동 발생(rows_map 실측) | 문서 수정 |
| G14 | 설계 §1 "PDF (83권)", 계획 3.2 성능 "83권" vs 실측 84권 | 문서 수정 |
| G15 | 계획 §2.1·Risks "마커 보유 23권" vs 실측 22권. 마크다운 89개 중 23개가 쪽 단위인 것과 워크북 84권 중 22권인 것은 양립하지만 문서가 차이를 설명하지 않음 | 문서 한 줄 |

## 계획 기준 대 실측

| 기준 | 계획 | 실측 | 출처 | 판정 |
|---|---|---|---|:---:|
| 정렬 정확 | ≥ 85% | 83.25% (17,389/20,888) | `alignment_check.overall` | 미달 |
| ±1쪽 | ≥ 97% | 94.86% (19,814/20,888) | 같음 | 미달 |
| 미매칭 행 | ≤ 10% | 1.21% (94/7,769) | `unmatched_rows` | 충족 |
| 처리 권수 | 83권 | 해결 84 + 미해결 2 | `method_books` | 초과 |
| 성능 | 10분 이내 | 약 30초 | 결과 문서 기재, 재현 안 함 | 충족(추정) |
| 1:1 쪽 등급 일치 | 기준 없음 | 762/772 = 98.7% | `rows_map.csv` 재계산으로 확인 | — |

정확도 2건 미달은 계획 3.2·성공기준·결과 문서 §3.1 에 이미 기록되어 있고, 미달분이 결과에 반영되지 않는다는 설명(마커 보유 책은 마커 사용)도 붙어 있다. 다만 그 설명은 G5 때문에 절반만 성립한다.

결과 문서의 다른 수치는 전부 산출물과 맞는다. 2,174쪽 / 1,503·524·147 / 사고사례 13쪽·5권 / 이동 4,315행 / 미매칭 94행 / PDF 8,861쪽 / 해결 2,123쪽 / 등급3 0쪽 교재 57권 / 최다 42쪽(『반도체 장비 안전관리』, 147의 28.6%) / 분야별 396·324·561·893 — 모두 CSV·JSON 에서 재계산해 일치를 확인했다.

## 컨벤션·보안 점검

| 항목 | 결과 |
|---|:---:|
| `grep -c "/Users/" docs/03-analysis/data/reseg_summary.json` | **0** (`meta.pdf_root` = `~/DEV/…`, `resegment.py:510` 의 `public()`) |
| 추적 산출물의 교재 본문 | 없음. `등급사유` 최대 99자, 줄바꿈 0건, 형식은 "안전 1건 [부상(1)], 구체적 조치 언급 없음" |
| 본문성 산출물 격리 | `data/markdown/ncs_paged/` 84개 `pages.json` + `rows_map.csv` 전부 `.gitignore:10 /data/` 로 제외 확인 |
| 산출물 위치 | `docs/03-analysis/data/` ✅ |
| 의존성 | 표준 라이브러리 + `regrade` 임포트. `fitz` 는 `main()` 안(`:438`), `openpyxl` 은 `load_rows` 안(`:285`) → 하니스는 둘 다 없이 돈다 ✅ |
| 하니스 픽스처 전용 | R16 은 PDF·워크북·네트워크 없이 돈다 ✅ |
| CLAUDE.md·README 동기화 | `resegment.py` 항목 추가, R16 그룹 기재, 하니스 수 325→334 두 파일 모두 갱신 ✅ |
| 하니스 통과 | 334/334 PASS, KNOWN ISSUE 0 ✅ |
| 커버리지 ≥60% | **55.4%** ❌ (G1) |
| CLAUDE.md 내용 정합 | ❌ 폐기된 절단 해석 유지 (G7) |

보안상 노출 위험은 발견하지 못했다. 추적 대상 산출물 두 개는 등급·쪽 번호·집계뿐이고, 홈 경로와 본문은 없다.

## 결론

**Match Rate 79%로 90% 미만이다.** 다만 성격을 구분할 필요가 있다. 미구현 0건, 하니스 전건 통과, 결과 문서 수치는 산출물과 전부 일치한다. 어긋난 7건은 모두 구현이 설계보다 앞서 나간 것이고, 그중 둘(마커 우선 경로, `jump_pen` 0.06)은 실측으로 정당화되는 개선이다. 나머지 두 High 갭만 실제 부채다.

다음 단계 권고, 우선순위 순:

1. **하니스 4건 추가 (G1)** — `write_outputs`·`load_rows`·`unresolved_pages`·`pick_md`. 60% 최소선을 넘기는 최소 작업이고, 설계 §3 의 CSV 열 계약을 처음으로 검증하게 된다.
2. **회귀 가드 (G2)** — `EXPECTED` + 쪽→등급 지문. 보고서가 이 수치를 인용하는 한 다른 두 스크립트와 같은 수준이 필요하다.
3. **CLAUDE.md·TODOS.md 의 폐기 문구 정리 (G7)** — 한 줄짜리 문서 수정인데, 방치하면 다음 에이전트가 폐기된 [108, 112] 구간을 사실로 읽는다.
4. **설계 문서 갱신 (G3·G4·G8~G11)** — 마커 경로, 실제 기본값, 산출물 실물에 맞춰 §1~§3 을 고치고 §4 에 R16i 추가. 이것까지 하면 Design Match 는 90%대로 올라간다(추정).
5. **결과 문서 두 곳 정정 (G5·G6·G13)** — 검증 표본과 산출 표본이 겹치지 않는다는 사실, 폴백으로만 존재하는 27쪽, "81권 중 80권" 의 출처.

참고 파일 경로: `resegment.py`, `outputs/test-recount-grades.py` (2414~2495행), `docs/03-analysis/data/reseg_summary.json`, `docs/03-analysis/data/ncs_pages_reseg.csv`, `docs/03-analysis/resegment-results.analysis.md`.

</details>
