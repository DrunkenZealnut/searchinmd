# 의미 표현 사전 도메인 점검 완료 보고

> **Feature**: semantic-expression-review
> **Completed**: 2026-09-14
> **설계 항목 구현률 (Match Rate)**: 초기 96.0% → **Act-1 반영 후 100%** (부분 5 → 0)
> **PR**: #16 (미머지, https://github.com/DrunkenZealnut/searchinmd/pull/16)
> **승인**: 연구책임자

---

## Executive Summary

### 프로젝트 개요

| 항목 | 내용 |
|---|---|
| **Feature** | 2026-09-13 외부감사(M1·m3) 지목 사항을 근거로, 의미 재검산 사전 v1(포함 75·보류 19·제외 2)의 28.4%(동등·구체 표현 2,417 + 1,507 = 3,924건 / 13,799건)에 대한 도메인 정밀도 검증. 표현당 정밀도·95% 구간·κ를 측정하고 하한 < 0.8인 표현의 보류/조건부 처방을 정한다 — 사전 v2 변형·영향표·연구책임자 채택 결정을 담는다. |
| **기간** | 2026-09-14 |
| **커밋** | 기능 12개(사전 버전·표본·라벨·재정·v2 구성·채택·갭 분석·순위 통계) + ship 리뷰 수정분 — PR #16 29 커밋 중 |
| **변경 파일** | `semantic_keyword_recount.py` · `expression_review.py` · `test_semantic_keyword_recount.py` · `test_expression_review.py` · 데이터 6종 · 스펙 1건 · 분석 문서 2건 |

### 결과 요약

| 항목 | 값 |
|---|---|
| **설계 항목** | 63개 (일치 58 / 부분 5 / 다름 0) |
| **Match Rate** | 초기 96.0% → Act-1 후 100% |
| **갭(Check)** | 8건 (G-1~G-8) |
| **Act-1 처리** | 8건 전부 닫힘 |
| **표본** | 618건 (20개 표현 × 30건 + 전수 예외 `PSM` 16·`combustible` 2, seed 20260914, 사전 v1fix 에서 추출; `작업 환경` 은 30건 중 ? 5건이라 유효 25) |
| **코더** | A `claude-opus-5`(claude-cli), B `gpt-5.6-sol`(OpenAI 계열) · 일치율 97.2% · κ 0.965 |
| **재정** | 17건 (1: 8 · 2: 7 · ?: 2) |
| **하니스** | unittest 137(이 기능 98 = `test_semantic_keyword_recount` 70 + `test_expression_review` 28) · test-dashboard-data 68 · test-recount-grades 390 · 모두 통과 |

### 1.3 Value Delivered — 4관점 가치 분석

| 관점 | 내용 |
|---|---|
| **Problem** | 정본 13,799건 중 28.4%(동등·구체 표현 3,924건)는 LLM이 후보 결정한 값이고 검토·서명 기록이 없었다(감사 M1·m3 "점검 필요"). 표현별 정밀도를 재지 않은 채 14개 키워드가 혼합 문맥(사람 보호 vs 제품 오염관리·계측·설비)을 한 규칙으로 계산했다. |
| **Solution** | 22개 표현의 618건 표본을 2계열 AI 코더가 판정("이 문맥이 노동자 안전·보건인가")하고 Clopper-Pearson 정확 이항 95% 구간으로 정밀도를 측정했다. 하한 < 0.8 표현 13개에 대해 계층별 처방(보류 2개 `방진화`·`케미컬`, 조건부 4개 `방진복`·`장갑`·`X선`·`PSM`, 동의어 4개와 `가연성`·`combustible` 은 유지, `자외선` 은 이미 보류)을 정해 사전 v2를 구성했다. 불일치 17건은 연구책임자 재정. |
| **Function/UX Effect** | 포함 표현마다 정밀도·표본·판정자·근거(동반어 통계)가 남아 "왜 이 표현이 들어갔나"에 답할 수 있고, 대시보드 확장분(28.4%)이 검증된 값이 된다. 정본 사전이 v1→v1fix(결함 2건 수정)→v2(도메인 처방)로 진화한다. |
| **Core Value** | 사전 채택의 주체가 LLM 단독에서 "정밀도 측정 + 연구책임자 결정"으로 바뀐다. 감사 M1·m3 종결. NCS 12,506 → 11,517(−989, −7.9%; v1fix 12,310 대비 −793, −6.4%. 등급3 비율 20.8 → 21.9% 는 구성 효과), 의미 단위 키워드 재검산의 세 번째 정본이 확정된다. |

