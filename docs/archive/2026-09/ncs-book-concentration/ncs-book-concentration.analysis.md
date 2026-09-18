# ncs-book-concentration — 설계·구현 갭 분석 (Check)

> **Feature**: ncs-book-concentration · **Design**: `docs/02-design/features/ncs-book-concentration.design.md` (D1 (b)·D2 (a)·D3 (b)·D4 (a)·D5 (a)·D6 (b)) · **Plan**: `docs/01-plan/features/ncs-book-concentration.plan.md`
> **Date**: 2026-09-17 · **Analyst**: gap-detector 에이전트(Claude Opus 5) — 작업 트리(미커밋, HEAD `b057902`) 22:45 기준. 분석 중 다른 세션이 문서 3곳을 고쳤고(§3 끝), 표는 재확인 시각의 상태다.
> **결과**: 1차 **89.8 %** (118항목: 일치 96 · 변경 10 · 부분 12 · 불일치 0 — 갭 Medium 1 · Low 9. 코드 동작·정본 수치·HWPX 산출·대시보드는 설계와 일치하고, 갭은 문서 계보(data README 1행)·가드 폭(분야별 등급 합)·테스트 강도(3권 수사·항등식) 에 몰려 있었다) → **Act-1 반영 후 100 %** (부분 12 → 0, §7; 정본 재실행 없음 — `EXPECTED`·해시·HWPX sha 불변, unittest 242 OK · 하니스 24/83/390/32/38). Act-1 이후 같은 PR 의 `/ship` 리뷰(전문가 5·레드팀·적대적 리뷰 2건)가 3단계 삽입의 중복 빈 문단·가드 공백 등을 추가로 찾아 고쳐, 최종 수치는 unittest 247 OK·하니스 24/84/390/32/38·HWPX sha `aa0f3453…`(§7 이후 수치는 바뀌었으나 Match Rate 100% 는 그대로).

## 1. 대조 범위

| 구분 | 항목 수 | 근거 문서 |
|---|---:|---|
| 설계 §3.1~§3.9 (payload·파생 사실·템플릿·3단계 삽입·감사·대시보드·하니스·대조 JSON·문서) | 63 | design §3 |
| 설계 §2.4 정본 재실행 연쇄 체크리스트 | 11 | design §2.4 |
| 설계 §4 테스트 설계 | 9 | design §4 |
| 계획 FR-01~FR-11 | 11 | plan §3.1 |
| 계획 §3.2 비기능(재현성·공개 경계·크기) | 2 | plan §3.2 |
| 계획 §4 성공 기준 | 5 | plan §4 |
| 결정 D1~D6 + 설계 §6 설계 결정 3건 | 7 | plan §6 · design §6 |
| **합계** | **118** | |

비교 대상: `semantic_keyword_recount.py`(`_book_title`·`dashboard_payload` books·`check_books`·`_books_digest`·`EXPECTED`), `hwpx_methods_bridge.py`(`BookRow`·`GroupConcentration`·`ConcentrationFacts`·`load_concentration_facts`·템플릿·상수), `hwpx_results_refresh.py`(`Facts.concentration`·`_Ledger.last_inserted`·3단계 블록·목차·`SECTION_LABEL`), `docs/semantic_grade_dashboard.js`(`books()`·`bookRows()`), 테스트 4모듈, 하니스 `outputs/test-dashboard-data.js`, 추적 산출물(`semantic_summary.json`·`semantic_recount_data.js`·분석 페이지 3종·`hwpx_results_refresh_20260917.json`·`review.html`), 비추적 산출물(`…_20260917_정본.hwpx`·xlsx·report), 문서 5종. 실측: 하니스 83/83, `test_hwpx_methods_bridge`+`test_hwpx_results_refresh` 103 OK(skip 1), `test_semantic_keyword_recount` 111 OK; 정본 실행·HWPX 스크립트는 다시 돌리지 않고 산출물을 읽었다. 항목별 근거는 부록 A.

## 2. 항목별 결과 (요약)

