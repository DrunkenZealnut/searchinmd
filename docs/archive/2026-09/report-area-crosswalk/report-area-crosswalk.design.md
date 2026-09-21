# 교과서 4영역 대응 변경을 정본 산출물까지 반영하는 설계 (report-area-crosswalk)

> **Summary**: 공용 대응표(`semantic_report_areas.py`, 『반도체 인프라 일반』 → 장비)는 그대로 두고, `hwpx_results_refresh.py` 의 교과서 절 템플릿을 **권수로 분기**하도록 고쳐(0권 영역 한 문장 · 2권 이상 영역은 교재 이름 나열 · 사고·SDS 문단을 장비 블록 뒤로 — 문단 슬롯 텍스트 교환, 구조 편집 없음) 원본(2026-09-11)에서 1·2·3단계를 `--force` 로 재생성한다. 정본 수치·해시·XLSX·`semantic_summary.json` 은 불변, 손 숫자 0, 장부·감사·결정론은 기존 규약 그대로. `CommittedDiffTests` 의 역사 mock 은 지우고, 09-19 Codex 문서 4건은 함께 커밋해 보관한다.
>
> **Project**: SearchInMD
> **Feature**: report-area-crosswalk
> **Plan**: `docs/01-plan/features/report-area-crosswalk.plan.md` (Approved — D1 (b)·D2 (b)·D3 W1·D4 무시·D5 (a))
> **Author**: Claude (Opus 5)
> **Date**: 2026-09-21
> **Status**: Revised in Do — 1.1 (2026-09-22): 슬롯 텍스트 교환 → 본문 소제목 "(4)" 재작성 + 장부 이동 (§3.2a)
> **Level**: Starter
> **Branch**: `feat/report-area-crosswalk`

---

## 1. 설계 목표

| # | 목표 | 검증 |
|---|---|---|
| G1 | 교과서 절의 영역 서술이 **권수로 분기**한다 — 0권(재료)·1권·2권 이상(장비) 모두 문장이 성립하고 "0권, 총 0쪽" 은 어떤 데이터에서도 나오지 않는다 | `TemplateTests` 양쪽 분기 + 문자열 부정 단언 |
| G2 | 사고·SDS/GHS 문단이 근거 교재(인프라 일반)가 있는 장비 블록 **뒤**에 놓이고(D3 W1), 재료 영역이 0권일 때 (4) 는 한 문장이다 | 슬롯 교환 조건 `slot` 기록 + E2E 문단 순서 단언 |
| G3 | "재료·인프라" 같은 손 문구가 템플릿에 남지 않고 영역명은 `AREA_LABEL`(→ `AREA_ORDER`)에서 나온다(D2 b) | `grep` 단언 + 리드 문단 테스트 |
| G4 | 재생성 정본이 새 대응 값으로 감사를 통과하고(미일치 0), 옛 대응 값(197쪽·9.6%)은 감사에서 **탈락**한다 | `AuditTests` 역방향 단언 |
| G5 | 정본 수치·해시 4종·XLSX·`semantic_summary.json`·대시보드 무변경; 교과서 절 밖의 ZIP 항목·문단은 바이트/구조 동일; 재실행 바이트 동일 | `git diff` 0 + `check_untouched` + 재실행 비교 |
| G6 | 추적 대조 JSON·`review.html` 이 새 대응이고 `CommittedDiffTests` 가 mock 없이 통과 | 테스트 |
| G7 | CLAUDE.md·README·data README·TODOS·메모리가 공용 대응표와 새 정본을 가리키고, 09-19 문서 4건이 보관된다(D5 a) | 문서 diff + `_INDEX.md` |

## 2. 아키텍처

### 2.1 구성 (변경 파일)