---

## 연구책임자 결정 기록

### 결정 1 (2026-09-14) — 결함 2건 정본 반영

| 항목 | 내용 | v1 vs v1fix |
|---|---|---|
| **(a) 영문 정확 키워드 단어 경계** | `PSM`·`MSDS` 를 정확 규칙에 단어 경계 추가(`_ascii_term`) | 교과서 `PSM` 13→9건(내부 문자 `EAPSM` 등 4건 제거) |
| **(b) 보류 표현의 정확 규칙 내 계수 차단** | `안전` 정확 규칙에서 `안전성`·`안전 마진/여유/재고/율/계수` 제외 | NCS 4,119→3,929(−190), 교과서 380→363(−17) |
| **영향** | v1fix = 새 정본(결정 3 전까지), 정본 재실행 → `EXPECTED["dictionary"]="v1fix"` 고정 | NCS 12,506 → 12,310(−196), 교과서 1,293 → 1,272(−21) |

### 결정 2 (2026-09-14) — v2 구성: 계층별 처방

| 처방 | 표현 | 정밀도 | 근거 | v1fix → v2 |
|---|---|:-:|---|---:|
| **보류** | 방진화 | 0/30 | 모두 제품 오염관리(클린룸 방지복) | 75→0 |
| **보류** | 케미컬 | 1/30 | 설비명(CCSS·펌프·필터) | 500→0 |
| **조건부** | 방진복 | 5/30 (동반어 5/10) | 착용·보호 동반어로 사람 보호 문맥만 | 165→65 |
| **조건부** | 장갑 | 22/30 (동반어 22/23) | 동반어로 O 유지 1.00 | 257→188 |
| **조건부** | X선 | 5/30 (동반어 4/5) | 방사선 경고·선량계 동반어 | 115→15 |
| **조건부** | PSM | 1/16 (동반어 1/2) | 정확 키워드지만 phase-shift mask 문맥 다수 | 16→2 |
| **유지** | 화학약품·화학 물질·누설·작업 환경·가연성·combustible | 0.17~1.00 | 동의어·정확 키워드에도 같은 공정 문맥 (비일관성 회피) | 그대로 |

결정 2는 **뜻이 다른 표현**(오염관리 장비·계측·설비)만 고친다(§5 해석의 단서 참고).

### 결정 3 (2026-09-14) — v2 채택

| 항목 | 값 |
|---|---|
| **정본 사전 변경** | `DEFAULT_DICTIONARY = "v2"` |
| **정본 수치** | NCS 11,517건 / 교과서 1,207건 · 등급3 2,525 / 115 · 등급3 비율 NCS 21.9% / 교과서 9.5% |
| **재실행** | 정본 재실행(`--force` 측정) → `EXPECTED` 재고정 → `rule_sha256` `c08e6353…` 변경 |
| **영향** | v1·v1fix는 이제 변형(추적 경로 거부, `EXPECTED` 불일치 기록만) · 표본은 v1fix 유지(`SAMPLE_DICTIONARY`) |
| **발표면** | 대시보드·README·CLAUDE.md·이전 보고서의 인용 수치 갱신(하니스 S1~S9가 검증) |

---

## 구현 요약

### 사전 버전 구조

`semantic_keyword_recount.py`:
- `DICTIONARY_VERSIONS = ("v1", "v1fix", "v2")`
- `DEFAULT_DICTIONARY = "v2"` (결정 3)
- `_V2_OVERRIDES`: 보류 2개·조건부 4개 — 결정 2 처방 (`(키워드, 키워드)` 키는 정확 규칙에 적용: `PSM`)
- `SAFETY_COMPANIONS`: 초기 12개(착용·보호·노출·피폭·화상·부상·위험·유해·안전·보건·재해·사고)
- 비정본 버전(`v1`·`v1fix`)은 추적 경로 거부, `EXPECTED` 불일치 기록만

### 표본 추출과 판정

`expression_review.py`:
- **표본**: 22개 표현(정본 출현 ≥50 비정확·정확 감사 지목·보류 probe) × 최대 30건 층화(NCS/교과서 비례)
- **표본 키**: `expression_review_key.json`(618항목, 파일·줄·표현만, 본문 없음)
- **시트**: `data/expression_review_sheet.json`(비추적, 앞줄·«매칭»줄·뒷줄·프롬프트)
- **코더**: A `claude-opus-5`(claude-cli), B `gpt-5.6-sol` · `family_guard` null
- **판정**: 질문 하나 "이 문맥이 노동자 안전·보건인가" (1/2/?)
- **재정**: `expression_review_adj.json`(17건, 1: 8 · 2: 7 · ?: 2)