| 설계 절 | 일치 | 부분 | 불일치 | 변경 | 비고 |
|---|---:|---:|---:|---:|---|
| §3.1 정본 payload (`books[]`·가드·`EXPECTED`) | 10 | 2 | 0 | 2 | 실측 NCS 86·교과서 9행, 합 == 말뭉치·분야(총계 11,517/1,207·등급·`detected_pages` 2,492/388·쪽수 9,100), `books_digest` `9c57f39963c6c7cd` 재계산 일치. 부분: 분야별 **grades** 합은 `check_books` 도 `S3q` 도 보지 않는다(A8·A9). 변경: `_book_title` 이 목록 접두("반도체 재료 02. ")까지 뗀다(A3), `books_digest` 가 pages·title·group 을 뺀다(A11) |
| §3.2 파생 사실 | 8 | 0 | 0 | 1 | 정본 값 2권·2,238/965·84권 9,279/1,537·장비 19/3,239/1,052→18/1,608/272·8.5/0.0/57·상위 10권 2,015(80.5%) 모두 재계산과 일치; `CONCENTRATION_SAME_PP` 별칭 없이 `BRIDGE_SAME_PP` 직접(B7) |
| §3.3 템플릿 | 6 | 0 | 0 | 3 | 피스 15개·표 12-3 7행·표 12-4 10행·주·분기 조건 일치; 문구 미세 차이(C2·C3), "같다"→"거의 같다"(C5) |
| §3.4 3단계 삽입 | 10 | 0 | 0 | 0 | 장부 `last_inserted` 로 삽입, 소결 4)→6), 목차 삽입 2, 검토 HTML 절 이름; `write_text_review` 순서는 분석 중 반영됨(D8) |
| §3.5 숫자 감사 | 4 | 0 | 0 | 0 | 감사 1,052 → 1,168 토큰·미일치 0; 삽입 P/N 전부 `keys` 있음; 제목 안 숫자 0건(규칙 불요) |
| §3.6 대시보드 | 6 | 0 | 0 | 0 | NCS 만, 리드 문단(57권·38.6%), 9열·86행·등급 3 내림차순, `scroll-x[role=region]`, `index.html` 정적 불변 |
| §3.7 하니스 | 2 | 1 | 0 | 2 | ID 는 S3q·S1w·S1x(설계 S3p·S1r·S1s 는 기존 ID 와 충돌); `detected_pages <= Math.max(pages, detected_pages)` 는 항등식(G1) |
| §3.8 대조 JSON·검토 HTML | 5 | 0 | 0 | 0 | `concentration` {inserted 15, tables 8×4·11×4, conditions, dedicated}, `bridge.toc` 1/2, `renumbered` 4)→6), review.html 표 2개, 본문 없음 |
| §3.9 문서 | 9 | 2 | 0 | 0 | data README 대조 JSON 행이 이름만 바뀜(I10, **G1**); CLAUDE.md `docs/index.html` 항목에 교재별 절 없음(I3) |
| §2.4 연쇄 11항목 | 9 | 2 | 0 | 0 | 해시 4종·총계·등급·keywords·previous_basis 가 HEAD 판과 동일(차이는 `meta.generated`·`meta.run` 뿐), HWPX sha == 대조 JSON; 부분은 data README(J9)·메모리(J10) |
| §4 테스트 설계 | 7 | 1 | 0 | 1 | 3권 수사("세 권") 분기 미검사(K6); ID 변경(K9) |
| FR-01~11 | 7 | 3 | 0 | 1 | FR-02(분야별 grades·Σdetected_pages 가드), FR-07(3+), FR-11(data README·메모리) |
| 비기능 2 | 2 | 0 | 0 | 0 | data.js 48 → 67 KB(+19 KB, 설계 추정 +20 KB); 추적 JSON·대조 JSON·대시보드에 본문·절대 경로 없음 |
| 성공 기준 5 | 4 | 1 | 0 | 0 | Polaris 확인 기록이 2단계 파일까지(M5) |
| 결정 7 | 7 | 0 | 0 | 0 | |
| **합계** | **96** | **12** | **0** | **10** | **(96 + 10) / 118 = 89.8 %** |

## 3. 갭 목록