| 파일 | 변경 | 비고 |
|---|---|---|
| `semantic_report_areas.py` | **무변경** (09-19 그대로: `AREA_ORDER`·`AREA_DISPLAY`·`NCS_GROUP_TO_AREA`·`TEXTBOOK_GROUP_TO_AREA`·`TEXTBOOK_CLASSIFICATION_ROWS`·`area_for`) | 유일한 분류 출처 |
| `hwpx_results_refresh.py` | `corpus_facts` 가 영역별 `titles` 를 보존; `textbook_paragraphs` 의 리드·장비·재료·사고 문단 분기(§3.2); `conditions` 4건 추가 | 1단계 템플릿만 |
| `test_hwpx_results_refresh.py` | `CommittedDiffTests` mock 제거 + 새 조건 단언; `TemplateTests` 영역 분기 양쪽; `AuditTests` 역방향; `EndToEndTests` 문단 순서·0권 문장 | |
| `docs/03-analysis/data/hwpx_results_refresh_20260917.json`, `docs/03-analysis/hwpx-results-refresh/review.html` | 재생성 | 이름은 정본 실행일(20260917) 유지 — 정본 재실행 없음 |
| `data/반도체 기초보고서_20260917_정본.hwpx` (비추적) | 재생성; 기존 Polaris 재저장본은 `.9ef93187cd38f10e.bak` | D4 무시 — 본문 대조 없음 |
| `CLAUDE.md`, `README.md`, `docs/03-analysis/data/README.md`, `TODOS.md` | §3.7 | |
| `docs/{01-plan,02-design,03-analysis,04-report}/…semantic-report-area-symmetry…` → `docs/archive/2026-09/semantic-report-area-symmetry/` + `_INDEX.md` | 09-19 Codex 문서 4건 보관(D5 a), 분석 문서에 재저장본 주석 | 이 기능 문서와 서로 가리킴 |
| 09-19 승계분(`semantic_keyword_recount.py`·`hwpx_methods_bridge.py`·테스트 3건) | **무변경** | 이미 작업 트리에 있음 |

### 2.2 데이터 흐름 (기존 `refresh()` 안, 1단계 문단 루프)

```
semantic_summary.json corpora.교과서.groups[]  (교재별 9행, 불변)
        │  corpus_facts("교과서", TEXTBOOK_AREA.get)      ← semantic_report_areas.TEXTBOOK_GROUP_TO_AREA
        ▼
CorpusFacts.areas[영역] = {documents, pages, total, grades, titles[]}     ← titles 신설 (그룹명 = 교재 제목, 대응표 선언 순)
        │  textbook_paragraphs(f)  → (locator, text, conditions) × 21     (문단 수 불변)
        │      lead: 영역명 나열 = AREA_LABEL[AREA_ORDER]                  (D2 b)
        │      장비: documents ≥ 2 → 제목 나열 + 인프라 문장                (§3.2)
        │      slot "반도체 재료·인프라 분야는" / "특히 반도체산업의 대형 사고는" — 재료 documents == 0 이면 텍스트 교환 (D3 W1)
        ▼
find_paragraph(원본 첫머리) → set_text → 장부 touched → audit_numbers(value_index) → diff JSON / review.html / HWPX
```

문단 45·표 14·그림 3·layout 124/912/124 는 그대로다 — 구조 편집(삽입·삭제·이동)이 없고 슬롯의 **텍스트만** 바뀐다.

### 2.3 의존

- 슬롯 교환이 서식 중립인 근거: 원본 문단 796("반도체 재료·인프라 분야는")과 798("특히 반도체산업의 대형 사고는")은 `paraPrIDRef="10"`·`charPrIDRef="22"` 로 같다(2026-09-21 실측, 인접 본문 문단 790·792·779 도 동일). `set_text` 는 텍스트만 바꾸고 문단 속성·줄 배치 정책은 손대지 않는다.
- `find_paragraph` locator 는 원본(2026-09-11) 첫머리이므로 재작성 문장이 바뀌어도 유효(스크립트는 언제나 원본에서 실행).
- `AREA_LABEL` = `{"개발": "반도체 개발 분야", …, "재료": "반도체 재료 분야"}` (기존) — HWPX 산문 표기(띄어쓰기)이며 `AREA_DISPLAY`(Markdown 표, "반도체재료")와 뜻이 같다. D2 (b) 는 "재료·인프라" 를 버리고 이 두 표기로 통일하는 것이다.

### 2.4 재생성 절차 — Do 의 체크리스트