### 정밀도 측정

`expression_review.py score`:
- **정밀도**: Clopper-Pearson 정확 이항 95% 구간 (stdlib `math.comb`+`bisect`)
- **하한 기준**: 0.8 (연구책임자 결정)
- **일치도**: κ 0.965 (표본 전체)
- **조건부 근거**: 동반어 통계(O/X 문맥 출현)를 `meta.companions.counts`에 기록

### 영향표

`expression_review.py impact`:
- **입력**: 86 NCS권 + 9 교과서권(v1fix 기준)
- **세 버전 메모리 집계**: v1·v1fix·v2 동시 실행(비추적)
- **영향표 항목**: 총계·등급 분포·키워드·표현·제외 사유별 계수
- **정본 열 검증**: v2 열 = `semantic_summary.json.totals.v2` (테스트 `test_impact_canonical_column_equals_canonical_summary`)

### 테스트 대응

`test_semantic_keyword_recount.py` + `test_expression_review.py`:
- **설계 항목 대응**: 63개 (일치 58 + 부분 5) — §5 갭 처리로 부분 5 → 0
- **새 테스트**: `test_semantic_keyword_recount.py` 53 → 70(DictionaryVersionTests·DictionaryVersionAuditTests), `test_expression_review.py` 28 신규(Sample/Score/Impact/CommittedArtifacts/CliAndEdge)
- **하니스 통과**: `unittest` 137/137(세 모듈) · `test-dashboard-data.js` 68/68 · `test-recount-grades.py` 390/390

---

## 영향표 — 의미 재검산 사전 v1 · v1fix · v2

| 항목 | v1 (2026-09-09) | v1fix (결함 수정) | v2 (도메인 처방) |
|---|---:|---:|---:|
| **NCS 총계** | 12,506 | 12,310 | 11,517 |
| NCS 등급1 | 5,057 | 4,946 | 4,378 |
| NCS 등급2 | 4,854 | 4,795 | 4,614 |
| NCS 등급3 | 2,595 | 2,569 | 2,525 |
| NCS 등급3 비율 | 20.8% | 20.9% | 21.9% |
| **교과서 총계** | 1,293 | 1,272 | 1,207 |
| 교과서 등급1 | 705 | 691 | 633 |
| 교과서 등급2 | 468 | 464 | 459 |
| 교과서 등급3 | 120 | 117 | 115 |
| 교과서 등급3 비율 | 9.3% | 9.2% | 9.5% |

**읽는 법**:
- v1fix − v1: 결함 2건 수정(영문 정확 키워드 단어 경계 + 보류 표현 정확 규칙 제외) — NCS −196(보류 표현 내부 190 + `PSM` 부분 문자열 6), 교과서 −21(17 + 4).
- v2 − v1fix (NCS): 도메인 처방 −793건 = 보류 2개 −551건 + 동반어 없음 −242건 (교과서 −65 = 24 + 41; 두 말뭉치 합 858). v2가 걷어낸 NCS 출현의 72%(568/793)가 등급1이므로 등급3은 −44에 그친다.
- **등급3 비율이 20.9→21.9%로 오르는 것은 개선이 아니라 구성 효과**(분모 감소). CLAUDE.md 예외 문단 참고.

### 키워드별 변화

| 키워드 | v1fix NCS | v2 NCS | 변화 | 원인 |
|---|---:|---:|---:|---|
| **화학물질** | 1,559 | 1,080 | −479 | 케미컬 보류 |
| **보호구** | 1,182 | 965 | −217 | 방진화 보류·방진복·장갑 조건부 |
| **방사선** | 204 | 113 | −91 | X선 조건부(두 말뭉치 합 115 → 15) |
| **PSM** | 8 | 2 | −6 | 조건부(phase-shift mask 제외; 교과서 9 → 1) |

---

## 갭 분석과 Act-1 처리

### 갭 분석 결과 (Check, 2026-09-14)

| 항목 | 값 |
|---|---|
| **설계 항목** | 63개 (일치 58 / 부분 5 / 다름 0) |
| **Match Rate (초기)** | 96.0% = (58 + 5×0.5) / 63 → Act-1 후 100% |
| **갭** | 8건 (설계 항목 갭 5 + 문서 정합 3) |

### Act-1 처리 (2026-09-14) — 8건 전부 닫힘

