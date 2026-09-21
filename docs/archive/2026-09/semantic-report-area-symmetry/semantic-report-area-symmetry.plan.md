# Markdown 보고서 4영역 구성 대칭화 구현 계획

> **Summary**: 확정된 XLSX 통계는 그대로 두고, 재검산 Markdown 보고서에 NCS·교과서의 동일한 4영역 분포표와 교과서 연구상 분류 근거를 추가한다.
>
> **Project**: searchinmd
> **Version**: 1.0
> **Author**: Codex
> **Created**: 2026-09-19
> **Status**: Approved — 2026-09-19 사용자 실행 지시
> **Level**: Starter

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `semantic_keyword_recount_20260917_report.md`에 NCS와 교과서를 같은 4영역 틀로 비교할 수 있는 분포표를 추가하고, 교과서 9권의 영역 배정이 공식 분류가 아닌 연구상 비교 분류임을 독자가 확인할 수 있게 한다.

**Architecture:** 기존 확정 집계와 등급 판정은 건드리지 않는다. 4영역 대응을 작은 공용 모듈 한 곳에 두고, Markdown 생성기와 HWPX 생성기가 같은 대응을 읽게 한다. 보고서 재생성 시 XLSX를 쓰지 않는 명시적 실행 경로를 마련하여 확정 XLSX의 바이트와 통계 해시를 보존한다.

**Tech Stack:** Python 3.13+, 표준 라이브러리, `unittest`, Markdown, 기존 `semantic_keyword_recount.py` 생성 파이프라인

**Spec:** 이 문서의 §1~§4 및 2026-09-19 사용자 승인 범위 — “Markdown 4영역 표와 연구상 분류 근거만 보완하며 XLSX 확정 통계는 수정하지 않는다.”

## Global Constraints

- `data/semantic_keyword_recount_20260917.xlsx`는 읽기·대조만 하고 다시 쓰지 않는다.
- 키워드 사전, 검색 결과, 페이지 등급 및 NCS/교과서 총계는 재판정하지 않는다. 단, 사용자 결정에 따라 『반도체 인프라 일반』의 연구상 대응만 `재료`에서 `장비`로 바꾸어 교과서 4영역 표시값을 다시 합산한다.
- `docs/03-analysis/data/semantic_summary.json`, `docs/semantic_recount_data.js`, 대시보드 HTML 및 HWPX 본문은 이번 작업에서 갱신하지 않는다.
- Markdown 숫자의 분모는 현재와 동일한 의미 출현건수이며, 페이지 수나 고유 문장 수로 바꾸지 않는다.
- NCS 영역은 원자료 그룹 `반도체개발·반도체제조·반도체장비·반도체재료`를 따른다.
- 교과서 영역은 공식 교육과정 분류로 표현하지 않고, NCS 4영역과 비교하기 위한 연구상 대응으로만 표현한다.
- 『반도체 인프라 일반』은 전기설비·공조·유틸리티·설비 운용 중심의 내용에 따라 `반도체장비`에 대응한다.
- 확정 XLSX 기준 SHA-256 `e0c2b9933c66a7ba81bc07cd8d444f971e6ed5ee57630897e9cef0d4626b07a9`는 작업 전후 동일해야 한다.
- 기존 manifest의 `source_sha256`, `rule_sha256`, `detail_sha256`, `summary_sha256` 네 값은 모두 불변이어야 한다.

## Review Focus

- 새 교과서 제목이나 NCS 그룹이 추가되면 임의 영역으로 조용히 들어가지 않고 알 수 없는 그룹 오류로 중단되는가.
- 네 영역의 자료 수·출현·등급 1~3 합이 각 말뭉치 총계와 정확히 일치하는가.
- 『반도체 인프라 일반』의 `장비` 배정이 공식 분류가 아닌 연구상 대응이라고 명시되는가.
- Markdown만 갱신하는 실행이 XLSX·요약 JSON·대시보드·HWPX를 쓰지 않는가.
- HWPX와 Markdown이 같은 공용 대응표를 사용하여 교과서 배정이 다시 갈라지지 않는가.

---

## 1. 배경과 문제 정의