1. 코드·테스트 변경 후 `python3.13 -m unittest test_hwpx_results_refresh test_hwpx_methods_bridge` (fixture E2E 통과).
2. `python3 hwpx_results_refresh.py --no-render --diff-out /tmp/…/check.json` — 점검 실행: 감사 미일치 0, 슬롯 조건 확인.
3. `python3 hwpx_results_refresh.py --force` — 기존 `data/반도체 기초보고서_20260917_정본.hwpx`(Polaris 재저장본 `9ef93187…`)는 `<이름>.9ef93187cd38f10e.bak` 로 자동 보존(화면 출력만, 대조 JSON 밖). 출력 sha·백업 이름을 기록(분석 문서·TODOS 5).
4. 한 번 더 실행해 ZIP 항목·대조 JSON·`review.html` 바이트 동일 확인(결정론).
5. 교과서 절 밖 불변 확인: 두 정본(옛 `aa0f3453…` 는 git 의 대조 JSON 에만 있으므로, 대신 원본 대비 `check_untouched` 통과 + 대조 JSON 의 NCS·cases·methods·bridge·concentration 블록이 옛 JSON 과 동일함을 `git diff` 로 확인).
6. `git diff --stat` 에 `semantic_summary.json`·`semantic_recount_data.js`·XLSX 없음.
7. 전체 하니스(5종 + unittest 4모듈).

## 3. 상세 설계

### 3.1 사실 — `corpus_facts` 의 `titles`

```python
areas = {a: {"documents": 0, "pages": 0, "total": 0, "grades": {1: 0, 2: 0, 3: 0}, "titles": []} for a in AREA_ORDER}
for g in c["groups"]:
    area = group_to_area(g["name"]) ...
    areas[area]["titles"].append(g["name"])        # 교과서: 교재 제목 · NCS: 그룹명 1개 — 산문의 『』 나열에 쓴다. 정본 groups[] 는 이름순이므로 groups 를 대응표 선언 순으로 정렬해 접는다(1.1: 『기초기술 1』·『2』·『기초』 순)
```

`CorpusFacts.areas` 주석 갱신(`titles`). `value_index` 는 그대로(제목은 숫자가 아니다). 정본 결과: 장비 `["반도체 장비 유지보수", "반도체 인프라 일반"]`, 재료 `[]`.

### 3.2 템플릿 — `textbook_paragraphs`

공통 헬퍼(함수 안):

```python
def titles(area): return "·".join(f"『{t}』" for t in s.areas[area]["titles"])
def area_sentence(area, lead):                      # documents ≥ 1 전용 — 0권은 호출하지 않는다 (호출하면 ValueError: 0권 영역 문장 없음)
    a = s.areas[area]
    if a["documents"] == 0: raise ValueError(...)
    count = f"{a['documents']}권" + (f"({titles(area)})" if a["documents"] >= 2 else "")
    return f"{lead} {count}, 총 {fmt(a['pages'])}쪽으로 전체의 약 {pct(a['pages'], pages_total)}를 차지하였다."
def empty_area_sentence(area): return f"{AREA_LABEL[area]}로 분류한 교과서는 없었다."
materials_empty = s.areas["재료"]["documents"] == 0
infra_in_equipment = "반도체 인프라 일반" in s.areas["장비"]["titles"]
```