| ID | 갭 내용 | 처리 | 상태 |
|---|---|---|:-:|
| G-1 | `meta.adopted` null → 결정 3 기록 불가 | CLI `--adopted v2` 옵션 추가, `score --adopted v2` 재실행 | ✅ |
| G-2 | 설계 vs 구현의 `3` 라벨 처리 문구 불일치 | 설계 §3.3 문구 수정 | ✅ |
| G-3 | `ALPHA`·`kappa` 재정의 vs 재사용 | `ALPHA = score_coding.ALPHA` 로 단일 출처화 | ✅ |
| G-4 | `excluded_by_fix` 가 `안전성`/`안전_마진류` 미분리 | 패턴별 분리 계수(NCS 146/44, 교과서 14/3) | ✅ |
| G-5 | 설계 "openpyxl 불필요" vs 구현 필요 | 설계 문구 수정 | ✅ |
| G-6 | 분석 문서가 "v1fix 열" 인용 vs 실제 v2 | `expression-review.analysis.md` §6 갱신 | ✅ |
| G-7 | README 테스트 절이 `test_expression_review` 누락 | 한 줄 추가 | ✅ |
| G-8 | `.pdca-status.json` phase `"do"` vs Check 완료 | phase `"check"`, matchRate 96 갱신 | ✅ |

### Ship 리뷰 (PR #16) 반영

| 항목 | 추가 개선 (커밋) |
|---|---|
| **표본 키 결속** | `score` 가 키 digest 를 항목에서 다시 계산하고 항목 id 중복·시트 본문 sha256 을 검사; 실제 키에는 digest 없는 코더 파일도 거부 (`627d469`, `393c00d`) |
| **코더 라벨 결속** | 두 코더의 `prompt_sha256` 일치 + 지금의 `coder_prompt()` 해시 대조; 중단된 코더 파일(`grades`·`errors` 어디에도 없는 항목) 거부 (`2598cab`, `88b907b`, `d85d02e`) |
| **표본 키 기록** | 키가 실제 사용한 seed·표본 수·대상 표현을 적는다 (`988d0eb`) |
| **재정 파일** | 명시한 `--adj` 경로가 없으면 조용히 재정 없이 채점하지 않고 멈춘다 (`393c00d`) |
| **보류 귀속** | `impact.excluded_by_fix` 의 `안전성`/`안전_마진류` 를 출현별로 귀속(`_held_labels_by_occurrence`) — 같은 줄에 둘 다 있을 때 첫 패턴에 몰리지 않는다 (`393c00d`) |
| **변형 manifest** | 비정본 사전 실행은 `force` 가 아니라 `variant` 로 기록 (`393c00d`) |
| **정본 xlsx 보호** | 거부 테스트가 실제 정본 워크북을 덮어쓴 사고 → 임시 경로로 격리하고 정본을 깨끗한 트리에서 재실행 (`90284de`) |

---

## 한계와 이월

### 측정 한계

1. **표본 크기**: 30건의 구간 폭(±0.15)으로 경계 표현(`가연성` 28/30, κ 0.78)은 정밀도 0.8 라인에 걸려 있다. 계획이 허용한 **60건 2차 패스 후보**(TODOS 1(a)).

2. **사람 판정 비중**: 코더는 2계열 AI이고 재정 17건만 연구책임자 확인이다. 일치 601건의 정확성은 κ 0.965로 추정할 뿐 **사람 재검증 없음**(TODOS 1(c)).

3. **정확 키워드의 문맥**: 계획 §5 해석의 단서 — 측정은 **확장 표현에만** 적용됐고 정확 키워드 30개 자체의 문맥 정밀도는 재지 않았다. `화학약품`(0.17)·`누설`(0.23)이 저정밀도인 것은 확장 오류가 아니라 키워드 자체의 공정 문맥 비중이 높을 수 있다 — **미측정**(TODOS 1(b)).

4. **조건부 판정 창**: 시트 문맥(세 줄)이 조건부 규칙(같은 줄±1줄)과 같으므로 정밀도는 같은 창에서 측정됐다. 실제 페이지 블록 경계(마커)에서는 창이 더 좁을 수 있다.

5. **같은 줄 중복 표현**: 표본 618건 중 12쌍(24건)이 같은 줄의 같은 표현인데, 시트가 첫 번째 출현에만 «…» 표시라 두 출현의 뜻이 다르면 어긋날 수 있다(최대 3.9%). **후속**(TODOS 1(e)).

### 설계 이월