현재 HWPX 보고서는 NCS와 교과서를 각각 개발·제조·장비·재료의 4영역으로 집계하지만, `data/semantic_keyword_recount_20260917_report.md`는 말뭉치·키워드별 집계만 제공한다. 따라서 같은 분석 묶음 안에서 Markdown만 읽으면 영역별 분포를 확인할 수 없다.

또한 교과서의 4영역 배정은 `hwpx_results_refresh.py`의 별도 상수에만 있으며, 공식 분류가 아니라 교재 제목과 주요 교육 내용을 이용한 연구상 대응이다. 사용자 결정에 따라 『반도체 인프라 일반』은 전기설비·공조·유틸리티·설비 운용을 주 내용으로 보아 네 영역 중 `반도체장비`에 대응한다.

이번 작업은 이 표시·설명 비대칭만 해소한다. 통계 산식과 XLSX는 확정 상태로 유지한다.

## 2. 범위

### 2.1 포함 범위

- NCS 4영역 분포표를 Markdown 보고서에 추가한다.
- 교과서 4영역 분포표를 같은 열과 순서로 추가한다.
- 각 표에 자료 수, 전체 의미 출현, 등급 1·2·3 출현, 전체 출현 대비 비율을 표시한다.
- 교과서 9권의 영역 대응표와 분류 원칙을 Markdown에 명시한다.
- 『반도체 인프라 일반』의 장비 배정 근거와 연구상 대응의 성격을 설명한다.
- 영역 대응을 공용 모듈로 옮겨 Markdown과 HWPX 코드가 한 정의를 사용하게 한다.
- Markdown-only 재생성 경로와 XLSX 미변경 회귀 검사를 추가한다.

### 2.2 제외 범위

- XLSX 시트·셀·파일 내용 변경
- 30개 키워드 사전, 의미 표현, 포함·제외 규칙 변경
- 등급 1~3 판정 규칙이나 기존 페이지 등급 변경
- NCS 86권·교과서 9권의 개별 분석 재작성
- 『반도체 인프라 일반』 이외 교과서 8권의 기존 영역 배정 변경
- HWPX 본문·표·그림의 재생성 또는 문안 변경
- 대시보드, `semantic_summary.json`, HTML 분석 페이지 갱신
- 4영역 분류를 공식 NCS·교육과정 분류로 승격하는 주장

## 3. 확정 분류와 표시 원칙

### 3.1 NCS 대응

| 원자료 그룹 | 보고서 표시 영역 | 성격 |
|---|---|---|
| 반도체개발 | 반도체개발 | 원자료 그룹 |
| 반도체제조 | 반도체제조 | 원자료 그룹 |
| 반도체장비 | 반도체장비 | 원자료 그룹 |
| 반도체재료 | 반도체재료 | 원자료 그룹 |

### 3.2 교과서 연구상 대응

| 보고서 표시 영역 | 교과서 | 대응 근거 |
|---|---|---|
| 반도체개발 | 반도체 기초기술 1, 반도체 기초기술 2, 반도체 기초 | 제목과 주요 내용이 반도체 기초·소자·기술 이해에 중심을 둔다. |
| 반도체제조 | 반도체 공정기초, 반도체 포토에칭, 반도체 박막확산, 반도체 조립검사 | 제목과 주요 내용이 전·후공정 및 개별 제조공정에 중심을 둔다. |
| 반도체장비 | 반도체 장비 유지보수, 반도체 인프라 일반 | 장비 유지보수와 팹 전기설비·공조·유틸리티·설비 운용을 다뤄 장비·시설 계통에 가장 가깝다. |
| 반도체재료 | 해당 교과서 없음 | 네 영역 비교의 행은 유지하되 교과서 수와 출현은 0으로 표시한다. |

Markdown에는 아래 취지의 주석을 표 바로 앞에 둔다.

> 교과서 9권의 4영역 배정은 공식 교육과정 분류가 아니라 NCS 4영역과의 비교를 위해 교재 제목과 주요 교육 내용을 기준으로 구성한 연구상 대응이다. 『반도체 인프라 일반』은 전기설비·공조·유틸리티·설비 운용 중심의 내용에 따라 `반도체장비`에 배정하였다.

## 4. 목표 표와 불변 기준값