| locator (원본 첫머리, 불변) | 새 텍스트 | 분기 |
|---|---|---|
| `본 연구에서는 9권의 반도체 교과서를` | `f"… 교육 내용에 따라 {', '.join(AREA_LABEL[a].removesuffix(' 분야') for a in AREA_ORDER)} 분야로 재분류하였다. …"` → "반도체 개발, 반도체 제조, 반도체 장비, 반도체 재료 분야로" | 없음(D2 b) — 나머지 문장 그대로 |
| `반도체 개발 분야는`, `반도체 제조 분야는` | 기존 그대로(`area_sentence` 가 2권 이상일 때만 제목을 덧붙이는데 개발 3권·제조 4권이므로 **제목이 붙는다** — 아래 주) | |
| `반도체 장비 분야는` | `area_sentence("장비", …)` + 기존 유지보수 문장 + (`infra_in_equipment` 이면) " 『반도체 인프라 일반』은 반도체 생산에 필요한 화학물질, 특수 가스, 전력, 초순수, 폐수처리 등 각종 지원설비의 운용을 다루므로, 이 분야의 안전보건 교육은 장비 유지보수와 인프라 운용 양쪽에 걸친다." | `infra_in_equipment` |
| `따라서 장비 분야에서는 전기, 기계, 압력` | 기존 그대로 | |
| `반도체 재료·인프라 분야는` (슬롯 3) | `materials_empty` → **사고·SDS 문단 텍스트**(아래) / 아니면 `area_sentence("재료", "반도체 재료 분야는") + " 이 분야는 반도체 생산에 필요한 화학물질, 특수 가스, 전력, 초순수, 폐수처리, 각종 지원설비와 연결되기 때문에 안전보건 측면에서 매우 중요한 교육 영역이다."` | `materials_empty` |
| `특히 반도체산업의 대형 사고는` (슬롯 4) | `materials_empty` → `empty_area_sentence("재료")` = "반도체 재료 분야로 분류한 교과서는 없었다." / 아니면 사고·SDS 문단 텍스트 | `materials_empty` |

사고·SDS 문단 텍스트(양쪽 분기 공통, 영역명 없음): "특히 반도체산업의 대형 사고는 생산공정 자체뿐 아니라 화학물질 공급, 가스 공급, 배기, 폐수·폐가스 처리, 시설 유지보수 과정 등에서 발생할 수 있다. 따라서 **인프라 관련 교육에서는** GHS, SDS/MSDS, 화학물질 저장과 이송, 특수 가스 관리, 누출·화재·폭발·질식 예방과 비상 대응 등을 체계적으로 다룰 필요가 있다. 그러나 전체 교과서 분석에서 ‘물질안전보건자료’는 N건, ‘MSDS’ N건, ‘작업환경’ N건, ‘유해 인자’ N건에 그쳤다는 결과는 이 분야의 화학물질과 작업환경 교육도 상당한 보완이 필요함을 시사한다." ("재료·인프라 분야에서는" → "인프라 관련 교육에서는": G3)

주 — 제목 나열 규칙은 **영역 공통**(2권 이상이면 나열)으로 두어 장비만 특별 취급하지 않는다. 그 결과 개발·제조 문장도 "3권(『반도체 기초기술 1』·『반도체 기초기술 2』·『반도체 기초』), 총 639쪽…", "4권(『반도체 공정기초』·『반도체 포토에칭』·『반도체 박막확산』·『반도체 조립검사』), 총 1,002쪽…" 으로 바뀐다. 개발 문단의 기존 "『반도체 기초기술』과 『반도체 기초』는 …" 서술은 그대로 둔다(제목 표기 "반도체 기초기술" 은 1·2권 통칭이라 나열과 충돌하지 않는다). 이 확장은 정본 문장 4개(개발·제조·장비·재료)를 모두 데이터에서 만든다는 뜻이며, 감사에는 숫자가 늘지 않는다.

정본 산출(예상): 장비 "반도체 장비 분야는 2권(『반도체 장비 유지보수』·『반도체 인프라 일반』), 총 414쪽으로 전체의 약 20.1%를 차지하였다. 장비 유지보수는 … 증가할 수 있다. 『반도체 인프라 일반』은 … 양쪽에 걸친다."; 슬롯 3 = 사고·SDS 문단; 슬롯 4 = "반도체 재료 분야로 분류한 교과서는 없었다."

### 3.2a Do 에서의 수정 (2026-09-22) — 슬롯 교환을 버리고 장부 이동으로

구현 중 원본에 **본문 소제목 문단 "  (4) 반도체 재료·인프라 분야"** (top-level 398, paraPr 10·charPr 22 — 본문 문단과 같은 서식, 목차의 표기는 원래부터 "  (4) 반도체 재료 분야")가 있음을 실측했다. §3.2 의 슬롯 교환은 두 본문 문단이 모두 그 소제목 **아래**에 있어 사고·SDS 문단이 여전히 (4) 블록에 남는다 — W1("장비 문단 뒤로 이동")을 만족하지 못한다. 수정:

| 항목 | 1.0 (§3.2) | 1.1 (구현) |
|---|---|---|
| 소제목 "(4)" | 손대지 않음 | 새 locator `(4) 반도체 재료·인프라 분야` → `f"  (4) {AREA_LABEL['재료']}"` = "  (4) 반도체 재료 분야" (목차와 일치, D2 b), 조건 `area_label` |
| locator `반도체 재료·인프라 분야는` | 재료 0권이면 사고·SDS 텍스트 | 재료 0권이면 `empty_area_sentence("재료")`, 아니면 재료 문장 — 조건 `materials_documents`·`materials_empty` |
| locator `특히 반도체산업의 대형 사고는` | 재료 0권이면 0권 한 문장 | 양쪽 분기 모두 사고·SDS 텍스트("인프라 관련 교육에서는"); 조건 `relocate_after_equipment` |
| 이동 | 텍스트 교환(구조 편집 없음) | `relocate_accident_paragraph(root, section, located, _Ledger)` — 재작성된 사고·SDS 문단의 복제본(`MB.Piece("P")`, 원형 = 그 문단 자신) + 간격 `B`(장비 마지막 문단 뒤 빈 문단이 원형; fixture 처럼 빈 문단이 없으면 `P` 만)를 `따라서 장비 분야에서는 …` 문단(과 그 뒤 빈 문단) 뒤에 `_Ledger.insert`, 원본(과 그 뒤 빈 문단)을 `_Ledger.remove`. 2단계 장부 규약이라 `check_untouched` 의 순서 검사와 맞고, `drop_line_layout_cache` 가 삽입본의 캐시도 지운다 |
| 대조 JSON | `conditions.slot` | `relocation` 블록 `{locator, after, inserted 2, removed 2, numbers, keys}` + `paragraphs` 46(소제목 locator 추가) + `layout` 124·912·124 → **126·914·126** (+1 소제목 재작성, −1 원본, +2 삽입) |
| 문단 수 | 45 불변 | 46 (소제목 1 추가; 이동은 −1+1) |
| 정본 sha | — | `1b46474225e03233`(재실행 바이트 동일); 09-21 첫 재생성(슬롯 교환 판) `f2002e68…` 는 중간 산출물이라 백업을 지웠다 |

`refresh()` 의 문단 루프는 절마다 **먼저 전부 찾고 나서 쓴다**(`located`) — 재작성된 문단이 다른 locator 로 시작할 수 있어 순차 탐색이 2건을 잡던 문제(fixture 에서 발견). 결과 순서(정본 top-level 406~418): (3) 제목 · 장비 2권 문장 · 따라서 장비 … · **사고·SDS** · (4) 반도체 재료 분야 · 0권 한 문장 · 표 8 캡션.

### 3.3 조건 기록 — `conditions`

| locator | 키 | 정본 값 |
|---|---|---|
| `본 연구에서는 9권의 반도체 교과서를` | `page_basis`(기존), `area_labels: [AREA_LABEL[a] …]`, `empty_areas: [영역…]` | `["재료"]` |
| `반도체 장비 분야는` | `equipment_documents`, `equipment_titles`, `infra_in_equipment` | `2`, `[유지보수, 인프라 일반]`, `true` |
| `반도체 재료·인프라 분야는` | `materials_documents`, `slot` | `0`, `"accident_sds"` (아니면 `"materials"`) |
| `특히 반도체산업의 대형 사고는` | `slot` | `"materials_empty"` (아니면 `"accident_sds"`) |
| `반도체 개발 분야는` / `반도체 제조 분야는` | `documents`, `titles` | `3`/`4`, 제목 목록 |

대조 JSON 의 `paragraphs[].conditions` 에 그대로 실린다(본문 없음, 제목은 공개 값 — `books[].title` 이 이미 정본 JSON 에 공개돼 있다).

### 3.4 표 8 · 감사 · 불변

