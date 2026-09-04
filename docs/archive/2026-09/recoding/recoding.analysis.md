# Gap 분석: 재코딩 (recoding)

> 대상: `docs/archive/2026-09/recoding/recoding.design.md` vs 구현
> 분석일: 2026-09-04 · 기준: `c33e7a3` + 미커밋 작업 트리 (`feat/regrade-safety`)
> 연구 **결과** 문서는 별도다: `docs/03-analysis/recoding-results.analysis.md`. 이 문서는 설계-구현 갭(bkit Check)이다.
>
> | 회차 | Match Rate | 비고 |
> |---|---:|---|
> | Check-1 | **92.5%** (49.0 / 53) | 90% 게이트 통과. High 1(FR-1, 결정됨) · Medium 5 · Low 6 |
> | **Act-1 후** | **98.1%** (52.0 / 53) | Partial 7 → 2 해소 안 됨: FR-1(결정됨), 아카이브 git 추적(커밋 시 `git add` 필요) |
> | **Act-2 후** (FR-1 회차) | **99.1%** (52.5 / 53) | 코더 C = `claude-opus-5` 로 FR-1 충족. 남은 Partial: 아카이브 git 추적뿐 |

## ⚠️ 이 분석은 독립적이지 않다

구현한 세션이 띄운 gap-detector 에이전트(읽기 전용)의 판정을 그대로 옮겼다. 에이전트는 설계서·
기획서·코드·산출물·하니스를 직접 읽고 설계 §3 의 수치와 `regrade_impact.json` 행을 재계산으로
확인했으나, 구현자와 같은 저장소 상태를 공유한다. 첫 판독에서 리네임 전 설계서를 읽어 낸 파일명
갭 1건은 재확인 후 **철회**됐고 아래는 철회 반영본이다. Act-1 재집계(§9)는 자체 평가다.

## Executive Summary

**Match Rate 92.5%** = 49.0 / 53 (Partial 0.5 환산). 산식은 §6 말미.

| 심각도 | 건수 | 내용 |
|---|---:|---|
| High | 1 | FR-1 코더 계열 다양성 미충족 (연구 책임자 결정·문서화됨) |
| Medium | 5 | 분석 문서 수치 출처 주장, R15 어서션 수(44↔48), 아카이브 git 미추적, §2.2 코더 A 서술, `?` 층별 임계 경고 미구현 |
| Low | 6 | `version`=null, 1,028↔1,076, §6 예비집계 문단 낡음, TODOS 내부 모순, "절단 분쟁군 8쪽", §7 표에 R15q 누락 |

**결론**: 코드·시험·산출물은 설계대로 구현됐고 설계 §3 의 실측 수치(44/85/109/300 = 538, 지문
`68a4575ffff0def9`, 재현율 모집단 1,609, 전체 1,847)와 `regrade_impact.json` 의 V 행 두 개는
파일 대조로 정확히 일치한다. 남은 갭은 **하나의 요구사항 미충족(FR-1, 결정됨)과 문서 정합 결함**이며,
알고리즘·가드·기록 계층에서 설계와 어긋나는 곳은 발견되지 않았다. 하니스 280/280 PASS, KNOWN ISSUE 0건.

---

## 1. 요구사항(FR-1~FR-7) 대조표