| 항목 | 상태 | 근거 |
|---|---|---|
| **`가연성` 60건 2차 패스** | 이월 (TODOS 1(a)) | 정밀도 0.93, κ 0.78 — 경계 사례 |
| **정확 키워드 문맥 정밀도** | 이월 (TODOS 1(b)) | 확장분만 검증했으므로 "정확 vs 확장의 품질 차이" 미측정 |
| **동반어 동음이의 패턴화** | 이월 (TODOS 1(c)) | `노출`(노광)·`보호`(보호막)의 공정 문맥 정의 |
| **표본 다시 표시 & 재판정** | 이월 (TODOS 1(e)) | 같은 줄 24건의 위치 보존 재판정 |
| **보류 표현 probe 규칙** | 해결 | `발화성`·`자외선` probe로 계수 0, 표본 문맥 수집 |

### 문서화

- **보류 정책**: `docs/superpowers/specs/2026-09-08-semantic-keyword-recount-design.md` "보류 정책" 절 추가 — 영문 일반어 / 계측·물성 문맥어 / 오염관리 장비어 / 가연성·발화성 구분
- **사전 버전 규약**: CLAUDE.md 그룹 4에 `DEFAULT_DICTIONARY`·버전 수명·변형 규약 명문화
- **계보 표**: `docs/03-analysis/data/README.md` 에 6개 파일(key·A·B·adj·scores·impact) 추적 용도 기록

---

## 재현 절차

### 1. 표본 추출 (결정론)

```bash
python3 expression_review.py sample \
  --ncs-root data_source/markdown/ncs \
  --school-root data_source/markdown/school-text
```
→ `expression_review_key.json` (digest `9713a337b4d94bac` 고정) + `data/expression_review_sheet.json` (비추적)

### 2. 코더 판정

```bash
# 코더 A (claude-cli)
python3 code_pages.py \
  --sheet data/expression_review_sheet.json \
  --coder A --backend claude-cli --model claude-opus-5 \
  --out docs/03-analysis/data/expression_review_A.json

# 코더 B (OpenAI 계열)
python3 code_pages.py \
  --sheet data/expression_review_sheet.json \
  --coder B --provider-env ~/.config/auditagent/.env \
  --out docs/03-analysis/data/expression_review_B.json
```
→ `expression_review_A.json` / `expression_review_B.json` (라벨만)

### 3. 불일치와 재정

```bash
python3 expression_review.py score --list-disagreements
```
→ 17건 조회 후 연구책임자 재정(결정 2 검토) → `expression_review_adj.json` 작성

### 4. 정밀도 & 동반어

```bash
python3 expression_review.py score --adopted v2
```
→ `expression_review_scores.json` (정밀도·CP 구간·κ·조건부·동반어 통계)

### 5. 영향표

```bash
python3 expression_review.py impact \
  --ncs-root data_source/markdown/ncs \
  --school-root data_source/markdown/school-text \
  --source-workbook data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx
```
→ `expression_review_impact.json` (v1/v1fix/v2 영향)

### 6. 정본 재실행

```bash
python3.13 semantic_keyword_recount.py --dictionary v2 ...   # 전체 옵션은 README 산출물 재생성 절 — 가드 통과 실행이 정본(--force 는 EXPECTED 를 새로 잴 때만)
```
→ `semantic_summary.json` (`meta.run.dictionary` = "v2", `expected` true, `force` false)

### 7. 테스트

```bash
python3.13 -m unittest test_semantic_keyword_recount test_expression_review test_hwpx_results_refresh
node outputs/test-dashboard-data.js
python3 outputs/test-recount-grades.py
```
→ 137(70 + 28 + 39) + 68 + 390 OK 확인 (이 기능 몫은 앞 두 모듈 98)

---

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 1.0 | 2026-09-14 | 계획·설계·갭분석·Act-1 정리 | Claude (Opus 5, bkit report-generator) |
| 1.1 | 2026-09-14 | 검수 — 재정 분포(1: 8·2: 7·?: 2), 결정 2 처방 수(보류 2·조건부 4), v1fix 영향(−196/−21), 하니스 수, ship 리뷰(PR #16) 반영 표를 실제 커밋 기준으로 정정 | Claude (Opus 5) |
| 1.2 | 2026-09-15 | CodeRabbit(PR #16) — 확장분 비율 28.4%(3,924/13,799), NCS 감소 −989(−7.9%), 표본 규칙(20×30 + 16 + 2), v2 제외 사유를 NCS 기준(551 + 242 = 793)으로, Match Rate 시점, 재현 명령에 세 번째 unittest 모듈 | Claude (Opus 5) |