- 표 8: `area_table_rows(facts.school, with_grade_sum=False)` 무변경 — 재료 행 `재료 · 0 · 0 · 0 · 0 · 0 · 0.0%`, 장비 행 `장비 · 2 · 772 · 276 · 385 · 111 · 64.0%`, 합계 `9 · 1,207 · …`. `"0"` 은 `ALLOWED_TOKENS`, `"0.0%"` 는 `value_index` 의 `corpora.교과서.groups[재료].total/corpus` 로 해소.
- 감사: 새 문장의 숫자는 `2`(허용 토큰)·`414`·`20.1%`·N건(키워드)·`3`·`639`·`31.1%`·`4`·`1,002`·`48.8%` — 전부 `value_index` 키. 옛 값 `197`·`501` 은 새 대응의 인덱스에 **없다**(재료 pages 0, total 0) → 역방향 테스트가 이를 증명한다. `9.6%` 만은 `corpora.NCS.groups[개발].total/corpus` 와 우연히 같은 문자열이라 값 소속 감사로는 잡히지 않는다(실측 2026-09-21) — 감사의 알려진 한계이며 테스트가 그 충돌 키를 고정해 둔다. `STALE_PATTERNS` 에는 넣지 않는다(값이 아니라 대응이 바뀐 것이고, 197 은 정본 `books[]` 의 인프라 일반 pages 로 다른 문맥에서 정당하다).
- `largest_area` = 제조(불변) → "가장 큰 비중을 보였다" 분기 그대로.
- 불변: 문단 루프는 locator 집합이 같으므로 장부 `touched` 도 같다(124 문단·912 캐시). NCS·cases·2·3단계 블록의 대조 JSON 기록은 옛 JSON 과 동일해야 한다(§2.4-5).

### 3.5 재생성 산출물·계보

| 산출물 | 이름 | 계보 표기 |
|---|---|---|
| HWPX | `data/반도체 기초보고서_20260917_정본.hwpx` (덮어씀) | 대조 JSON `output_sha256` 갱신; 백업 `.9ef93187cd38f10e.bak` 는 화면 출력·TODOS 5 에만 |
| 대조 JSON | `docs/03-analysis/data/hwpx_results_refresh_20260917.json` (덮어씀) | data README 행에 "2026-09-21 교과서 영역 재대응(인프라 일반 → 장비, D1~D3) 재생성 — 정본 실행일은 그대로" ; 옛 내용은 git 이력(PR #20 시점) |
| review.html | 덮어씀 | 표 8 재료 0 행 |

파일 이름에 새 날짜를 붙이지 않는 근거: 이름은 `meta.run.generated_at`(정본 실행일)에서 오고 정본은 재실행하지 않았다(계획 §1.2). 대조 JSON 의 `source.summary_run` 이 그 정본을 가리킨다.

### 3.6 09-19 문서 보관 (D5 a)

- `git mv` 는 쓰지 못한다(미추적) — 4건을 `docs/archive/2026-09/semantic-report-area-symmetry/` 로 **이동**해 그 위치로 추가(`git add` 는 이름을 대고, 연구책임자 커밋 지시 뒤).
- 분석 문서 §Verification Evidence 의 HWPX 행 아래에 주석 1줄: "> 주(2026-09-21, report-area-crosswalk): 이 sha 는 2026-09-19 13:28 Polaris Office 재저장본이며 스크립트 출력(`aa0f3453…`, 대조 JSON `output_sha256`)이 아니다. HWPX 반영은 `report-area-crosswalk` 에서 했다."
- `_INDEX.md` 에 두 항목(09-19 기능, 이 기능) 추가, 서로 참조. `.pdca-status.json` 의 09-19 기능은 `archived` 로(비추적 파일).

### 3.7 문서

| 문서 | 변경 |
|---|---|
| `CLAUDE.md` 그룹 4 | (a) `semantic_keyword_recount.py` 항목 끝에: `--skip-xlsx-write`(보고서만 다시 쓰고 XLSX 는 건드리지 않음)와 `_report.md` 의 "4영역별 키워드·등급 분포" 절(NCS·교과서 대칭 표 + 교과서 9권 대응 근거표, `area_distribution_rows` 합 불변식) 한 문장; (b) 새 불릿 `semantic_report_areas.py` — 4영역 연구상 분류의 유일한 출처(`AREA_ORDER`·`AREA_DISPLAY`·두 대응표·근거표·`area_for` 실패 폐쇄), 『반도체 인프라 일반』 → 장비(2026-09-19 결정, 2026-09-21 D1 재확인), 새 교재는 여기 먼저; (c) `hwpx_results_refresh.py` 문단: "the textbook→area map (`TEXTBOOK_AREA`, the report's 연구상 분류)" → `semantic_report_areas.TEXTBOOK_GROUP_TO_AREA` (re-exported as `TEXTBOOK_AREA`), 교과서 영역 문장은 권수로 분기(0권 한 문장·2권 이상 제목 나열·재료 0권이면 사고·SDS 문단이 장비 블록 뒤 슬롯으로), 2026-09-21 재생성으로 재료 0권/장비 2권; (d) `hwpx_methods_bridge.py` 의 `NCS_GROUP_TO_AREA` "한 정의" → 공용 모듈 re-export; (e) Test Coverage 의 `TemplateTests` 설명에 영역 분기 추가. |
| `README.md` | 산출물 재생성 절: `--skip-xlsx-write` 한 문장; `hwpx_results_refresh.py` 한 줄 설명에 "교과서 4영역 대응은 `semantic_report_areas.py`" 추가 |
| `docs/03-analysis/data/README.md` | `hwpx_results_refresh_20260917.json` 행에 2026-09-21 재생성 사유·sha |
| `TODOS.md` | 후속 3: "C 교과서 보강 96.5%" 는 이제 장비 영역 2권의 등급 3 비중(111/115)이라는 주; 후속 5: 정본 sha 갱신, 백업 `.9ef93187cd38f10e.bak`, 1절 2) 문단·표 8 의 Polaris/한글 확인 항목 추가(`[→E2E]`); 09-19 기능·이 기능 한 줄 |
| 메모리 | `ncs-book-concentration.md` 의 정본 sha 갱신 + 새 파일 `report-area-crosswalk.md` |