### 4.1 NCS 4영역 표

| 영역 | 자료 수 | 전체 | 등급 1 | 등급 2 | 등급 3 | 출현 비율 |
|---|---:|---:|---:|---:|---:|---:|
| 반도체개발 | 30 | 1,110 | 735 | 253 | 122 | 9.6% |
| 반도체제조 | 13 | 1,328 | 630 | 618 | 80 | 11.5% |
| 반도체장비 | 19 | 3,239 | 871 | 1,316 | 1,052 | 28.1% |
| 반도체재료 | 24 | 5,840 | 1,552 | 3,040 | 1,248 | 50.7% |
| 합계 | 86 | 11,517 | 3,788 | 5,227 | 2,502 | 100.0% |

### 4.2 교과서 4영역 표

| 영역 | 자료 수 | 전체 | 등급 1 | 등급 2 | 등급 3 | 출현 비율 |
|---|---:|---:|---:|---:|---:|---:|
| 반도체개발 | 3 | 136 | 114 | 22 | 0 | 11.3% |
| 반도체제조 | 4 | 299 | 243 | 52 | 4 | 24.8% |
| 반도체장비 | 2 | 772 | 276 | 385 | 111 | 64.0% |
| 반도체재료 | 0 | 0 | 0 | 0 | 0 | 0.0% |
| 합계 | 9 | 1,207 | 633 | 459 | 115 | 100.0% |

위 숫자는 새로 산출할 목표값이 아니라 확정 XLSX와 `semantic_summary.json`에서 이미 확인된 불변 기준값이다.
영역별 비율은 각 행을 소수 첫째 자리로 독립 반올림하므로 표시값의 합이 NCS 99.9%, 교과서 100.1%가 될 수 있다. 합계 행은 원자료 총계 기준으로 `100.0%`를 표시하고, 반올림 차이를 데이터 불일치로 처리하지 않는다.

## 5. 선택한 접근과 대안

| 접근 | 판단 | 이유 |
|---|---|---|
| 공용 분류 모듈을 만들고 두 생성기가 공유 | **채택** | 대응표 중복을 없애고 알 수 없는 교재를 실패로 처리할 수 있다. |
| `semantic_keyword_recount.py`에 기존 대응표를 복사 | 기각 | HWPX와 Markdown의 분류가 다시 갈라질 수 있다. |
| 생성 코드를 건드리지 않고 Markdown에 표를 수동 삽입 | 기각 | 다음 정본 재실행에서 표가 사라지고 생성물과 코드가 불일치한다. |
| 교과서에 새 공식 영역 값을 부여 | 기각 | 이번 분석에는 공식 분류 근거가 없으며 통계 범위를 넘어선다. |

## 6. 파일 구조와 책임

| 파일 | 변경 | 책임 |
|---|---|---|
| `semantic_report_areas.py` | 생성 | 4영역 순서, NCS 그룹 대응, 교과서 연구상 대응, 표시명, 분류 설명의 단일 출처 |
| `semantic_keyword_recount.py` | 수정 | 확정 결과를 영역별로 합산해 Markdown 표를 생성하고 report-only 실행을 지원 |
| `hwpx_methods_bridge.py` | 수정 | NCS 대응 상수를 공용 모듈에서 재노출하여 기존 호출부 호환 유지 |
| `hwpx_results_refresh.py` | 수정 | 로컬 교과서 대응표를 제거하고 공용 대응표 사용; HWPX 산출물은 재생성하지 않음 |
| `test_semantic_keyword_recount.py` | 수정 | 영역 합계·문구·알 수 없는 그룹·XLSX 미쓰기 검사 |
| `test_hwpx_methods_bridge.py` | 수정 | 기존 NCS 대응 인터페이스가 유지되는지 검사 |
| `test_hwpx_results_refresh.py` | 수정 | HWPX가 공용 교과서 대응을 사용하는지 검사 |
| `data/semantic_keyword_recount_20260917_report.md` | 수정 | NCS·교과서 4영역 표와 연구상 분류 설명 추가 |

## 7. 구현 작업

### Task 1: 4영역 분류의 단일 출처 확립