| ID | 기획서 수용 기준 | 구현·산출물 | 판정 |
|:--:|---|---|:--:|
| **FR-1** | 코더가 `regrade.py`·`recount_grades.py`를 열람하지 않았음이 기록되고, **두 코더의 모델 계열이 다르다** | 전자는 충족 — `code_pages.py`에 등급 정의·동음이의·`SAFETY_TERMS`·`regrade` 문자열이 0건(R15m, 소스 검사). 후자는 **미충족** — `coding_A.json`/`coding_B.json` 둘 다 `model: gpt-5.6-sol`, `base_url: https://api.openai.com/v1`. `family_guard()`(`score_coding.py:482`)가 경고를 내고 `recoding_scores.json.family_warning`에 실린다 | **Partial** |
| **FR-2** | 코딩 로그에 항목별 호출이 남는다 | `code_items()`가 항목마다 한 호출, `raw[id]`에 `answer`/`tokens_in`/`tokens_out`/`latency_ms`/`retries`, `meta.context_isolated=true`. 538항목 전부 기록 | **Match** |
| **FR-3** | `coding_A/B.json`에 `model`·`version`·`prompt_sha256`·`temperature`·`run_at`·`context_isolated` | 6필드 전부 존재(`code_pages.py:246-253`). `version`은 두 실행 모두 **null**(OpenAI가 `system_fingerprint` 미반환) — `model_reported`가 대신 채워짐. 온도는 `0.0`으로 기록되고 `temperature_honored=false`가 병기됨 | **Match** (갭 #7) |
| **FR-4** | `score_coding.py`가 지문 검증을 통과한다 | `sample_digest = 68a4575ffff0def9`가 키·A·B 세 파일에 동일. `check_sample()` 통과, R15q가 커밋 산출물 삼각 검증. 지문 정의는 `(교재, 쪽, 군)`(`make_coding_sheet.py:194`) | **Match** |
| **FR-5** | `strata()` 출력에 층별 수치와 절단 포함/제외 민감도 | `score_coding.py:187-254`. 절단 16항목 전수 포함, 일치 14/16, 분쟁군 수정본 지지율 절단 포함 10/43(23%) vs 제외 9/35(26%) — 재계산으로 확인 | **Match** |
| **FR-6** | 표본에 등급2→1 층이 포함된다 | `boundary` 109쪽 전수(`strata()` 합집합, 106 ∪ 100). 키의 `population.strata.boundary = 109` | **Match** |
| **FR-7** | 표본에 등급1·2 층이 포함되고 거기서 나온 등급3이 재현율 추정에 쓰인다 | `recall` 300쪽(모집단 1,609). A 적중 99, B 적중 98 → 정확 초기하 구간 A [454, 612], B [449, 607] | **Match** |

FR 소계: 6 Match + 1 Partial = **6.5 / 7**

---

## 2. 설계 절별 대조표 (§0~§9)

| 절 | 설계가 말하는 것 | 코드·산출물이 하는 것 | 판정 |
|---|---|---|:--:|
| **§0** 제약 8건 | 제약 3(온도 1.0 미상속), 5(`group` 2값→4층), 7(`.env.local`에 OpenAI만), 8(python3.13) | 전부 반영. 제약 7이 그대로 FR-1 미충족으로 실현됨 | Match |
| **§1-1** 코더는 규칙을 보지 않는다 | 코딩 프로세스에 규칙 접근 경로 없음 | `code_pages.py`가 `coder_prompt`를 시트에서 읽고 자기 문자열을 갖지 않음. 소스 검사 R15m 통과 | Match |
| **§1-2** 한 항목 = 한 호출 | 컨텍스트 미공유 | `build_messages()`가 system+user 2메시지, 이력 없음 | Match |
| **§1-3** 제공자 교체 가능 | 코드가 아니라 설정을 바꾼다 | `PRESETS` 6종 + `AUDIT_LLM_*` 우선(`code_pages.py:63-111`) | Match |
| **§1-4** 원자료 보존 | 응답 원문·토큰·지연·재시도 | `raw` 전 항목 기록 | Match |
| **§2.1** CLI·플래그 | `--coder/--provider-env/--model/--base-url/--temperature/--seed/--limit/--resume/--dry-run/--sheet/--out` | `main()` 전부 구현(`code_pages.py:300-312`) | Match |
| **§2.1** env 우선순위 | `AUDIT_LLM_*` → 키 변수 프리셋 | `provider_config()` 동일 순서 | Match |
| **§2.1** 온도 미상속 | 소스에 `AUDIT_LLM_TEMPERATURE` 문자열 자체가 없다 | grep 0건. `DEFAULT_TEMPERATURE = 0.0` | Match |
| **§2.1** 온도·시드 400 폴백 | 그 인자만 빼고 즉시 재요청 + `*_honored=False` 기록, 뒤 항목은 처음부터 제외 | `call_chat()` `state` 딕셔너리로 파일 단위 공유(`:196-202`). 실제 실행 두 건 모두 `temperature_honored=false` 기록됨 | Match |
| **§2.1** 재개 | 원자적 갱신, 채점 항목 건너뛰기, 오류 항목 재질의, 다른 모델 거부, `--resume` 없는 덮어쓰기 거부 | `write_doc()` tmp+`os.replace`, `code_items():228-243`. B 실행에 `resumed_at` 1건 실증 | Match |
| **§2.1** 라벨은 확실할 때만 / 재시도 | 1·2·3·`?`가 홀로 정확히 하나, 429·5xx·네트워크 1·2·4·8·16초 5회 | `parse_grade()`(`code_pages.py:118-126`) + `BACKOFF`(`:59`). **추가로 408·409도 재시도**(설계에 없음, Extra E2) | Match |
| **§2.1** 산출물 스키마 | `"version": "<system_fingerprint>"` | 필드는 있으나 실제 두 파일 모두 `null` | **Partial** |
| **§2.2** 코더 A = A2 제3 제공자 | Gemini/DeepSeek 키가 들어오면 A를 돌린다 | 실제로는 `.env.local`의 `OPENAI_API_KEY`로 같은 모델 실행. §6-8이 기록하나 §2.2 본문·머리말은 미갱신 | **Partial** |
| **§3** 4층 합집합 정의 | 어느 쌍에서든 갈리면 분쟁, 어느 변형이든 3이면 전수 | `strata()`(`make_coding_sheet.py:199-216`) — `g3`가 `preds.values()` 전체 순회, 단조성 미의존 | Match |
| **§3** 실측 수치 | 44/85/109/300 = 538, 지문 `68a4575ffff0def9`, 모집단 1,609, 전체 1,847 | 키 파일과 완전 일치 (§4 표) | Match |
| **§3** 변형 라벨 소유권 | `variant_grid()`만 정의, 새 경로는 재타이핑 금지 | `RULE_PAIRS`가 `RG.*` 참조(`:100-101`), `score_census`는 `key_doc['variants']`를 읽음. 타이핑된 라벨은 구경로(`score_variants`, `population` 폴백)에만 | Match |
| **§3** `strata`/`draw` 순수함수, `N_CONTROL` 제거 | 합성 예측으로 시험 | R15e–h2. `N_CONTROL`은 전 소스에 0건(하니스의 부재 검사 1곳 제외) | Match |
| **§3** 키 스키마 | `pred` + `population`/`variants`/`rule_pairs`/`seed` | 전부 존재 (+ `n_recall`, Extra E3) | Match |
| **§3** 시트 스키마 | 등급·카운트·군 없음, `coder_prompt`·`notice` 포함 | `build_sheet()`(`:232-256`)/`main()`. R15i–i3 | Match |
| **§3** `sample_digest` = (교재, 쪽, 군) | 층이 늘어도 동작 | `make_coding_sheet.py:194` | Match |
| **§4.1** 두 경로 라우팅 | `is_census_key()`로 분기 | `main()`(`score_coding.py:705-710`), R15p | Match |
| **§4.1** 절 구성 1/2/3/3-1/4/5 | 6개 절 | `score_census()`가 정확히 그 순서로 출력(`:537-646`) | Match |
| **§4.1** 가드 둘 | 재현율층 등급3 예측 거부 + `check_population()` | `:530-534`, `:460-479`. R15o7·o8 | Match |
| **§4.1** JSON 기록 | "분석 문서의 숫자는 **전부** 이 파일에서 온다" | JSON은 씀. 그러나 §4.4 표의 다섯 부류는 JSON에 없다 | **Partial** |
| **§4.2** 정확 초기하 | Clopper-Pearson형, h=0 → (0,0,상한), 전수면 점 | `missed_interval()`(`:425-457`). R15n(1739/300/0 → 15)·n2·n3 | Match |
| **§4.2** `?` 는 유효 n에서 제외 | 재현율층에서도 | `_recall_est()`(`:507-512`) | Match |
| **§4.3** 신뢰구간 병기 | 코더 폭 [양쪽 3, 한쪽이라도 3] + 재현율 구간 | `band`/`recall_ci` 전 변형에 기록(`:638-642`) | Match |
| **§4.4** 절단 축 유지 | 기존 `strata()` 재사용 | `score_census`가 `strata(A,B,key,ids)` 호출(`:590`) | Match |
| **§4.4** 계열 가드 | 호스트 동일 시 FR-1 경고 | `family_guard()`(`:482-494`), 실제 경고 출력됨 | Match |
| **§5** 어휘 탐색 선행 | 표본보다 먼저 | `vocab-search.analysis.md`, `EXTRA_*_TERMS` 21종이 변형으로만(`regrade.py:138-144`) | Match |
| **§5** 산출물 내용 | 후보·영향·채택/기각 사유 | 4단계 방법론, 21종 채택 / 6종 보류 / 2종 기각, 등급 미사용 명시 | Match |
| **§6** 진행 상태 표 | 1~9 완료, "R15 44건" | 1~9 실제로 완료. **어서션 48건**. (파일명 참조는 리네임 후 정확) | **Partial** |
| **§6** B 단독 예비 집계 | "A가 없어 `score_coding.py`는 돌지 않는다" | 수치는 전부 정확(재계산 확인). A는 같은 날 완료됐고 채점도 돌았다 — 전제가 낡음 | **Partial** |
| **§7** R15 표 47 ID | 표에 열거된 ID 전부 존재하는가 | 47개 전부 존재. 하니스에는 R15q가 하나 더 있어 실제 48 | Match (Extra) |
| **§7** 뮤테이션 7종 | 전부 검출 | 7종이 지목한 어서션 ID가 모두 실재. 실행 기록이 없어 코드 검사로는 재확인 불가 | Match (미검증) |
| **§7** `[→E2E]` 표기 | 실 API 호출·완주·실 워크북 층 쪽수 | 표기 정확 | Match |
| **§8** 위험 완화 | `--resume`, 청크 재사용, `?` 비율 명시 + **층별 임계 경고**, 계열 가드 | `?` 개수·제외 수는 출력되나 **층별 임계 경고 미구현**. 회수는 1,028로 낡음 | **Partial** |
| **§9-1** 규칙 접근 경로 없음 | 코드로 확인 가능 | R15m (`code_pages.py`에 등급 정의·동음이의·`SAFETY_TERMS`·`regrade`·`AUDIT_LLM_TEMPERATURE` 0건) | Match |
| **§9-2** 코더 교체 = `.env` 변경 | | `--provider-env` + `--model`만 교체 | Match |
| **§9-3** 중단·재개 견딤 | | B 실행에 `resumed_at` 1건 | Match |
| **§9-4** 재현율 처음 측정 | | 13.2% [11.8, 14.8] (A 기준) | Match |
| **§9-5** meta 6필드 + 원자료 | | 538/538 전부 | Match |
| **§9-6** 같은 제공자면 스스로 경고 | | `family_warning` 실제로 실림 | Match |
| **§9-7** 옛 라벨 삼종 archive 존속 | 지워지지 않고 남는다 | 파일 존재·HEAD와 바이트 동일. 그러나 `docs/archive/2026-09/`는 **git 미추적(`??`)** | **Partial** |

---

## 3. 시험 대조 (설계 §7 ↔ R15 실제 어서션)

**설계 §7 표가 열거한 ID: 47개. 하니스 실제 ID: 48개. 설계에만 있고 구현에 없는 ID: 0개.**

| 설계 §7 행 | 열거 ID | 실재 | 비고 |
|---|---|:--:|---|
| 어휘 확장 | a, a2, b, c, d, d2 | 6/6 | `EXTRA_*` 21종 비중복, `variant_grid`↔`EXPECTED` 고정 |
| 4층 합집합 | e, f, g | 3/3 | 합성 예측 `_syn` 9쪽, p9가 단조성 미의존을 검사 |
| 추출 | h, h2 | 2/2 | 시드 결정성, `N_CONTROL` 부재 |
| 시트·키 | i, i2, i3 | 3/3 | 누출 문구(`진동`, `낮은 등급`) 부재까지 검사 |
| 호출기 설정 | j, j2, j3, j4, j5, j6 | 6/6 | 온도 미상속, 키·모델 없으면 거부 |
| 파싱 | k | 1/1 | 12사례 |
| 호출·기록·재개 | l, l2…l9 | 9/9 | meta 필드, 재개, 다른 모델 거부, 온도 폴백, 429, `--limit` |
| 소스 검사 | m | 1/1 | 8개 문자열 + `AUDIT_LLM_TEMPERATURE` |
| 초기하 | n, n2, n3 | 3/3 | |
| 전수 채점 | o, o2…o9 | 9/9 | |
| main·JSON | p, p2 | 2/2 | |
| 결과 dict | o10 | 1/1 | |
| 단조 시계 | l10 | 1/1 | |
| **(설계에 없음)** | **q** | — | 커밋된 `recoding_scores.json` ↔ 키 ↔ 라벨 삼각 검증 |

**뮤테이션 7종 매핑 검증**: 온도 env 상속→R15j5+R15m / 합의군 무작위→R15h / 재현율층 등급3→R15g / 0건 점추정→R15n+R15o4 / `?` 분모 잔류→R15o3 / 애매한 응답 라벨화→R15k+R15l+R15l5 / 재개 시 오류 미질의→R15l5. **지목된 어서션이 전부 실재.**

**하니스 실행 결과**: `python3 outputs/test-recount-grades.py` → `280/280 PASS`, KNOWN ISSUE 0건, exit 0.

---

## 4. 산출물·수치 대조

### 4.1 설계 §3 표 ↔ `coding_key.json`

| 항목 | 설계 §3 | 키 파일 실측 | 일치 |
|---|---:|---:|:--:|
| `disputed` | 44 (36 ∪ 39) | 44 | ✓ |
| `control` | 85 | 85 | ✓ |
| `boundary` | 109 (106 ∪ 100) | 109 | ✓ |
| `recall` | 300 | 300 | ✓ |
| 합계 | 538 | 538 | ✓ |
| 표본 지문 | `68a4575ffff0def9` | `68a4575ffff0def9` | ✓ |
| 재현율 모집단 | 1,609 | `population.recall_pool = 1609` | ✓ |
| 전체 쪽수 | 1,847 | `population.pages = 1847` | ✓ |
| 절단 항목 | 16 | 16 | ✓ |
| 시드 | 20260904 | 20260904 | ✓ |

규칙쌍별 분해 재계산: `baseline→D1+D2` 36쪽(108−72), `V 어휘 확장→D1+D2+V` 39쪽(129−90), 합집합 44쪽.

### 4.2 `regrade_impact.json` 변형 행

| 변형 | 과제서 명시 | 산출물 | 키 `pred` 등급3 | 일치 |
|---|---|---|---:|:--:|
| `V 어휘 확장` | {1247, 471, 129} | {1: 1247, 2: 471, 3: 129} | 129 | ✓ |
| `D1+D2+V` | {1366, 391, 90} | {1: 1366, 2: 391, 3: 90} | 90 | ✓ |

9개 변형 전부에서 `regrade.EXPECTED['dist']` = `regrade_impact.json.dist` = 키의 `pred` 등급3 카운트가 삼중 일치(`check_population()`이 실행 시점에도 확인).

### 4.3 코더 산출물

| | A | B |
|---|---|---|
| 모델 / 주소 | `gpt-5.6-sol` @ `api.openai.com/v1` | 동일 |
| 키 변수 / env | `OPENAI_API_KEY` / `.env.local` | `AUDIT_LLM_API_KEY` / `~/.config/auditagent/.env` |
| 채점 / 오류 | 538 / 0 | 538 / 0 |
| `temperature_honored` | **false** | **false** |
| `seed_honored` / `version` | true / **null** | true / **null** |
| 입력 토큰 | 901,656 | 901,656 |
| 재시도 합 | 0 | 0 |
| 최소 지연 | 725 ms | **−1,159 ms** (id 385, 설계 §6 기록과 일치) |
| `?` | 2 | 0 |

설계 §6의 B 단독 예비 집계도 전부 재현: 분쟁군 등급3 32 / 1·2 12, 합의군 79, 경계층 52, 재현율층 98, 규칙쌍별 현행 지지 25/36·27/39.

### 4.4 `recoding-results.analysis.md`의 수치 출처

문서 머리는 "숫자는 전부 `recoding_scores.json`에서 왔다"고 적었으나, 다음은 JSON에 없는 손계산이다(**전부 재계산으로 값 자체는 정확함을 확인**):

| 문서 위치 | 수치 | JSON |
|---|---|:--:|
| §2 | 불일치 29건 패턴 3→2 10, 1→2 8, 2→3 4, 2→1 3 | ✗ (전수 경로는 패턴을 출력조차 하지 않음 — 구경로에만 존재) |
| §3 표 전체 | 규칙쌍별 26/9, 25/11, 25/35(71%), 28/10, 27/12, 27/38(71%) | ✗ (콘솔에만) |
| §4.1 | 둘 다 3 = 52쪽, 그 현행 예측 등급2 49 / 등급1 3 | ✗ |
| §4.2 | 둘 다 3 = 94/300, 504.2, [429, 585], 등급1 43 / 등급2 51 | ✗ |
| §6 | 절단 일치 14/16, 둘 다 3 12, 절단 분쟁군 7 | ✗ (콘솔에만) |

---

## 5. 문서 정합 (CLAUDE.md, TODOS.md, 설계서 상태 표기)

**CLAUDE.md — 정합.** 작업 트리 버전이 다음을 정확히 반영한다.

- 어서션 수 `280` ✓ (실행값과 일치)
- `R15` 그룹 설명 추가 ✓, `code_pages.py`를 커버리지 규칙과 파이프라인 목록 양쪽에 추가 ✓
- 층 이름·쪽수 `disputed 44 / control 85 / boundary 109 / recall 300` ✓
- `code_pages.py` 서술(`post=` 주입, 온도 미상속, 라벨 파싱 규칙, `--resume` 모델 거부) ✓
- `recoding-results.analysis.md`, `recoding_scores.json`, `.env`/`.env.local` gitignore, 아카이브 이동 ✓
- 잔여 미세 사항: "`score_coding.population()` reads it" 서술은 이제 **구경로 전용**이다(전수 경로는 `check_population()` 사용). 오류는 아니나 조건이 빠져 있다.

**TODOS.md — 대체로 정합, 내부 모순 1건.** 재코딩 완료 항목·재현율 13% 실측·아카이브 이동·어휘 탐색 완료가 모두 반영됐다. 다만 같은 파일의 "5.8%는 상한이 아니다" 문단이 여전히 **"재현율은 여전히 측정된 적이 없다"**라고 적는데, 세 줄 위 열린것 2번은 "2026-09-04 처음 측정: 13%"라고 적는다.

**설계서 상태 표기 — 2건 낡음.** §6-6 "44건"(실제 48), §8·§9 "1,028회"(실제 1,076). 분석 문서 파일명 참조(§4.1, §6-9)는 리네임 후 `recoding-results.analysis.md`로 정확하며, `truncation-integrity.analysis.md`가 "Gap 분석"으로 시작하는 저장소 선례와도 일치한다. §6-8은 A의 OpenAI 실행을 정확히 기록했으나 §2.2 본문과 §6 예비집계 문단은 그 이전 상태로 남아 있다.

**아카이브 — `_INDEX.md`는 정확**(coding-v1 삼종, 무효 사유, 재채점 불가 사유, 후속 링크). 파일 3개는 HEAD 버전과 바이트 동일.

---

## 6. 갭 목록

### High

**#1 · FR-1 코더 모델 계열 다양성 미충족** — `coding_A.json:meta`, `coding_B.json:meta`
두 코더 모두 `gpt-5.6-sol` @ `api.openai.com`. FR-1 수용 기준 후반부("두 코더의 모델 계열이 다르다")를 충족하지 않는다.
**맥락**: 2026-09-04 연구 책임자의 명시적 결정(OpenAI 키만 확보). 설계 §6-8, `recoding-results.analysis.md` 머리·§7, `TODOS.md`, CLAUDE.md가 모두 기록하고, `score_coding.family_guard()`가 실행 시점에 경고를 찍으며 `recoding_scores.json.family_warning`에 문자열이 남는다. **상태: 결정됨/문서화됨.**
**권고**: 고치지 말 것. 다음 회차에서 Gemini 또는 DeepSeek 키로 `code_pages.py --coder A --provider-env .env.local --model <모델>`만 다시 돌리면 같은 지문이 유지된다. 그때까지 `recoding_scores.json`의 정밀도·재현율을 발표에 인용하지 않는 것이 유일한 운영 대응이다.

### Medium

**#2 · 분석 문서 수치의 출처 주장이 과하다** — `recoding.design.md:156`, `recoding-results.analysis.md:4`
설계 §4.1은 "분석 문서의 숫자는 전부 이 파일에서 온다(R15o10, R15p2)"고 하고 문서 머리도 같은 문장을 쓰지만, §4.4 표의 다섯 부류는 JSON에 없는 손계산이다. R15q의 삼각 검증도 이 값들에는 닿지 않는다.
**권고**: `score_census()`가 `res`에 네 덩어리를 추가하면 주장이 참이 된다 — (a) 불일치 패턴 `Counter((A,B))`, (b) 규칙쌍별 지지율(3절이 이미 계산하고 버리는 값), (c) 절단층 통계(`strata()`가 출력만 하는 값), (d) "둘 다 3" 재현율 추정. 그 뒤 R15o10을 확장한다. 대안으로 설계 문장을 "핵심 수치는"으로 낮출 수 있으나, 재현성 관점에서는 (a)~(d)를 싣는 쪽이 맞다.

**#3 · 설계 §6이 R15 어서션 수를 44로 적는다** — `recoding.design.md:207`
실제 48건(a·a2·b·c·d·d2·e·f·g·h·h2·i·i2·i3·j–j6·k·l–l10·m·n–n3·o–o10·p·p2·q).
**권고**: `44건` → `48건`.

**#4 · 아카이브 삼종이 git에 추적되지 않는다** — `docs/archive/2026-09/`
설계 §3 "추적은 유지하고"와 §9 "지워지지 않고 남는다"에 대해, 현재 상태는 `?? docs/archive/2026-09/`(미추적)이고 루트의 `coding_*.json` 세 개는 새 538쪽 라벨로 **덮어써진 상태**(`M`)다. `git commit -a`는 미추적 파일을 담지 않으므로, 그대로 커밋하면 κ 0.796의 원자료는 작업 트리 사본과 git 히스토리에만 남고 `git clean -fd` 한 번에 사본이 사라진다.
**권고**: 커밋 전 `git add docs/archive/2026-09/`. 파일 3개가 HEAD 버전과 바이트 동일함은 확인했으므로 내용 손실은 아직 없다.

**#5 · 설계 §2.2가 코더 A를 아직 "제3 제공자 대기"로 서술한다** — `recoding.design.md:95-98`, 머리말 7행
"Gemini/DeepSeek 키와 모델명이 들어오면 … 로 돌린다"가 남아 있어 §6-8(OpenAI로 완료)과 어긋난다.
**권고**: §2.2 끝과 머리말에 "2026-09-04 실행은 OpenAI 같은 계열로 진행 — FR-1 미충족, §6-8" 한 줄 추가.

**#6 · `?` 층별 임계 경고가 없다** — `recoding.design.md:257`, `score_coding.py:547-549`
설계 §8 위험표는 "`?` 비율을 보고에 명시하고, **층별로 임계를 넘으면 경고**"라고 적었다. 구현은 전체 `?` 건수, 층별 분포, 변형별 `excluded`, 재현율층 `unsure`를 출력하지만 임계 판정은 없다. 이번 실행은 `?`가 2건뿐이라 드러나지 않았을 뿐이다.
**권고**: `score_census`에 층별 `?` 비율이 임계(예: 10%)를 넘으면 경고 한 줄을 추가하고 R15에 어서션 하나를 붙인다. 또는 설계에서 완화책을 "비율 명시"까지로 축소한다.

### Low

**#7 · `meta.version`이 두 실행 모두 null** — `coding_A.json`, `coding_B.json`
설계 §2.1 스키마는 `"version": "<system_fingerprint>"`인데 OpenAI가 이를 반환하지 않아 채워지지 않았다. FR-3의 필드 존재 요건은 충족하나 "어느 모델 빌드가 코딩했는가"는 `model_reported`로만 남는다.
**권고**: 설계 §2.1에 "제공자가 `system_fingerprint`를 주지 않으면 null이고 `model_reported`가 대체 기록" 한 줄. 코드 변경 불필요.

**#8 · 설계 §8·§9의 "1,028회"** — `recoding.design.md:255`, `:267`
합집합 표본 확정 후 실제는 538 × 2 = 1,076회이며 §3·§7은 이미 1,076으로 적는다.
**권고**: 두 곳 정정.

**#9 · 설계 §6 예비 집계 문단의 전제가 낡음** — `recoding.design.md:216-222`
"A가 없어 `score_coding.py`는 돌지 않는다 / 단일 코더라 해석 보류"는 A 완료·채점 완료 이후 상태와 어긋난다. 수치 자체(32/12, 79, 52, 98, 25/36, 27/39)는 재계산으로 전부 정확.
**권고**: 문단 머리에 "(A 완료 전 기록. 최종 수치는 `recoding-results.analysis.md`)"를 붙이거나 결과 문서로 대체.

**#10 · TODOS.md 내부 모순** — "5.8%는 상한이 아니다" 문단
같은 파일 안에서 재현율이 "여전히 측정된 적이 없다"와 "2026-09-04 처음 측정: 13%"가 공존한다.
**권고**: 전자를 "재현율은 2026-09-04에 처음 측정됐고(13%), 다만 FR-1 미충족 조건부다"로 교체.

**#11 · "절단 분쟁군 8쪽 중 7쪽"** — `recoding-results.analysis.md:131`
절단 ∩ 분쟁군의 원 개수는 **9쪽**이고, `?` 1건을 제외한 유효 8쪽 중 7쪽이 둘 다 3이다. 다른 지지율 수치와 같은 규약(`?` 양쪽 제외)이라 값은 옳지만 "8쪽"의 근거가 문장에 없다.
**권고**: "(`?` 1쪽 제외, 원 9쪽)" 병기.

**#12 · 설계 §7 표에 R15q가 없다** — `recoding.design.md:228-242`
구현에만 있는 어서션이라 설계 표가 하니스의 전수 목록이 아니게 된다.
**권고**: §7 표에 "R15q · 커밋된 `recoding_scores.json`이 커밋된 키·라벨과 맞는다" 행 추가(#3과 같이 처리).

### Match Rate 산식

```
FR       6 Match + 1 Partial(FR-1)                 = 6.5 / 7
§0       1 Match                                   = 1.0 / 1
§1       4 Match                                   = 4.0 / 4
§2.1     7 Match + 1 Partial(스키마 version)        = 7.5 / 8
§2.2     1 Partial(A2 서술)                        = 0.5 / 1
§3       7 Match                                   = 7.0 / 7
§4.1     3 Match + 1 Partial(JSON 출처 주장)        = 3.5 / 4
§4.2     3 Match                                   = 3.0 / 3
§4.3     1 Match                                   = 1.0 / 1
§4.4     2 Match                                   = 2.0 / 2
§5       2 Match                                   = 2.0 / 2
§6       2 Partial(상태표 44건, 예비집계)            = 1.0 / 2
§7       3 Match                                   = 3.0 / 3
§8       1 Partial(1,028 + ? 임계 경고)             = 0.5 / 1
§9       6 Match + 1 Partial(아카이브 추적)          = 6.5 / 7
───────────────────────────────────────────────────────────
합계                                              49.0 / 53 = 92.5%
```

갭 12건: High 1 · Medium 5 · Low 6.

---

## 7. Extra — 설계에 없지만 구현에 있는 것

| # | 항목 | 위치 | 평가 |
|:--:|---|---|---|
| E1 | **R15q** — 커밋된 `recoding_scores.json` ↔ `coding_key.json` ↔ `coding_A/B.json` 삼각 검증(지문·항목 수·모델·전수 등급3 수) | `outputs/test-recount-grades.py:1749-1768` | 유익. 라벨을 다시 만들고 채점을 건너뛰면 여기서 걸린다. 설계 §7에 추가할 것(#12) |
| E2 | 408·409도 재시도 대상 | `code_pages.py:203` | 무해한 확장. 설계는 429·5xx·네트워크만 명시 |
| E3 | `coding_key.json`의 `n_recall` 필드 | `make_coding_sheet.py:292` | 설계 §3 스키마 목록에 없음. 재현에 유용 |
| E4 | 결과 문서 §4.2의 "둘 다 3" 행(94/300 → 504.2 [429, 585]) | 결과 문서 | 설계 §4.3의 코더 폭을 재현율로 확장한 것. 코드가 계산하지 않아 손계산(#2와 연결) |
| E5 | `.gitignore`에 `/.env`·`/.env.local` | `.gitignore:33-35` | 설계 §2.2는 키를 `.env.local`에 두라고만 했고 무시 규칙은 미명시. 필수적인 추가 |
| E6 | CLAUDE.md의 `code_pages.py` 절 및 R15 커버리지 규칙 | `CLAUDE.md:135, 197` | 설계 범위 밖이나 정확 |
| E7 | 결과 문서 7행의 자기 위치 선언("갭 분석은 별도 문서") | 결과 문서 | 두 문서의 충돌을 막는 장치 |

**성능 관찰 1건(갭 아님)**: `score_coding.py:637`의 `pb = [i for i in P if i in set(both_ok)]`는 항목마다 `set(both_ok)`를 새로 만든다. 현재 규모(238 × 9 × 2)에서는 무해하나 `both_ok_set = set(both_ok)`를 루프 밖으로 빼는 것이 옳다.

---

## 8. 권고 다음 단계

1. **커밋 전 필수 — `git add docs/archive/2026-09/`** (갭 #4). 유일하게 데이터 손실 가능성이 있는 항목이다. 나머지는 전부 문서 정정이다.
2. **설계서 일괄 정정 4줄** (갭 #3·#5·#8·#12): 44건→48건, §2.2·머리말에 OpenAI 실행 기록 한 줄, 1,028→1,076 두 곳, §7 표에 R15q 행.
3. **`score_census()`가 버리는 수치를 `res`에 싣는다** (갭 #2): 불일치 패턴, 규칙쌍별 지지율, 절단층 통계, "둘 다 3" 재현율. R15o10을 확장해 결과 문서의 "전부 이 파일에서" 주장을 참으로 만든다. 유일하게 코드 변경을 권하는 항목.
4. **`?` 층별 임계 경고** (갭 #6): 구현하거나 설계에서 완화책을 축소하거나 — 둘 중 하나로 설계와 코드를 맞춘다.
5. **TODOS.md 한 문장 정정** (갭 #10), 결과 문서 §6에 "(`?` 1쪽 제외)" 병기 (갭 #11).
6. **FR-1은 다음 회차로** (갭 #1). 표본·시트·지문이 그대로 유효하므로 `code_pages.py --coder A --provider-env <다른 제공자 env> --model <모델>` 한 번과 `score_coding.py` 재실행이면 끝난다. 그 전까지 `recoding_scores.json`의 정밀도·재현율은 발표 근거가 아니다 — 코드가 스스로 그렇게 경고하고 있다.

(선택) 설계 §6 9단계 옆에 "갭 분석은 `recoding.analysis.md`" 한 줄을 병기하면 설계서만 읽는 독자도 두 문서를 구분할 수 있다.

---

## 9. Act-1 (2026-09-04, 자체 재집계)

| 갭 | 조치 | 판정 변화 |
|:--:|---|---|
| #1 FR-1 | 고치지 않음 (결정됨). 채점기 경고·JSON `family_warning` 그대로 | Partial 유지 |
| #2 수치 출처 | `score_census()` 가 불일치 패턴·규칙쌍별 지지율·절단층 통계·"둘 다 3" 재현율을 `res` 에 싣고 JSON 에 기록 (R15o11). 채점 재실행으로 `recoding_scores.json` 갱신 | §4.1 Partial → Match |
| #3 44건 | 설계 §6-6 → 50건 (R15o11·o12 추가분 포함) | §6 Partial → Match |
| #4 아카이브 미추적 | **스테이징하지 않았다** — 커밋은 사용자 요청 시에만 하므로 index 도 건드리지 않는다. 커밋 시 `git add docs/archive/2026-09/` 가 필수임을 보고에 명시 | §9-7 Partial 유지 |
| #5 §2.2 서술 | 머리말·§2.2 에 OpenAI 실행 기록 추가 | §2.2 Partial → Match |
| #6 `?` 임계 경고 | `UNSURE_WARN = 0.10`, 층별·코더별 비율이 넘으면 경고 출력 + `res['unsure_warnings']` (R15o12) | §8 Partial → Match |
| #7 version null | 설계 §2.1 에 대체 기록(`model_reported`) 명시 | §2.1 Partial → Match |
| #8 1,028회 | §8·§9 → 1,076회 | (§8 과 함께 해소) |
| #9 예비 집계 | 문단 머리에 "A 완료 전 기록, 최종 수치는 결과 문서" | §6 Partial → Match |
| #10 TODOS 모순 | "측정된 적이 없다" → "2026-09-04 처음 측정(13%, FR-1 조건부)" 두 곳 | 해소 |
| #11 8쪽 근거 | "9쪽 중 `?` 1쪽 제외 8쪽" 으로 병기 | 해소 |
| #12 R15q | 설계 §7 표에 R15q·o11·o12 행 추가 | 해소 |
| 성능 관찰 | `set(both_ok)` 를 루프 밖으로 | — |

재집계: Partial 로 남는 항목은 FR-1 과 §9-7 뿐 → **52.0 / 53 = 98.1%**. 하니스 282/282 PASS.
이 재집계는 구현자의 자체 평가다 — 독립 재검은 다음 회차(FR-1 충족 회차)의 gap-detector 로 미룬다.

---

## 10. Act-2 — FR-1 회차 (2026-09-04, 자체 재집계)

연구 책임자 지시("anthropic 모델로 한번 더")로 코더 **C = `claude-opus-5`** 를 넣었다. API 키가 없어 설계
A1 경로(`claude -p`)를 `code_pages.py --backend claude-cli` 로 구현했고, 그 과정에서 **원칙 1 을 깨는 통로를
실측으로 찾아 막았다**: `claude -p` 는 기본으로 사용자 MCP 서버의 도구 정의(4.8만~11.8만 토큰)와 프로젝트
설정·CLAUDE.md 를 코더 컨텍스트에 싣는다. `--strict-mcp-config` · `--setting-sources ""` · `--tools ""` ·
저장소 밖 cwd 를 강제해 310토큰(짧은 항목)으로 내렸다(설계 제약 9, R15s). 첫 스모크 2항목은 그 통로가
열린 채 나왔으므로 폐기하고 다시 돌렸다.

| 항목 | 결과 |
|---|---|
| FR-1 | **충족** — C(Anthropic) vs B(OpenAI). `score_coding.py --coders C,B`, `family_warning` 없음 |
| 실행 | 538/538, 오류 0, `?` 5, 입력 1.61M 토큰, 추정 $14.78 |
| 시험 | R15r(`--coders`), R15s–s5(백엔드·워커·dry-run), R15q 가 JSON 의 `coder_files` 를 따라감 — 하니스 288/288 |
| 산출물 | `recoding_scores.json`(C,B 주), `_CA.json`, `_AB.json`(1차 보존) |
| 결과 문서 | `recoding-results.analysis.md` 를 2회차 기준으로 다시 씀 |

재집계: FR-1 Partial → Match. 남는 Partial 은 §9-7(아카이브 미추적, 커밋 시 `git add` 필요)뿐 →
**52.5 / 53 = 99.1%**. 자체 평가다.