## 4. 테스트 설계 (TDD — 실패 먼저)

| # | 테스트 | 위치 | 확인 |
|---|---|---|---|
| T1 | `test_area_titles_follow_the_crosswalk` | `AuditTests` | `f.school.areas["장비"]["titles"] == ["반도체 장비 유지보수", "반도체 인프라 일반"]`, 재료 `[]`, NCS 각 1개 |
| T2 | `test_textbook_area_paragraphs_branch_on_book_count` | `TemplateTests` | 정본: 장비 문장에 "2권(『반도체 장비 유지보수』·『반도체 인프라 일반』)"·"414쪽"·"20.1%"·인프라 문장; 슬롯 3 텍스트가 "특히 반도체산업의 대형 사고는" 로 시작; 슬롯 4 == "반도체 재료 분야로 분류한 교과서는 없었다."; 조건 `materials_documents 0`·`slot`; 어느 문단에도 "0권"·"0쪽"·"재료·인프라" 없음. 옛 대응(`mock.patch.dict(HR.TEXTBOOK_AREA, {"반도체 인프라 일반": "재료"})` 로 만든 facts): 장비 "1권, 총 217쪽", 슬롯 3 "반도체 재료 분야는 1권, 총 197쪽 … 9.6%", 슬롯 4 사고·SDS 문단, 조건 반전 |
| T3 | `test_lead_paragraph_names_areas_from_the_crosswalk` | `TemplateTests` | "반도체 개발, 반도체 제조, 반도체 장비, 반도체 재료 분야로 재분류" + `conditions["area_labels"]` |
| T4 | `test_audit_rejects_the_retired_materials_figures` | `AuditTests` | `audit_numbers(["… 197쪽 … 9.6% … 501건"], f) == ["197", "501"]`(9.6% 는 NCS 개발 비중과 충돌 — 그 키를 단언); 옛 대응 facts 로는 `[]` |
| T5 | `test_area_sentence_refuses_an_empty_area` | `TemplateTests` | `area_sentence` 를 0권 영역에 부르면 `ValueError` (헬퍼를 모듈 수준으로 올려 검사 가능하게) |
| T6 | `test_templates_branch_on_data` 확장 | `TemplateTests` | 옛 대응 facts 에서도 모든 템플릿 숫자가 감사를 통과 |
| T7 | `EndToEndTests.test_refresh_…` 확장 | | 출력 XML 에서 "특히 반도체산업의 대형 사고는" 문단이 "따라서 장비 분야에서는" 뒤·"반도체 재료 분야로 분류한 교과서는 없었다." 앞; `diff["paragraphs"]` 수 불변; 표 8 재료 행 `["재료","0","0","0","0","0","0.0%"]` |
| T8 | `CommittedDiffTests` | | mock 제거; `conds["반도체 재료·인프라 분야는"] == {"materials_documents": 0, "slot": "accident_sds"}`; `conds["반도체 장비 분야는"]["equipment_documents"] == 2`; 표 8 `changed_cells` 에 재료 행 0; `layout` 124/912/124 유지 |
| T9 | 리포지토리 grep 단언 | `TemplateTests` | `hwpx_results_refresh.py` 소스에 `"재료·인프라"` 문자열 없음(locator 상수는 원본 첫머리라 예외 — locator 튜플에만 허용) |