**Files:**
- Create: `semantic_report_areas.py`
- Modify: `hwpx_methods_bridge.py:36`
- Modify: `hwpx_results_refresh.py:69`
- Test: `test_hwpx_methods_bridge.py`
- Test: `test_hwpx_results_refresh.py`

**Interfaces:**
- Produces: `AREA_ORDER: tuple[str, ...]`, `AREA_DISPLAY: dict[str, str]`, `NCS_GROUP_TO_AREA: dict[str, str]`, `TEXTBOOK_GROUP_TO_AREA: dict[str, str]`, `TEXTBOOK_CLASSIFICATION_ROWS: tuple[tuple[str, str, str], ...]`, `area_for(corpus: str, group: str) -> str`
- Consumes: 현재 HWPX 코드에 하드코딩된 NCS·교과서 대응

- [ ] **Step 1: 공용 대응표의 완전성·실패 폐쇄 테스트를 먼저 작성한다.**

```python
def test_textbook_area_crosswalk_is_complete_and_explicit():
    assert set(TEXTBOOK_GROUP_TO_AREA) == {
        "반도체 기초기술 1", "반도체 기초기술 2", "반도체 기초",
        "반도체 공정기초", "반도체 포토에칭", "반도체 박막확산", "반도체 조립검사",
        "반도체 장비 유지보수", "반도체 인프라 일반",
    }
    assert TEXTBOOK_GROUP_TO_AREA["반도체 인프라 일반"] == "장비"
    assert AREA_DISPLAY["장비"] == "반도체장비"

def test_unknown_group_fails_closed():
    with self.assertRaisesRegex(ValueError, "대응되지 않은 교과서 그룹"):
        area_for("교과서", "새 교과서")
```

- [ ] **Step 2: 테스트를 실행해 공용 모듈이 없어 실패하는 것을 확인한다.**

Run: `python3 -m unittest test_hwpx_methods_bridge test_hwpx_results_refresh`

Expected: `semantic_report_areas` import 또는 새 상수·함수 부재로 FAIL.

- [ ] **Step 3: 공용 분류 모듈을 최소 구현한다.**

구현은 §3의 정확한 4영역·9권 대응과 설명을 상수로 제공한다. `area_for()`는 알 수 없는 말뭉치나 그룹에 기본값을 주지 않고 `ValueError`를 발생시킨다. 『반도체 인프라 일반』은 내부 키 `장비`, 표시명 `반도체장비`, 성격 `연구상 대응`을 함께 제공한다.

- [ ] **Step 4: HWPX 관련 두 모듈의 로컬 대응표를 공용 import로 교체한다.**

`hwpx_methods_bridge.NCS_GROUP_TO_AREA`는 기존 외부 호출을 깨지 않도록 공용 상수를 import해 같은 이름으로 재노출한다. `hwpx_results_refresh.py`는 `AREA_ORDER`와 교과서 대응을 공용 모듈에서 읽되 기존 HWPX 문장·수치·표 행은 바꾸지 않는다.

- [ ] **Step 5: HWPX 관련 회귀 테스트를 실행한다.**

Run: `python3 -m unittest test_hwpx_methods_bridge test_hwpx_results_refresh`

Expected: 기존 테스트 전체 PASS, 새 완전성·실패 폐쇄 테스트 PASS.

- [ ] **Step 6: 독립 검토 가능한 단위로 커밋한다.**

```bash
git add semantic_report_areas.py hwpx_methods_bridge.py hwpx_results_refresh.py test_hwpx_methods_bridge.py test_hwpx_results_refresh.py
git commit -m "refactor: centralize report area crosswalk"
```

### Task 2: Markdown용 4영역 집계와 표 생성

**Files:**
- Modify: `semantic_keyword_recount.py:2213`
- Modify: `test_semantic_keyword_recount.py:497`

**Interfaces:**
- Consumes: `area_for()`, `AREA_ORDER`, `AREA_DISPLAY`, 기존 `dashboard_payload(result)`의 `corpora.*.groups[]`
- Produces: `area_distribution_rows(result: AnalysisResult, corpus: str) -> list[dict[str, object]]`, `_area_distribution_markdown(result: AnalysisResult) -> list[str]`