| ID | 심각도 | 항목 | 실측 | 조치 (Act-1 가치) |
|---|:-:|---|---|---|
| G1 | Medium | data README 대조 JSON 행(I10·J9·FR-11) | `docs/03-analysis/data/README.md:13` — 파일명만 `hwpx_results_refresh_20260917.json` 으로 바뀌고 내용은 2026-09-16 판: `layout` "정본 109·821·109"(실측 125·913·125), "소결 5)"(6)), "토큰 1,052"(1,168), "새 HWPX 는 `…_20260915_정본.hwpx`"(20260917), `concentration` 블록·표 12-3/12-4 미기재 | 행 내용을 20260917 실행값으로 다시 쓰고 3단계(`concentration`: 삽입 15·표 12-3 8×4·12-4 11×4·`dedicated`·`conditions`) 한 절 추가. **예** — 계보표가 틀린 숫자를 말한다 |
| G2 | Low | 분야별 등급 합 가드·단언(A8·A9·G1·FR-02) | `check_books` `semantic_keyword_recount.py:1606-1611` `for key in ("documents", "total", "pages")`, `load_concentration_facts` `hwpx_methods_bridge.py:382-386`(documents·total), `S3q` `outputs/test-dashboard-data.js:153-156`·교과서 비교 `:160` — 어디에도 분야별 `grades` 합 비교가 없다(설계 §3.1·§3.2·§3.7 은 grades 포함). 같은 레코드에서 나오므로 실측 위험은 없다 | 세 곳에 등급 4종 합 비교 한 줄씩(교과서 books≡groups 에 `grades` 딥 비교). **예** — 10줄 |
| G3 | Low | `grade3_pages ≤ detected_pages ≤ pages` 단언(G1) | `S3q :158` 와 `test_semantic_keyword_recount.py:1057` 이 `detected_pages <= max(pages, detected_pages)` — 뒤 부등식이 항등식. 실측 95권 모두 `detected_pages <= pages` 성립(NCS 0건·교과서 0건 위반) | `<= b.pages` 로 되돌린다. **예** — 2줄 |
| G4 | Low | 테스트 보강(K6·K7·FR-07) | `test_branches` `test_hwpx_methods_bridge.py:632-649` 는 전용 1권·올라감·거의 같음·≤50%·0건 미만만 — 3권 수사("세 권", `KOREAN_COUNT[3]`) 미검사; E2E `:504` review.html 캡션 단언이 표 12-2 까지, `:501` text_review 에 "concentration" 미단언 | `dedicated` 3권 fixture 로 "세 권" 단언, 캡션 목록에 "표 12-3."·"표 12-4.", text_review 에 "concentration". **예** — 테스트만 |
| G5 | Low | FR-02 `Σ detected_pages ≥ corpus detected_pages` | `check_books` 에 없음. 실측 등식(2,492 == 2,492, 388 == 388 — 쪽은 교재 안에서 고유하므로 항상 등식) | `check_books` 에 등식 비교 한 줄(문서에는 "등식" 으로 정정). **선택** |
| G6 | Low | CLAUDE.md·README 문구(I2·I3·I7) | CLAUDE.md:222 `docs/index.html` 항목에 교재별 현황 절 없음(3단계 문단 안 한 문장뿐); CLAUDE.md:150 3단계 문단 끝 "Tests for the second stage as a whole"(third); README:87 2단계 문장 "소결 → 5)" — 지금 한 실행에서 소결은 6) | 세 문구 수정. **예** — 문서 |
| G7 | Low | `hwpx_results_refresh.py` 문자열에 3단계 없음 | 모듈 docstring `:2`·`:8`, `review_text.html` h1 `:1663`, `review.html` h1 `:1687`("표 4·5·6·12-1·12-2(2단계)" — 실제 파일엔 12-3·12-4 절이 있다), argparse `:1704`, 자기 산출물 거부 문구 `:1533` "이미 2단계 산출물입니다"(검사 집합엔 `CONCENTRATION_HEADING` 이 들어 있다) | 문구에 3단계·표 12-3/12-4 추가, 거부 문구 "2·3단계". **선택** — 문구(review.html 재생성은 다음 실행 때) |
| G8 | Low | `EXPECTED` 주석 오배치 | `semantic_keyword_recount.py:80` — `dedup` 의 "MI 장비 운영 공백 경로(마커 0) 1개를 버린다" 주석이 `books_digest` 줄 끝에 끌려가 있고 `:78` `dedup` 은 주석이 없다 | 주석을 `dedup` 줄로 되돌린다. **예** — 1줄 |
| G9 | Low | TODOS 5·Polaris(I11·M5) | TODOS.md:31 "줄 배치 캐시를 지운 문단 109개"(3단계 뒤 125); "Polaris 확인 완료" 목록이 표 12-1/12-2·2절 4)·소결까지 — 3단계 정본(`…_20260917_정본.hwpx`: " 5) 교재별 집중과 편차"·표 12-3(8행)·12-4(11행)·" 6) 소결") 확인 미기록 | 문단 수 갱신; Polaris/한글 확인은 §5 `[→E2E]` 로 넘기고 확인 뒤 기록. **예**(문구) / 확인은 사람 |
| G10 | Low | 메모리·archive `_INDEX.md`(§2.4 #10, J10·FR-11) | 메모리 디렉터리에 `ncs-book-concentration` 항목 없음; archive 는 report 뒤 | report 단계에서 기록(정본 실행일 2026-09-17·수치 불변·HWPX 이름). **보류** — 순서상 다음 단계 |

분석 중 닫힌 항목(다른 세션이 22:3x~22:4x 에 반영, 재확인 시각 기준 일치): `write_text_review` 절 순서에 `concentration`(`hwpx_results_refresh.py:1665`), CLAUDE.md:150 파일명 `…_20260917_정본.hwpx`·`hwpx_results_refresh_20260917.json` 과 :172 "2026-09-17 canonical run — same inputs and numbers as the 2026-09-15 run", README:87 HWPX 이름 예시 `…_20260917_정본.hwpx`.

## 4. 설계 외 구현·의도적 차이 (기록)

| 항목 | 설계 | 구현 | 판단 |
|---|---|---|---|
| `_book_title` | `\d{8}_\d{6}_` 접두·`LM\d{10}_`·`\d+v\d+_` 판 토큰 제거 | `_BOOK_TITLE_DROP`(LM 코드·판 토큰을 위치 무관 제거) + `_BOOK_TITLE_PREFIX`("반도체 재료 02. " 목록 접두) `semantic_keyword_recount.py:1788-1799` | 실 파일명이 두 모양(코드 앞/뒤)이라 필요 — 개선. 4형 테스트 `:1416` |
| `books_digest` | `books` 목록 전체 해시 | result 의 (말뭉치·식별자·출현·등급·검출 쪽·등급 3 쪽) — `pages`(이전 기준 파일 유래, 입력 sha256 이 고정)·`title`·`group` 제외 `:1476-1491` | 재배분 탐지라는 목적은 같음; 제목 규칙 변화는 `DEDICATED_EXPECTED_CODES`(HWPX)·`S3r`(하니스)가 잡는다. 커밋 JSON 재계산 테스트가 같은 규칙을 쓴다 |
| `check_books` | 4종 합 | + 교재마다 `grade3_pages <= detected_pages` `:1612-1614` | 개선 |
| 하니스 | S3p·S1r·S1s | S3q·S1w·S1x + **S3r**(전용 2권 965건·38.6%·0건 57권 고정 — 제목 규칙의 파이썬·JS 동일성) | 기존 ID 충돌 회피; S3r 는 개선 |
| `CONCENTRATION_SAME_PP` | `= BRIDGE_SAME_PP` 별칭 | `BRIDGE_SAME_PP` 직접 `hwpx_methods_bridge.py:775` | 같은 값·한 정의 |
| 방향 문구 | 내려간다/올라간다/같다 | "거의 같다" `:776` | 2단계 "거의 같았다" 와 일관 |
| P1·분야 문장·P2 문구 | "NCS 등급 3 출현 …", "두 권을 제외한", "보기 위한", "{반도체장비} 분야에서는 … 한 권의", "(표 12-4는 상위 10권)" | "NCS의 등급 3 출현 …", "이 두 권을 제외한", "확인하기 위한", "장비 분야에서는 {제목}의"(약칭 `NCS_GROUP_TO_AREA`, "한 권의" 생략), "(상위 10권은 표 12-4)" `:785-807` | 값·분기·조건 동일; 분야 약칭은 보고서 규약(표 12-4 와 같음) |
| 표 12-3 분야 라벨 | "{분야} 분야" | "장비 분야"·"재료 분야"(약칭) `:748-750` | 같은 규약 |
| 설계 §3.1 예시 행 | `LM1903060329` pages 120·detected 41·grade3_pages 9 | 실측 155·137·42 | 설계의 예시값 — 데이터로 바로잡힘 |
| payload 크기 | 64 → ≈85 KB | `semantic_summary.json` 92,346 → 121,059 B(indent=1), `semantic_recount_data.js` 48,448 → 67,263 B | 증가분 +19~29 KB 는 추정과 일치, 설계의 기준선(64 KB)이 틀렸음. 대시보드가 읽는 data.js 는 67 KB |
| `books` 없음 정지 | `_get` hint | 명시 `ValueError` `:369-370` | 동가 |
| 테스트 이름 | `test_run_census_refuses_book_sum_mismatch` | `test_run_census_refuses_when_book_sums_disagree` | 이름만 |
| 리드 문단 서체 | 미지정 | `<p class="ts">` `docs/semantic_grade_dashboard.js:32` | 설계 밖. 브리지 절은 S1s 규칙(해석 문단은 본문 서체)으로 `.ts` 를 벗겼으므로 디자인 리뷰에서 같은 잣대를 댈지 판단 |
| S1w 행 수 단언 | 86행 전부 | 페이지 전체 `<tr><td><strong>` ≥ 86 | 실측 절 안 86·밖 49 — 절 없이는 통과하지 못하므로 유효 |
| 감사 토큰 | — | 1,052 → 1,168(+116: P1 26·P2 9·표 12-3/12-4 셀·주·헤더·목차) | 대조 JSON `audit` |

## 5. 잔여 (자동 검증 밖)

- `[→E2E]` 한글: 3단계 정본 `data/반도체 기초보고서_20260917_정본.hwpx` 의 " 5) 교재별 집중과 편차"·표 12-3(8행)·표 12-4(11행, "반도체용 박막 도금 공정 재료 제조 (재료)" 같은 긴 첫 열)·" 6) 소결"·목차 2절 6항목의 렌더와 쪽 넘김(2절에 표 4개). Polaris 기록은 2단계 파일까지(G9).
- 숫자 감사의 문맥 무지: "등급 3"·"상위 10권" 의 `3`·`10` 이 `cases.false_positive` 등 무관 키에도 걸린다(대조 JSON `keys` 목록) — 1단계부터의 알려진 한계. 미일치 0 은 값 소속만 뜻한다.
- 실행 시간 ≈35 s(NFR)·`--force` 재실행 "새 출력과 같음" 은 실행 로그가 없어 여기서 확인하지 못함 — 결정론은 fixture E2E(`test_hwpx_methods_bridge.py:553`)로 대체.
- 커버리지 ≥ 80 %: 수치 도구 없음. 새 함수(`_book_title`·`check_books`·`_books_digest`·`load_concentration_facts`·템플릿 7종·3단계 블록·`books()`)마다 테스트가 있다.
- Polaris Drive 자동 업로드 주의(TODOS 5)는 그대로.

## 6. 판단

1차 Match Rate **89.8 %** (118항목, 불일치 0). 정본 수치·HWPX·대시보드·가드·대조 JSON 은 설계대로이고, 갭 10건 중 Medium 은 data README 한 행(G1)뿐이며 나머지는 문서 문구·가드 한 줄·테스트 강도였다. Act-1(§7)로 G1~G9 를 모두 닫았고 G10 의 메모리도 적었다(archive `_INDEX.md` 는 archive 단계의 일이므로 갭이 아니다) → 재평가 **100 %**. 남는 것은 §5 의 `[→E2E]` 한글 확인뿐이며, 이는 설계 §5 가 사람 확인으로 둔 항목이다.

## 7. Act-1 반영 (2026-09-17, 같은 세션)

정본 재실행 없이 닫았다 — `semantic_summary.json`·`EXPECTED`·해시 4종·HWPX sha(`9ce5cd63…`)·대조 JSON 은 바이트 그대로이고, 바뀐 것은 가드·테스트·문구·문서뿐이다. 가드 2건은 TDD(실패 확인 → 구현)로 넣었다.

| 갭 | 반영 | 검증 |
|---|---|---|
| G1 | `docs/03-analysis/data/README.md` 대조 JSON 행을 20260917 실행값으로 다시 씀 — layout 125·913·125, 소결 `4) → 6)`, 토큰 1,168, `concentration` 블록(삽입 15·표 12-3 8×4·12-4 11×4·`dedicated` 2·`conditions` 4종), `tables` 14, 새 HWPX `…_20260917_정본.hwpx` | 대조 JSON 실측과 대조 |
| G2 | 분야별 등급 합: `check_books` 등급 4종(`semantic_keyword_recount.py`), `load_concentration_facts` 등급 1~3(`hwpx_methods_bridge.py`), `S3q` 분야별 4종 + 교과서 books ≡ groups 등급 | RED `test_check_books_catches_group_grades_and_detected_pages`·`test_guards_bind_books_to_the_canonical_totals`("교재 등급 합" subTest) 실패 확인 → GREEN; 하니스 83/83 |
| G3 | `detected_pages <= pages` 로 교정 — `S3q`, `test_committed_summary_json_matches_expected` | 실측 95권 위반 0 |
| G4 | `test_branches` 에 전용 3권 fixture("세 권(", "이 세 권을 제외한 83권", 같은 분야 두 권 `·` 연결, `dedicated_count` 3); E2E 캡션 목록에 표 12-3·12-4, `review_text.html` 에 `concentration` 절이 `bridge` 뒤 | unittest 242 OK |
| G5 | `check_books` 에 Σ`detected_pages` == 말뭉치 `detected_pages` 등식(쪽은 교재 안에서 고유), `S3q`·커밋 JSON 테스트도 같은 등식 | 실측 2,492 == 2,492 · 388 == 388 |
| G6 | CLAUDE.md `docs/index.html` 항목에 "NCS 교재별 현황" 절(S1w·S1x); 3단계 문단 끝 "Tests for the second and third stages"; README 2단계 문장에서 "소결 → 5)" 를 빼고 3단계 문장에 "소결을 6) 으로(2단계만의 2026-09-16 정본은 5))" | 하니스 S7·S8 통과 |
| G7 | `hwpx_results_refresh.py` docstring(3단계 문단·추적 파일 8종 → 11종 정정)·argparse·`review_text.html` h1·`review.html` h1(표 12-3·12-4(3단계))·자기 산출물 거부 "이미 2·3단계 산출물"(목차 수 검사의 같은 문구 포함); 정본 명령 `--force` 재실행으로 추적 `review.html` 재생성 | 재실행: HWPX sha·대조 JSON 바이트 동일, `review.html` 은 h1 한 줄만 차이; 거부 문구 테스트 2곳 갱신 |
| G8 | `EXPECTED` 의 `dedup` 주석을 제자리로 | — |
| G9 | TODOS 5: 캐시 없는 문단 2단계 109 / 3단계 125 구분, 3단계 정본의 Polaris 확인 범위를 사실대로 기록(첫 문단·표 12-3·12-4 정상, 표 12-4 는 36/37쪽에 갈림 — (a)와 같은 쪽 경계 문제; 둘째 문단·목차·" 6) 소결" 은 뷰어 미확인) | 스크린샷(20:54) 재확인 |
| G10 | 메모리 `ncs-book-concentration.md` 기록(결정 6건·정본 실행일·HWPX 이름·남은 단계); archive `_INDEX.md` 는 archive 단계 | — |

재평가: 부분 12건(A8·A9·G1·I3·I10·J9·J10·K6·FR-02·FR-07·FR-11·M5) 전부 일치 → (96 + 12 + 10) / 118 = **100 %**. 부록 A 의 판정은 1차(22:45) 기록 그대로 두고, 위 표가 그 뒤의 상태다.

## 부록 A. 항목 대조표 (118)

판정: 일치 / 부분 / 불일치 / 변경(다른 수단, 같은 목적). 행 번호는 22:45 작업 트리.

### A. 설계 §3.1 정본 payload (14)

| ID | 항목 | 판정 | 근거 |
|---|---|:-:|---|
| A1 | `corpora.*.books[]` 교재당 1행, 매칭 0건 교재도 행 | 일치 | `semantic_keyword_recount.py:1864-1893`(`records_by_document.get(…, [])`); 실측 86·9행; `test_payload_books_rows_and_sums` `test_semantic_keyword_recount.py:1385`(무매칭 교재 행) |
| A2 | `code` NCS `_document_code` / 교과서 null | 일치 | `:1875`,`:1884`; 실측 교과서 9행 null |
| A3 | `title` 규칙(접두·LM·판 토큰·`_`→공백·NFC; 교과서 표시명) | 변경 | `_book_title` `:1788-1799` — 목록 접두·LM 코드 위치 무관 제거 추가(§4) |
| A4 | `group` `_dashboard_group` | 일치 | `:1871`,`:1886` |
| A5 | `pages` 규칙을 교재 단위로, `groups[].pages == Σ books.pages` | 일치 | `:1875-1881`; 실측 84권 == reseg `per_book.pdf_pages`, `LM1903060408` 120·`LM1903060424` 119 == manifest `real_page_marker_books`, 합 9,100 == groups 합 |
| A6 | `total`·`grades`·`detected_pages`·`grade3_pages` | 일치 | `:1887-1891`; 실측 합 11,517/1,207, 등급 3,788/5,227/2,502·633/459/115, detected 2,492/388, `unpaged` 0 |
| A7 | 정렬 NCS `code` / 교과서 `title` | 일치 | `:1893`; 실측 정렬·고유 |
| A8 | 교과서 `books[]` ≡ `groups[]`(이름·총계·등급) 를 S3 가 단언 | 부분 | 실측 9행 이름·total·grades·pages 모두 같음; `S3q` `outputs/test-dashboard-data.js:160` 는 이름·total·pages 만(G2) |
| A9 | 가드(쓰기 전): 행 수·Σtotal·Σgrades·분야별(total·grades·pages·documents) | 부분 | `check_books` `:1594-1616`, 호출 `:2476`(쓰기 전) — 분야별은 documents·total·pages(G2); `test_run_census_refuses_when_book_sums_disagree` `:1434` |
| A10 | `summary_metrics`/`EXPECTED` `books` {NCS 86, 교과서 9} | 일치 | `:1469`,`:79` |
| A11 | `books_digest = _canonical_hash(books 목록 전체)` | 변경 | `_books_digest` `:1476-1491`(pages·title·group 제외, §4); `EXPECTED` `:80` `9c57f39963c6c7cd` |
| A12 | `STRICT_GROUPS` 에 `books` 미포함 | 일치 | `:63` 불변 |
| A13 | 커밋 JSON 에서 `books_digest` 재계산 == `EXPECTED` | 일치 | `test_semantic_keyword_recount.py:786-792`,`:1048`; 실측 재계산 `9c57f39963c6c7cd` |
| A14 | 크기 +≈20 KB, `write_dashboard_data` 불변 | 일치 | data.js +18.8 KB; writer diff 2줄(헤더·JSON 본문) |

### B. 설계 §3.2 파생 사실 (9)

| ID | 항목 | 판정 | 근거 |
|---|---|:-:|---|
| B1 | `BookRow` | 일치 | `hwpx_methods_bridge.py:297-306` |
| B2 | `ConcentrationFacts` 필드 | 일치 | `:323-340` |
| B3 | `GroupConcentration` | 일치 | `:310-320` |
| B4 | `books` 없음 → "2026-09-17 이후" 힌트 정지 | 일치 | `:369-370`; `test_hwpx_methods_bridge.py:602-604` |
| B5 | 가드: 교재 수·출현 합·등급 3 합·분야별 합·전용 집합 == `DEDICATED_EXPECTED_CODES` | 일치 | `:374-390`; subTest 5종 `:589-601` |
| B6 | `value_pairs()` `books.*` 키(총계·전용·제외·분야·평균·중앙값·0건·상위 10권·합과 몫) | 일치 | `:342-363`; 대조 JSON P1 keys |
| B7 | `CONCENTRATION_SAME_PP = BRIDGE_SAME_PP` | 변경 | `:775` 직접 사용(§4) |
| B8 | 과반 `> 50.0%`, 평균·중앙값(분모 0 제외), 0건 수 | 일치 | `:791`,`:403-410`; 실측 8.5/0.0/57 |
| B9 | `top` (−g3, −total, code) 상위 `TOP_BOOKS=10` | 일치 | `:412`,`:34`; 실측 1위 `LM1903060329` 780 |

### C. 설계 §3.3 템플릿 (9)

| ID | 항목 | 판정 | 근거 |
|---|---|:-:|---|
| C1 | 피스 순서 15개, 원형 `protos2` | 일치 | `:810-811`; 대조 JSON kinds `BHBPBCTNBCTNBPB`; `hwpx_results_refresh.py:1504` |
| C2 | P1 문안 | 변경 | `:794-799`(§4 문구) |
| C3 | 분야 문장(과반/비과반, 몫 큰 순) | 변경 | `:785-793`,`:402`; 실측 장비 74.1%(과반)·재료 14.8% 순 |
| C4 | P1 `conditions` | 일치 | `:799`; 대조 JSON `{2, 내려간다, {반도체장비: true, 반도체재료: false}}` |
| C5 | `rest_rate_direction` 내려간다/올라간다/같다 | 변경 | `:774-777` "거의 같다" |
| C6 | 표 12-3 캡션·헤더·7행·주 | 일치 | `:728`,`:733-757`; review.html 7행+헤더; 대조 JSON 8×4 |
| C7 | 표 12-4 캡션·헤더·10행·주(합·몫) | 일치 | `:729`,`:760-771`; 실측 2,015건·80.5% |
| C8 | P2 문안·`zero_majority` | 일치 | `:802-807`; 실측 57권(66.3%) 과반 |
| C9 | 상수 6종(`CONCENTRATION_HEADING`·`" 6) 소결"`·`TABLE12_3/4_*`·`TOP_BOOKS`·`DEDICATED_TITLE_RULE`) | 일치 | `:30-34`,`:728-730` |

### D. 설계 §3.4 3단계 삽입 (10)

| ID | 항목 | 판정 | 근거 |
|---|---|:-:|---|
| D1 | `_Ledger.last_inserted` | 일치 | `hwpx_results_refresh.py:1318`,`:1354` |
| D2 | `ref3 = L.last_inserted[-1]` → `L.insert(…, "concentration")` | 일치 | `:1502-1504` |
| D3 | `out["concentration"]`·`out["tables"]`·`review_tables` | 일치 | `:1505-1512` |
| D4 | 소결 " 6) 소결", `renumbered {"4) 소결": "6) 소결"}` | 일치 | `:1514-1515`; HWPX " 6) 소결" 2회·" 5) 소결" 0회 |
| D5 | 목차 `[H(CONC), H(CONCL)]`, `toc {1, 2}`, `audit_texts` | 일치 | `:1415-1417` |
| D6 | `Facts.concentration`·`load_facts`·`value_index` 합류 | 일치 | `:130`,`:196`,`:299-301` |
| D7 | `SECTION_LABEL["concentration"]` | 일치 | `:1678`; review.html "(교재별 집중)" |
| D8 | `write_text_review` 절 순서 | 일치 | `:1665`(분석 중 반영) |
| D9 | 표 원형 4열, 행 조정만 | 일치 | 대조 JSON cols 4·4 |
| D10 | 자기 산출물(3단계) 입력 거부 | 일치 | `:1531-1533` 검사 집합에 `CONCENTRATION_HEADING`; 문구는 G7 |

### E. 설계 §3.5 숫자 감사 (4)

| ID | 항목 | 판정 | 근거 |
|---|---|:-:|---|
| E1 | 새 문단·셀 숫자 전부 `value_pairs` 키 | 일치 | 대조 JSON P/N `keys` 비어 있지 않음; `test_every_number_has_a_source_key` `test_hwpx_methods_bridge.py:651-658`; 감사 1,168·미일치 0 |
| E2 | `STRIP_BEFORE_AUDIT` 그대로 | 일치 | `:1245` 불변 |
| E3 | 제목 안 숫자 실측 | 일치 | NCS 86권 제목에 숫자 0건 — 규칙 불요 |
| E4 | 감사 범위에 3단계 문단·셀·목차 | 일치 | 토큰 +116; `:1417` |

### F. 설계 §3.6 대시보드 (6)

| ID | 항목 | 판정 | 근거 |
|---|---|:-:|---|
| F1 | `books(name)` NCS 만 | 일치 | `docs/semantic_grade_dashboard.js:25-26` |
| F2 | 리드 문단(0건 수/비율·'안전관리' 몫) | 일치 | `:27-32`; `S1w` |
| F3 | 9열·등급 3 내림차순(동률 출현)·86행 | 일치 | `:22-23`,`:33`; 실측 절 안 86행 |
| F4 | `.card > .scroll-x[tabindex=0][role=region][aria-label]`, `--fg-*`·막대 없음 | 일치 | `:33`(색 지정 없음) |
| F5 | `render()` "영역별 현황" 뒤, `insights()` 불변 | 일치 | `:97` |
| F6 | `docs/index.html` 정적 불변 | 일치 | git status 변경 없음 |

### G. 설계 §3.7 하니스 (5)

| ID | 항목 | 판정 | 근거 |
|---|---|:-:|---|
| G1 | S3p books↔corpora | 부분 | `S3q` `outputs/test-dashboard-data.js:149-163` — grades 미단언·항등식(G2·G3) |
| G2 | S1r NCS "교재별 현황"·최다 교재·0건 N권 | 변경 | `S1w` `:84-90` |
| G3 | S1s 교과서 절 없음 | 변경 | `S1x` `:91` |
| G4 | S6 실행일·xlsx 이름 | 일치 | `S6b` 통과(20260917) |
| G5 | 인용 단언 수(S9/R17) | 일치 | 83 — README:115·CLAUDE.md:182 |

### H. 설계 §3.8 대조 JSON·검토 HTML (5)

| ID | 항목 | 판정 | 근거 |
|---|---|:-:|---|
| H1 | `diff["concentration"]` 스키마 | 일치 | `hwpx_results_refresh_20260917.json` 실측(inserted 15·tables 8×4/11×4·table_id·conditions·dedicated) |
| H2 | `bridge.toc {1, 2}` | 일치 | 실측 |
| H3 | `bridge.renumbered {"4) 소결": "6) 소결"}` | 일치 | 실측 |
| H4 | review.html 두 표(헤더 포함) | 일치 | h2 "표 12-3. (교재별 집중)"·"표 12-4. (교재별 집중)"; h1 은 G7 |
| H5 | 본문 텍스트 없음 | 일치 | `inserted` 는 kind·numbers·keys·conditions 만 |

### I. 설계 §3.9 문서 (11)

| ID | 항목 | 판정 | 근거 |
|---|---|:-:|---|
| I1 | CLAUDE.md 그룹 4 recount 항목 `books[]` | 일치 | CLAUDE.md:147 |
| I2 | CLAUDE.md `hwpx_results_refresh.py` 3단계 | 일치 | :150 "Third stage (2026-09-17…)"; 끝 문장 오기 G6 |
| I3 | CLAUDE.md 대시보드 항목에 교재별 절 | 부분 | :222 `docs/index.html` 항목 미갱신(G6) |
| I4 | CLAUDE.md Testing/Test Coverage | 일치 | :182(83), :213-214 `ConcentrationFactsTests`/`ConcentrationTemplateTests` |
| I5 | CLAUDE.md 날짜·파일명 문구 → 2026-09-17 | 일치 | :150·:172(분석 중 반영) |
| I6 | README 핵심 수치 문단·재생성 절 xlsx | 일치 | README:9,:79 |
| I7 | README HWPX 이름 | 일치 | :87(분석 중 반영); "소결 → 5)" 는 G6 |
| I8 | README 교재별 집중 한 문장 | 일치 | :87 "3단계(2026-09-17)는 … 38.6%, … 57권" |
| I9 | data README `semantic_summary.json` 행 `books[]` | 일치 | data README:6 |
| I10 | data README 대조 JSON 행 20260917(20260915 계보) | 부분 | :13 이름만(G1) |
| I11 | TODOS 1 닫기·2 `books[].pages`·5 표 12-3/12-4 | 일치 | TODOS:27-28,:31; "문단 109개" 는 G9 |

### J. 설계 §2.4 정본 재실행 연쇄 (11)

| ID | 항목 | 판정 | 근거 |
|---|---|:-:|---|
| J1 | summary.json·data.js `books[]`·`generated_at`·`git_commit` | 일치 | 2026-09-17T20:47:47·`b057902`(= HEAD); data.js ≡ JSON(파싱 비교) |
| J2 | 분석 페이지 3종 | 일치 | meta 줄 `…_20260917.xlsx · git b057902+ · 2026-09-17` |
| J3 | xlsx·`_report.md` 20260917(20260915 보존) | 일치 | `data/` 두 판 존재 |
| J4 | HWPX `…_20260917_정본.hwpx` | 일치 | 존재, sha256 == `diff.output_sha256` |
| J5 | 대조 JSON 신규·계보·최신 선택 | 일치 | `CommittedDiffTests` `paths[-1]` |
| J6 | review.html 표 12-3·12-4·실행일 | 일치 | 실측(정본 2026-09-17T20:47:47) |
| J7 | 본문 출처 문구 | 일치 | HWPX "2026-09-17 정본" 5회·"2026-09-15 정본" 0회 |
| J8 | impact.json 불변 | 일치 | git 변경 없음 |
| J9 | README·CLAUDE·data README·TODOS 날짜·파일명 | 부분 | data README 대조 JSON 행(G1) |
| J10 | 메모리·archive `_INDEX.md` | 부분 | 메모리 항목 없음(G10) |
| J11 | 수치·해시 불변, `EXPECTED` 통과 | 일치 | manifest 4종·총계·등급·groups·keywords·previous_basis·reseg_agreement 2,035/2,035·inputs 7종 == HEAD 판(차이는 `meta.generated`·`meta.run`); `meta.run.expected` true·`force` false |

### K. 설계 §4 테스트 설계 (9)

| ID | 항목 | 판정 | 근거 |
|---|---|:-:|---|
| K1 | `test_payload_books_rows_and_sums`(+`_book_title` 4형) | 일치 | `test_semantic_keyword_recount.py:1385-1420` |
| K2 | `test_metrics_and_expected_pin_books` | 일치 | `:1422-1432` |
| K3 | `test_run_census_refuses_book_sum_mismatch` | 일치 | `:1434-1445`(이름 다름) |
| K4 | 커밋 JSON `books_digest` 재계산 | 일치 | `:786`,`:1048` |
| K5 | `ConcentrationFactsTests` | 일치 | `test_hwpx_methods_bridge.py:570-604` |
| K6 | `ConcentrationTemplateTests` 분기 양쪽 | 부분 | `:632-649` — 3권 수사 미검사(G4) |
| K7 | `Stage2EndToEndTests` 확장 | 일치 | `:467-483`,`:491`; 감사 ok·불변·결정론·캐시(125/909); 캡션 보강은 G4 |
| K8 | `CommittedDiffTests` | 일치 | `test_hwpx_results_refresh.py:44-63`,`:69` |
| K9 | S3p·S1r·S1s | 변경 | S3q·S3r·S1w·S1x |

### L. 계획 FR-01~FR-11 (11)

| ID | 판정 | 근거 |
|---|:-:|---|
| FR-01 | 일치 | A1~A7 |
| FR-02 | 부분 | 분야별 grades·`Σdetected_pages ≥` 미검사(G2·G5) |
| FR-03 | 일치 | A10·A11·A13 |
| FR-04 | 일치 | B1~B9 |
| FR-05 | 일치 | D1~D9; HWPX 본문 순서 4)→5)→6) |
| FR-06 | 일치 | E1 |
| FR-07 | 부분 | 3+ 미검사(G4) |
| FR-08 | 일치 | E4·K7 |
| FR-09 | 일치 | H1~H4·K8 |
| FR-10 | 변경 | S3q/S1w |
| FR-11 | 부분 | data README·메모리(G1·G10) |