`SharedAreaCrosswalkTests`·`AreaCrosswalkTests`·09-19 의 `test_semantic_keyword_recount` 4건은 그대로.

## 5. 구현 순서 (Do)

1. `git status` 확인(작업 트리 = 09-19 승계분 + 계획·설계 문서). T1·T2·T3·T4·T5 를 먼저 써서 실패를 본다.
2. `corpus_facts` 의 `titles` → T1 통과.
3. `AREA_LABEL` 기반 리드 문단 → T3; `area_sentence`/`empty_area_sentence`/슬롯 교환/조건 → T2·T5·T6; 소스 grep → T9.
4. T7 E2E 확장 → 통과. `CommittedDiffTests` 는 이 시점에 **실패**(대조 JSON 이 옛 대응) — 정상.
5. `--no-render` 점검 → `--force` 재생성 → 재실행 동일 확인 → T8 갱신·통과.
6. 문서 §3.7, 09-19 문서 이동·주석·`_INDEX.md`, `.pdca-status.json`.
7. 전체 하니스: `node outputs/test-search-equivalence.js`, `test-dashboard-data.js`, `python3 outputs/test-recount-grades.py`, `run-core-logic-tests.js`, `test-sri.js`, `python3.13 -m unittest test_semantic_keyword_recount test_hwpx_methods_bridge test_hwpx_results_refresh test_expression_review`. 하니스 인용 수(84/390 등)는 실제 출력으로만.
8. Polaris 로 1절 2) 문단 4개·표 8 확인(Drive 업로드 주의) → TODOS 5 기록. 커밋은 연구책임자 지시 뒤, 파일 이름을 대고.

## 6. 결정 반영

| 결정 | 설계 반영 |
|---|---|
| D1 (b) 인프라 일반 → 장비 | 공용 대응표 무변경; 재생성으로 산출물이 따라온다 |
| D2 (b) "반도체재료"로 통일 | 리드 문단 영역명을 `AREA_LABEL` 에서 생성, "재료·인프라" 삭제(T3·T9) |
| D3 W1 | 슬롯 교환: 재료 0권이면 (4) 자리에 사고·SDS 문단, 마지막 자리에 0권 한 문장; 사고·SDS 문단의 영역 지시 "재료·인프라 분야에서는" → "인프라 관련 교육에서는" |
| D4 무시 | 재저장본 본문 대조 없음; `--force` 자동 백업만(§2.4-3) |
| D5 (a) | 09-19 문서 4건 보관 + 재저장본 주석 + `_INDEX.md` 상호 참조(§3.6) |

## 버전 이력

| 버전 | 날짜 | 내용 | 작성 |
|---|---|---|---|
| 1.0 | 2026-09-21 | 초안 — 권수 분기 템플릿·슬롯 교환·조건·감사·재생성 절차·테스트 9건·문서·09-19 문서 보관 | Claude (Opus 5) |
| 1.1 | 2026-09-22 | Do 수정 — 본문 소제목 "(4)" 실측으로 슬롯 교환 폐기, 소제목 재작성 + `_Ledger` 이동(§3.2a); 9.6% 값 충돌 주석(§3.4); 정본 sha `1b464742…`, layout 126/914/126 | Claude (Opus 5) |