- [ ] **Step 1: 영역별 합계 불변식 테스트를 작성한다.**

```python
def test_area_distribution_rows_reconcile_to_corpus_totals(self):
    result = self.sample_result_with_all_area_groups()
    for corpus in ("NCS", "교과서"):
        rows = area_distribution_rows(result, corpus)
        assert [row["area"] for row in rows] == list(AREA_ORDER)
        assert sum(row["documents"] for row in rows) == EXPECTED_DOCUMENTS[corpus]
        assert sum(row["total"] for row in rows) == EXPECTED_TOTALS[corpus]
        for grade in (1, 2, 3):
            assert sum(row["grades"][grade] for row in rows) == EXPECTED_GRADES[corpus][grade]
```

테스트 fixture에는 네 영역과 교과서 9개 그룹을 모두 넣어, 빈 영역이나 누락 그룹이 우연히 통과하지 않게 한다.

- [ ] **Step 2: Markdown 구조·문구 테스트를 작성한다.**

```python
def test_report_has_symmetric_area_tables_and_research_crosswalk_notice(self):
    report = render_report(self.sample_result_with_all_area_groups())
    section = report.split("## 4영역별 키워드·등급 분포", 1)[1]
    assert "### NCS" in section and "### 교과서" in section
    assert section.count("| 영역 | 자료 수 | 전체 | 등급 1 | 등급 2 | 등급 3 | 출현 비율 |") == 2
    assert "공식 교육과정 분류가 아니라" in section
    assert "『반도체 인프라 일반』" in section
    assert "『반도체 인프라 일반』은 전기설비·공조·유틸리티·설비 운용" in section
    assert "| 반도체장비 | 2 | 772 | 276 | 385 | 111 | 64.0% |" in section
    assert "| 반도체재료 | 0 | 0 | 0 | 0 | 0 | 0.0% |" in section
```

- [ ] **Step 3: 테스트를 실행해 새 절 부재로 실패하는 것을 확인한다.**

Run: `python3 -m unittest test_semantic_keyword_recount`

Expected: 새 4영역 절·집계 helper 부재로 FAIL.

- [ ] **Step 4: 기존 payload 그룹 합계를 4영역으로 접는 helper를 구현한다.**

helper는 새 검색이나 새 등급 판정을 하지 않는다. 이미 생성된 `groups[]`의 `documents`, `total`, `grades`만 합산하며 다음 조건을 만족하지 않으면 보고서를 쓰기 전에 `ValueError`로 중단한다.

```python
assert sum(area.documents) == corpus.documents
assert sum(area.total) == corpus.total
assert sum(area.grades[g]) == corpus.grades[g]  # g = 1, 2, 3, unpaged
```

- [ ] **Step 5: `write_report()`에 대칭 절을 추가한다.**

삽입 위치는 `## 키워드별 집계` 다음, `## 키워드 순위 통계` 이전으로 고정한다. NCS와 교과서에 동일한 열·영역 순서를 사용한다. 표 하단에는 “단위: 의미 출현건수, 비율 분모: 해당 말뭉치 전체 출현”을 명시한다. 교과서 표 앞에는 §3.2의 연구상 대응 설명과 9권 대응표를 넣는다.

- [ ] **Step 6: 단위 테스트를 실행한다.**

Run: `python3 -m unittest test_semantic_keyword_recount`

Expected: 전체 PASS. 기존 키워드별 표·순위·해시 절의 내용과 순서는 새 절 삽입을 제외하고 불변.

- [ ] **Step 7: 독립 검토 가능한 단위로 커밋한다.**

```bash
git add semantic_keyword_recount.py test_semantic_keyword_recount.py
git commit -m "feat: add four-area tables to semantic report"
```

### Task 3: XLSX를 쓰지 않는 Markdown-only 재생성 경로

**Files:**
- Modify: `semantic_keyword_recount.py:2363`
- Modify: `test_semantic_keyword_recount.py`

**Interfaces:**
- Consumes: 기존 `run_census(...)`와 CLI의 canonical 입력 경로
- Produces: CLI 플래그 `--skip-xlsx-write`; `run_census(..., write_xlsx: bool = True)`