### M·N·Q. 성공 기준·결정·비기능 (14)

| ID | 항목 | 판정 | 근거 |
|---|---|:-:|---|
| M1 | 정본 재실행 `EXPECTED` 통과·해시 불변·86/9·합계 | 일치 | J11; 11,517/2,502·1,207/115 |
| M2 | 집중도 값 | 일치 | 실측 965/2,502=38.6%, 84권 16.6%, 장비 32.5→16.9%, 8.5/0.0/57 |
| M3 | HWPX 삽입·6)·목차·감사 0·바이트 동일·재실행 동일 | 일치 | J4·J7·E1; `check_untouched` 내장; 결정론은 fixture E2E |
| M4 | 대시보드·하니스·테스트·커버리지 | 일치 | 83/83·103·111 OK |
| M5 | 문서·TODOS·Polaris·한글 `[→E2E]` | 부분 | Polaris 기록 2단계까지(G9) |
| D1 (b) | `books[]` 정본 payload | 일치 | A1 |
| D2 (a) | 2절 " 5) 교재별 집중과 편차", 소결 6) | 일치 | D2·D4 |
| D3 (b) | 표 12-3 + 12-4, 4열 | 일치 | C6·C7 |
| D4 (a) | 제목 "안전관리" + 기대 집합 | 일치 | `hwpx_methods_bridge.py:32-33`,`:389-390` |
| D5 (a) | 교과서 JSON 행만 | 일치 | 교과서 9행; 문안 NCS 만 |
| D6 (b) | NCS 표만(차트 없음) | 일치 | F1~F3 |
| 설계 §6 | 파생 미저장·4열·`last_inserted` | 일치 | JSON 에 파생값 없음; cols 4; D1 |
| Q1 | 재현성·공개 경계 | 일치 | `EXPECTED`·`S3i`·대조 JSON 본문 없음 |
| Q2 | payload 크기 | 일치 | data.js 67 KB(+19 KB) |
