# Archive Index — 2026-09

보관 산출물 목록. `coding-v1` 은 **폐기된 라벨의 기록**, `recoding`·`resegment`·`resegment-publish`·`marker-offset`·`semantic-recount-remediation`·`semantic-expression-review`·`hwpx-ncs-section-refresh` 는 완료된 PDCA 기능 문서다.

| Item | 종류 | 보관일 | 보관 파일 |
|------|------|--------|-----------|
| [coding-v1](coding-v1/) | 1차 수기 코딩 라벨 (무효) | 2026-09-04 | coding_key.json · coding_A.json · coding_B.json |
| [recoding](recoding/) | PDCA 기능 (완료, Match Rate 99.1%) | 2026-09-04 | plan · design · analysis(갭) · report |
| [resegment](resegment/) | PDCA 기능 (완료, Match Rate 99%) | 2026-09-07 | plan · design · analysis(갭 Check-1/2) · report |
| [resegment-publish](resegment-publish/) | PDCA 기능 (완료, Match Rate 93%) | 2026-09-07 | plan · design · analysis(갭 Check-1/2) · report |
| [marker-offset](marker-offset/) | PDCA 기능 (완료, Match Rate 100%; 채택 여부는 결정 대기) | 2026-09-08 | plan · design · analysis(갭 + Act-1) · report |
| [semantic-recount-remediation](semantic-recount-remediation/) | PDCA 기능 (완료, Match Rate Act-0 96% → 100%; PR #15) | 2026-09-14 | plan · design · analysis(갭 + Act-1 + Act-2 ship 리뷰) · report |
| [semantic-expression-review](semantic-expression-review/) | PDCA 기능 (완료, Match Rate 96% → Act-1 100%; PR #16 머지 `6f1fa1f`) | 2026-09-15 | plan · design · analysis(갭 + Act-1) · report |
| [hwpx-ncs-section-refresh](hwpx-ncs-section-refresh/) | PDCA 기능 (완료, Match Rate 92% → Act-1 100%; PR #16 머지 `6f1fa1f`) | 2026-09-15 | plan · design · analysis(갭 + Act-1) · report |

## coding-v1

`TODOS.md` P2 와 `docs/04-report/regrade-audit-response.report.md` §1 이 무효로 판정한 69쪽
(분쟁군 39 + 대조군 30) 이중코딩 라벨. 발표된 κ 0.796 / 일치 88.4% 의 **유일한 원자료**라
삭제하지 않고 옮겼다.

- **왜 무효인가**: 코더 A 가 규칙 작성 당사자였고, 코딩 시트가 D1 의 동음이의 가정과
  방향성 동점 규칙을 두 코더에게 흘렸으며, 표본틀이 C-2 버그를 가진 카운터로 뽑혔다.
- **왜 재채점할 수 없는가**: `coding_key.json` 이 `sample_digest` 가드(`9773312`)보다 먼저
  생성돼 지문이 없다. 채점기는 "구버전 산출물" 로 멈춘다 — 가드가 옳다.
- **후속**: `recoding` (이 디렉터리의 [`recoding/`](recoding/) 에 보관). 루트의 `coding_key.json` 은
  2026-09-04 부터 538쪽 4층 합집합 표본의 새 키다.

## recoding

안전등급 규칙 검증을 위한 라벨 재생산 — 2026-09-04, Plan → Design → Do → Check(92.5%) → Act-1(98.1%) → Act-2(99.1%).

- **Problem**: 기존 69쪽 라벨은 무효(코더 독립성 실패·지시문 누출·표본틀 오염)였고 규칙의 재현율은 측정된 적이 없었다.
- **Solution**: 두 어휘 정의의 합집합으로 4층 전수+재현율층 표본 538쪽을 뽑고, 항목별 독립 호출기 `code_pages.py` 로 세 코더(Claude `claude-opus-5`, OpenAI `gpt-5.6-sol` ×2)가 코딩, 전수 채점기가 정확 초기하 구간으로 재현율을 처음 측정했다.
- **결과**: 현행 규칙 정밀도 80~84%, 재현율 13~21%. 코더 기준 진짜 등급3 22~37%(발표 5.8% 의 4~6배). 계열 간 κ 0.685. 어느 변형도 채택하지 않았고 발표 수치는 불변.
- **관련 자산**: 연구 결과 `docs/03-analysis/recoding-results.analysis.md`, 어휘 탐색 `docs/03-analysis/vocab-search.analysis.md`, 수치 `docs/03-analysis/data/recoding_scores*.json`, 라벨 `coding_key.json`·`coding_A/B/C.json`, 회귀 `outputs/test-recount-grades.py` R15(56건).

보관 문서:
- [Plan](recoding/recoding.plan.md)
- [Design](recoding/recoding.design.md)
- [Analysis (갭)](recoding/recoding.analysis.md)
- [Report](recoding/recoding.report.md)

## resegment

워크북 페이지 라벨을 원본 PDF 실제 쪽으로 재배치해 등급 재집계 — 2026-09-06, Plan → Design → Do → Check-1(79%) → Act-1 → Check-2(99%) → Act-2 → 출하 전 리뷰 57건 반영 → PR #13(2026-09-06 머지, `07a91a6`).

- **Problem**: 외부감사(2026-09-04) C1 — 워크북 '페이지' 라벨은 2026-04 검색 당시 목차 유도 마커가 묶은 여러 쪽짜리 블록(32,767자 라벨 16개)이라 페이지 단위 등급 집계가 흔들렸다.
- **Solution**: `resegment.py` — 마크다운 줄을 PyMuPDF 쪽 텍스트에 문자 3-gram 포함률 + 단조 DP 로 정렬해 검출 행 7,769건을 실제 쪽에 재배치하고 `regrade.grade_page` 기준선으로 쪽 등급을 재계산; 마커 보유 23권으로 자기 검증(83.6% / ±1쪽 94.9%); `EXPECTED` 회귀 가드.
- **결과(Act-2, PR #13)**: 1,847 → 2,173쪽, 등급 1/2/3 = 1,502/524/147 (6.8%), 사고사례 8라벨 → 13쪽/5권, 1:1 쪽 등급 일치 98.7%. 발표 정본은 후속 `resegment-publish`(Act-3 하이브리드, 2,189쪽 · 145쪽 6.6%)가 이어받았다.
- **관련 자산**: 연구 결과 `docs/03-analysis/resegment-results.analysis.md`, 산출물 `docs/03-analysis/data/reseg_summary.json`·`ncs_pages_reseg.csv`(계보 `docs/03-analysis/data/README.md`), 회귀 `outputs/test-recount-grades.py` R16.

## resegment-publish

재세그먼트 수치 발표 + 마커 결손 하이브리드 배정 — 2026-09-06, Plan → Design → Do → Check-1(87%) → Act-1 → Check-2(93%) → Act-2 → 출하 전 리뷰 반영 → PR #14(2026-09-07 머지, `7fd6264`).

- **Problem**: PR #13 의 재세그먼트(실제 쪽 기준)가 있는데 공개 대시보드·README 는 라벨 기준(1,847쪽·등급3 108쪽 5.8%)을 발표했고, 마커 교재에서 마커가 빠진 쪽의 줄이 앞 쪽에 뭉쳤다.
- **Solution**: 연구 책임자 결정 ①②③ — `hybrid_pages()`(마커 사이가 2쪽 이상 비면 DP 배정, 앵커 보정)로 재실행하고 대시보드 3종·README·보고서를 `reseg_summary.json` 정본으로 교체, 하니스가 그 정본과 대조(D13·D14·R17).
- **결과**: 2,189쪽 · 등급 1/2/3 = 1,519/525/145 (69.4/24.0/6.6%) · 사고사례 13쪽/5권 · 지문 `20855b3bc05d906b`. 출하 전 리뷰가 잡은 결함(마커 쪽 17개 비움)은 앵커 보정으로 수정. 후속 판단: 마커 ±1쪽 보정 여부(TODOS ④).
- **관련 자산**: 결과 `docs/03-analysis/resegment-results.analysis.md` §3.6·§6, 계보 `docs/03-analysis/data/README.md`, 산출물 `reseg_summary.json`·`ncs_pages_reseg.csv`, 회귀 `outputs/test-recount-grades.py` R16z15~z21·R17, `outputs/test-dashboard-data.js` D13·D14.

## marker-offset

마커 교재의 마커 ±1쪽 오차 측정과 보정 판단 — 2026-09-07, Plan → Design → Do → Check(93.8%) → Act-1(갭 4건 즉시 수정, 재검증 100%) → Report(2026-09-08). 미커밋 상태로 보관(커밋은 연구 책임자 요청 시).

- **Problem**: `resegment-publish` 출하 전 리뷰 F2 — 마커 교재 23권은 변환기 마커를 쪽 번호로 쓰는데 마커 자체가 ±1쪽 밀린 경우가 있었고(『반도체 장비 안전관리』 한 권만 실측), 자기 검증은 그 오차를 DP 오류로 계상했다.
- **Solution**: `resegment.py` 에 DP 와 독립인 진단 `marker_offsets`(마커 쪽 본문 vs PDF P±3 3-gram 포함률) + 6분류 `classify_offset`(±1 은 포함률 ≥ 0.5, 마진 ≥ 0.10) 을 넣어 산출물(JSON `marker_offset`, CSV `마커오프셋` 13열, `EXPECTED` 17키)에 실었고, 보정은 변형 `--marker-correct MARGIN`(`corrected_markers` 비감소 규칙 + 마커 줄 교체, 추적 경로 거부)으로만 두었다.
- **결과**: 23권 2,035 마커 쪽 중 같은 쪽 1,772(87.1%), 뚜렷한 ±1 93(4.6%, 장비 안전관리 33). 보정 변형(마진 0.05/0.10/0.20, 둔감): 2,189→2,181쪽, 등급 3 145→147, 사고사례 112→113(수기 표 일치 4/7→5/7), 자기 검증 nogap 88.6→90.5%. 발표 수치 불변(지문 `20855b3bc05d906b`). 채택 여부(a/b, 권고 마진 0.10)는 연구 책임자 결정 대기 — `TODOS.md` ④, 결과 문서 §6 6.
- **관련 자산**: 결과 `docs/03-analysis/resegment-results.analysis.md` §3.7, 계보 `docs/03-analysis/data/README.md`, 회귀 `outputs/test-recount-grades.py` R16z22~z28·R17, `outputs/test-dashboard-data.js` D13i·D13q·D14.

보관 문서:
- [Plan](marker-offset/marker-offset.plan.md)
- [Design](marker-offset/marker-offset.design.md)
- [Analysis (갭 + Act-1)](marker-offset/marker-offset.analysis.md)
- [Report](marker-offset/marker-offset.report.md)

## semantic-recount-remediation

2026-09-13 외부감사(등급 F)의 시정 — 2026-09-13~14, Plan → Design → Do → Check(96%) → Act-1(G1~G10, 100%) → Act-2(/ship 리뷰 8종 47건 반영) → Report → PR #15(CI·GitGuardian·CodeRabbit pass, 보관 시점 미머지).

- **Problem**: 발표 중인 의미 출현 수치(NCS 12,875건·미확정 813·89파일)가 변환기 요약본 4개·중복 교재 1개로 오염돼 있었고(감사 C1), 미확정 813건을 등급1로 강제 배정한 미승인 산출물이 이미 발행(C3), 출현건수 분모가 등급3 비중을 페이지 기준 대비 약 3배로 보이게 함(C2), 교차검증 하니스가 153→18개로 축소(M3), 해시 불일치(M5).
- **Solution**: 연구책임자 결정 8건(코퍼스 정제, 미확정 강제 배정 승인, 출현건수 분모 공식화 + 페이지 기준 병기, 하니스 복원 등) 위에 `semantic_keyword_recount.py` 정본 실행 1개 — `select_ncs_documents`(LM 코드 필수·중복 제거), `check_marker_base`, `EXPECTED` 12키 + `check_expected` + `--force`, `run_manifest`(git·명령·입력 sha256), 산출물 7종 한 실행·원자적 쓰기, `shift_page_markers.py`(새 2권 0-based 마커 +1), 렌더러 브리지 절, 하니스 S1~S9(64)·R8k~u(390)·unittest 53.
- **결과**: NCS 86권 **12,506건**(등급 1/2/3 = 5,057/4,854/2,595 = 20.8%), 교과서 1,293건, 미확정 0(문맥 판정 1). 코덱스 09-09 대비 −369(요약본 −742·중복 −70·새 2권 +443), 등급3 비율 20.6→20.8%. 이전 기준(페이지) 2,189쪽·145(6.6%)는 브리지 표로 병기. 커밋 뒤 재실행 → 가드 통과·통계 동일.
- **이월**(`TODOS.md` "의미 재검산 감사 시정 후속"): 표현 75개 도메인 점검(감사 M1), 페이지 단위 이질성(M2), 비단조 마커 레거시 1권 재유도, `public_path`→`page_utils`, hwpx 문서 구 수치.
- **관련 자산**: 정본 `docs/03-analysis/data/semantic_summary.json`(≡ `docs/semantic_recount_data.js`), 분리 페이지 `docs/keyword-analysis.html`·`NCS_키워드검색결과.html`·`교과서_키워드검색결과.html`, 규칙 `CLAUDE.md` "Safety Grading Scheme" 예외 문단·"4. Semantic recount" 절, 이전 두 기능 문서(`semantic-keyword-recount`·`semantic-occurrence-grades`)의 폐기 배너.

보관 문서:
- [Plan](semantic-recount-remediation/semantic-recount-remediation.plan.md)
- [Design](semantic-recount-remediation/semantic-recount-remediation.design.md)
- [Analysis (갭 + Act-1 + Act-2)](semantic-recount-remediation/semantic-recount-remediation.analysis.md)
- [Report](semantic-recount-remediation/semantic-recount-remediation.report.md)

## semantic-expression-review

의미 표현 사전의 도메인 점검과 v2 채택 — 2026-09-14, Plan → Design → Do → Check(96%) → Act-1(G-1~G-8, 100%) → ship 리뷰(PR #16: 스페셜리스트·레드팀·Codex/Claude 적대적·CodeRabbit 2회) → Report → PR #16 머지(2026-09-15, main `6f1fa1f`).

- **Problem**: 정본 13,799건 중 28.4%(동등 2,417 + 구체 1,507)가 LLM 단독으로 고른 표현의 값이고 검토 기록이 없었다(감사 M1·m3); 14개 키워드가 사람 보호 vs 오염관리·계측·설비 문맥을 한 규칙으로 세었다.
- **Solution**: 연구책임자 결정 1(v1fix: 영문 정확 키워드 단어 경계, `안전` 안의 보류 표현 제외)·2(계층별 처방: 보류 `방진화`·`케미컬`, 조건부 `방진복`·`장갑`·`X선`·`PSM`, 동의어 유지)·3(v2 채택). `expression_review.py` sample/score/impact — 22개 표현 618건 층화 표본, 2계열 코더(A `claude-opus-5`, B `gpt-5.6-sol`, κ 0.965), 재정 17건, Clopper-Pearson 하한 0.8; `semantic_keyword_recount.py` 사전 버전 v1/v1fix/v2·조건부 규칙(`SAFETY_COMPANIONS`)·변형 실행 거부.
- **결과**: 정본 NCS 12,506 → **11,517**(등급 4,378/4,614/2,525 = 21.9%), 교과서 1,293 → 1,207. 등급3 비율 20.8 → 21.9% 는 구성 효과(걷어낸 NCS 출현의 72%가 등급1). 하니스 unittest 137·S1~S9 68·R 390.
- **이월**(`TODOS.md` 1·6): `가연성` 60건 2차 패스, 정확 키워드 문맥 대조 표본, 동반어 동음이의 근거 축적, 같은 줄 중복 표현 위치 보존, F11 phantom "동반어 없음" 제외(정본 워크북 복귀 뒤 재실행). 측정 정밀도가 하한 아래인데 채택된 동의어 4개·조건부 2개는 연구 결과 문서 §5·§7 이 명시.
- **관련 자산**: 연구 결과 `docs/03-analysis/expression-review.analysis.md`, 데이터 `docs/03-analysis/data/expression_review_{key,A,B,adj,scores,impact}.json`, 정본 `semantic_summary.json`(사전 v2), 규칙 `CLAUDE.md` "Dictionary versions"·`expression_review.py` 문단, 보류 정책 `docs/superpowers/specs/2026-09-08-semantic-keyword-recount-design.md`.

보관 문서:
- [Plan](semantic-expression-review/semantic-expression-review.plan.md)
- [Design](semantic-expression-review/semantic-expression-review.design.md)
- [Analysis (갭 + Act-1)](semantic-expression-review/semantic-expression-review.analysis.md)
- [Report](semantic-expression-review/semantic-expression-review.report.md)

## hwpx-ncs-section-refresh

기초보고서 HWPX 제3장 1~3절을 정본 수치로 재작성 — 2026-09-14, Plan(연구책임자 결정 D1~D5) → Design → Do → Check(92%) → Act-1(G-1~G-11, 100%) → ship 리뷰(PR #16: 레드팀 CRITICAL 2·Codex 적대적 10·Claude 적대적 F1~F15) → Report → PR #16 머지(2026-09-15).

- **Problem**: 보고서 제3장의 수치가 폐기된 2026-09-09 실행값(85종·12,875건·813 미확정)과 2026-04 행 수의 혼합이었고, "9건의 사례"·"모두 등급 3"·"전체 평균 수준 이상" 같은 서술이 정본과 모순됐다.
- **Solution**: 새 추적 스크립트 `hwpx_results_refresh.py`(stdlib + ImageMagick) — 정본 JSON(`semantic_summary.json` 키워드×그룹·그룹 쪽수 추가, `accident_case_pages.json` 13쪽 원문 확인 판정)만 읽어 절을 제목으로 찾고 문단 45·표 7·그림 3을 재작성, 서술 조건은 데이터로 분기해 대조 JSON `conditions` 에 기록, 1~3절 모든 숫자 토큰을 정본 값과 감사(미일치면 쓰지 않음), 1~3절 밖 문단 불변 검사, 재실행 바이트 동일(`-strip`).
- **결과**: `data/반도체 기초보고서_20260914_정본.hwpx`(비추적, sha256 `7827bdb7…`) — NCS 86권 8,914쪽 11,517건(38.0/40.1/21.9%), 교과서 9권 2,055쪽 1,207건, 사고사례 자동 판정 13쪽 → 실제 서술 3쪽·2건(반도체 산업재해 1건)·오탐 10쪽; 대조 JSON 숫자 토큰 723·미일치 0; `test_hwpx_results_refresh` 39.
- **한계·이월**(`TODOS.md` 5): 숫자 감사는 "정본 밖 숫자 없음"만 보장(작은 수의 다의성), 산출물에 재실행 불가(원본에서만), 한글(HWP) 렌더링 `[→E2E]` 미확인, 2장 5절 등 범위 밖 절과 다른 작업의 미추적 문서는 기록만.
- **관련 자산**: 대조 JSON `docs/03-analysis/data/hwpx_results_refresh_20260914.json`, 검토 HTML `docs/03-analysis/hwpx-results-refresh/review.html`, 판정 데이터 `docs/03-analysis/data/accident_case_pages.json`, 규칙 `CLAUDE.md` 그룹 4 `hwpx_results_refresh.py` 문단, README 산출물 재생성 절.

보관 문서:
- [Plan](hwpx-ncs-section-refresh/hwpx-ncs-section-refresh.plan.md)
- [Design](hwpx-ncs-section-refresh/hwpx-ncs-section-refresh.design.md)
- [Analysis (갭 + Act-1)](hwpx-ncs-section-refresh/hwpx-ncs-section-refresh.analysis.md)
- [Report](hwpx-ncs-section-refresh/hwpx-ncs-section-refresh.report.md)