- [ ] **Step 1: XLSX 미쓰기 테스트를 작성한다.**

```python
def test_report_only_run_does_not_touch_existing_xlsx(self):
    xlsx = fixture_dir / "locked.xlsx"
    xlsx.write_bytes(b"confirmed-xlsx")
    before = (xlsx.read_bytes(), xlsx.stat().st_mtime_ns)
    run_census(**fixture_args, xlsx_out=xlsx, report_out=report, write_xlsx=False)
    after = (xlsx.read_bytes(), xlsx.stat().st_mtime_ns)
    assert after == before
    assert report.exists()
```

- [ ] **Step 2: 테스트를 실행해 `write_xlsx` 인자 부재로 실패하는 것을 확인한다.**

Run: `python3 -m unittest test_semantic_keyword_recount`

Expected: `unexpected keyword argument 'write_xlsx'`로 FAIL.

- [ ] **Step 3: 최소한의 쓰기 차단을 구현한다.**

`write_xlsx=False`일 때 `write_workbook()`만 건너뛴다. 통계 계산, EXPECTED 검사, manifest 작성, Markdown 생성은 기존과 동일하게 수행한다. CLI에는 `--skip-xlsx-write`를 추가하되 `--xlsx-out`은 계보 표시를 위해 계속 받는다. 다른 출력은 이번 실행에서 모두 지정하지 않아 쓰지 않는다.

- [ ] **Step 4: 쓰기 차단과 기본 동작 회귀 테스트를 실행한다.**

Run: `python3 -m unittest test_semantic_keyword_recount`

Expected: `write_xlsx=False`는 바이트·mtime 불변, 기본값 `True`는 기존 workbook 테스트 PASS.

- [ ] **Step 5: 독립 검토 가능한 단위로 커밋한다.**

```bash
git add semantic_keyword_recount.py test_semantic_keyword_recount.py
git commit -m "feat: support report-only recount output"
```

### Task 4: Markdown 재생성 및 불변성 검증

**Files:**
- Modify: `data/semantic_keyword_recount_20260917_report.md`
- Verify only: `data/semantic_keyword_recount_20260917.xlsx`
- Verify only: `docs/03-analysis/data/semantic_summary.json`
- Verify only: `data/반도체 기초보고서_20260917_정본.hwpx`

**Interfaces:**
- Consumes: Tasks 1~3의 공용 분류·Markdown 생성·XLSX 쓰기 차단
- Produces: 4영역 절이 추가된 Markdown 보고서 한 파일

- [ ] **Step 1: 보호 대상의 작업 전 해시를 기록한다.**

Run:

```bash
shasum -a 256 \
  data/semantic_keyword_recount_20260917.xlsx \
  docs/03-analysis/data/semantic_summary.json \
  data/반도체\ 기초보고서_20260917_정본.hwpx
```

Expected XLSX: `e0c2b9933c66a7ba81bc07cd8d444f971e6ed5ee57630897e9cef0d4626b07a9`.

- [ ] **Step 2: canonical 입력으로 Markdown만 재생성한다.**

Run:

```bash
python3 semantic_keyword_recount.py \
  --source-workbook data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx \
  --ncs-root data_source/markdown/ncs \
  --school-root data_source/markdown/school-text \
  --xlsx-out data/semantic_keyword_recount_20260917.xlsx \
  --skip-xlsx-write \
  --report-out data/semantic_keyword_recount_20260917_report.md \
  --previous-basis docs/03-analysis/data/reseg_summary.json \
  --page-maps data/markdown/ncs_paged \
  --reseg-csv docs/03-analysis/data/ncs_pages_reseg.csv
```

Expected: EXPECTED 가드 통과, Markdown만 갱신, XLSX·JSON·대시보드·HWPX 미쓰기.

- [ ] **Step 3: 보호 대상 해시가 모두 같은지 확인한다.**

Step 1의 세 파일을 다시 `shasum -a 256`으로 계산한다. 세 해시는 작업 전과 완전히 같아야 한다. XLSX의 mtime도 같아야 한다.

- [ ] **Step 4: Markdown의 기준 숫자와 분류 설명을 자동 검증한다.**

Run:

```bash
python3 -m unittest test_semantic_keyword_recount test_hwpx_methods_bridge test_hwpx_results_refresh
node outputs/test-dashboard-data.js
```

Expected: Python 전체 PASS, 대시보드 84/84 PASS. Markdown 표는 §4의 두 표와 일치하고 각 영역 합계가 말뭉치 총계와 일치한다.

- [ ] **Step 5: 변경 범위를 점검한다.**

Run: `git status --short && git diff --stat && git diff -- data/semantic_keyword_recount_20260917_report.md`

Expected: 코드·테스트·계획 문서와 지정 Markdown만 변경된다. XLSX·요약 JSON·대시보드·HWPX diff는 없어야 한다.

- [ ] **Step 6: 결과 문서 변경을 커밋한다.**

```bash
git add data/semantic_keyword_recount_20260917_report.md
git commit -m "docs: add symmetric four-area report tables"
```

## 8. 성공 기준

- [ ] Markdown에 NCS와 교과서의 4영역 표가 같은 열·순서로 존재한다.
- [ ] 두 표의 각 행과 합계가 §4의 불변 기준값과 일치한다.
- [ ] 교과서 9권의 연구상 대응이 모두 공개되고 누락·중복이 없다.
- [ ] 『반도체 인프라 일반』의 장비 배정 근거와 연구상 분류임을 표 인접 문구가 명시한다.
- [ ] 알 수 없는 교재명·그룹은 자동 추정하지 않고 생성 중단으로 처리된다.
- [ ] Markdown과 HWPX 생성 코드가 같은 공용 대응표를 사용한다.
- [ ] 확정 XLSX의 바이트와 mtime이 작업 전후 동일하다.
- [ ] 네 manifest 해시와 NCS 11,517건·교과서 1,207건의 등급 분포가 변하지 않는다.
- [ ] Python 회귀 테스트와 대시보드 84개 검사가 통과한다.

## 9. 위험과 완화

| 위험 | 영향 | 가능성 | 완화 |
|---|---|---|---|
| 교과서 연구상 분류가 공식 분류로 읽힘 | 높음 | 중간 | 표 앞에 연구상 대응임을 명시하고 9권 대응표와 『반도체 인프라 일반』의 장비 배정 근거를 함께 제공한다. |
| 공용 모듈 이동 중 HWPX 결과가 달라짐 | 높음 | 낮음 | 기존 상수 이름을 재노출하고 HWPX 테스트만 실행하며 HWPX 파일은 재생성하지 않는다. |
| Markdown 재생성 명령이 확정 XLSX를 덮어씀 | 높음 | 중간 | `--skip-xlsx-write`를 테스트하고 SHA와 mtime을 전후 대조한다. |
| 새 교재가 무의식적으로 기존 영역에 포함됨 | 중간 | 중간 | 알 수 없는 그룹은 `ValueError`; 공용 대응표 갱신 없이는 보고서를 쓰지 않는다. |
| 표의 합계는 맞지만 영역 간 재배분이 발생함 | 높음 | 낮음 | 9권 정확 대응과 §4의 영역별 기준값을 모두 테스트한다. |

## 10. 일정과 단계 경계

| 단계 | 산출물 | 상태 |
|---|---|---|
| Plan | 본 계획 문서 | 완료 |
| Design | 공용 분류 인터페이스·Markdown 절 위치·report-only 옵션 확정 | 사용자 승인 후 진행 |
| Do | 코드·테스트·Markdown 반영 | Design 승인 후 진행 |
| Check | 해시 불변·표 합계·회귀 테스트 검증 | 구현 후 진행 |
| Report | 변경 내용과 불변성 증거 기록 | Check 통과 후 진행 |

## 11. 관련 문서

- `data/semantic_keyword_recount_20260917_report.md`
- `data/semantic_keyword_recount_20260917.xlsx`
- `docs/03-analysis/data/semantic_summary.json`
- `hwpx_results_refresh.py`
- `semantic_keyword_recount.py`
- `test_semantic_keyword_recount.py`

## Version History

| Version | Date | Changes | Author |
|---|---|---|---|
| 1.0 | 2026-09-19 | 4영역 구성 대칭화 및 연구상 분류 공개 계획 수립 | Codex |
