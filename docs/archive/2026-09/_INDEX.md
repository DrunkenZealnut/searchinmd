# Archive Index — 2026-09

보관 산출물 목록. `coding-v1` 은 **폐기된 라벨의 기록**, `recoding`·`resegment`·`resegment-publish`·`marker-offset`·`semantic-recount-remediation`·`semantic-expression-review`·`hwpx-ncs-section-refresh`·`occurrence-real-pages`·`hwpx-methods-bridge-refresh`·`ncs-book-concentration` 는 완료된 PDCA 기능 문서다.

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
| [occurrence-real-pages](occurrence-real-pages/) | PDCA 기능 (완료, Match Rate 90.8% → Act-1 100%; PR #17, 보관 시점 미머지) | 2026-09-15 | plan · design · analysis(갭 + Act-1) · report |
| [hwpx-methods-bridge-refresh](hwpx-methods-bridge-refresh/) | PDCA 기능 (완료, Match Rate 98.2% → Act-1 100%; 보관 시점 미커밋 — ship 예정) | 2026-09-16 | plan · design · analysis(갭 + Act-1) · report |
| [ncs-book-concentration](ncs-book-concentration/) | PDCA 기능 (완료, Match Rate 89.8% → Act-1 100%; 보관 시점 미커밋 — ship 예정) | 2026-09-17 | plan · design · analysis(갭 + Act-1) · report |

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

## occurrence-real-pages

의미 출현을 실제 PDF 쪽에 얹기 — 페이지 단위 이질성 해소 — 2026-09-15, Plan(연구책임자 결정 D1~D6 전부 A) → Design → Do → Check(90.8%) → Act-1(G-1~G-11, 100%) → ship 리뷰(PR #17: 전문가 6·레드팀·Codex design voice, 적대적 Claude 12·Codex 구조 리뷰 P2 1, CodeRabbit 3) → Report → PR #17(보관 시점 미머지).

- **Problem**: 정본 의미 재검산(NCS 11,517건)의 "페이지"는 마크다운 쪽 표식이었다 — 86권 중 23권만 실제 쪽이고 63권은 목차 유도 블록이라 한 "페이지"가 실제 1쪽이기도 41쪽이기도 했고(외부감사 M2), 등급도 2026-04 워크북 라벨 상속(6,292건)과 블록 텍스트 판정(5,225건)이 섞여 있었다.
- **Solution**: `resegment.py`가 이미 만든 줄→실제 쪽 대응(84권, 정렬 자기 검증 ±1쪽 94.9%)을 `--page-maps`로 입력해 NCS 출현마다 실제 쪽을 붙이고, 등급은 실제 쪽 본문에 `regrade.grade_page` 기준선 하나로 판정(이전 기준과 공유 쪽 2,035개에서 100% 일치를 `EXPECTED`로 고정); 표식이 실제 쪽인 새 2권은 표식 그대로. 신규 영향표 `occurrence_real_pages_impact.py`가 블록 기준 vs 실제 쪽 기준을 나란히 집계.
- **결과**: NCS 등급 3,788/5,227/2,502(21.9 → 21.7%, 구성 효과), 이동 4,016건(34.9%), `existing` 상속분 52.8%만 불변; 분야 쪽수 8,914(표식 최댓값) → 9,100(PDF 쪽수, D4); 대시보드 브리지 절이 "같은 실제 PDF 쪽 기준·같은 규칙, 검출 쪽 집합은 다르다(2,492 vs 2,189)"로 두 KPI 관계를 데이터에서 그린다. ship 리뷰 58건(critical 0) 반영으로 대응↔이전 기준 결속 검증(`check_page_maps_against_previous_basis`)·영향표 성능(21.7→14.0초)·영향표 교재 분류(`per_book.method` 기준, 23/61/2)·블록 폭 표 이중 계수 제거(CodeRabbit)까지 정본 밖 견고성도 확보. 테스트 unittest 137→175·하니스 68→79.
- **이월**(`TODOS.md` ④·5(c)·⑥): `--marker-correct` 채택(D2-B, `NCS_PDF_ROOT` 확보로 로컬 재실행 가능해졌으나 채택은 연구책임자 결정), LM 코드 규약 통일·`resegment.py` 실행 id 결속(적대적 리뷰 INVESTIGATE), `run_census`/`main()` metrics 중복 계산 제거(단순화 자문, 보류), 한글(HWP) E2E 확인, F11(정본 워크북 `data/` 복귀로 재실행 가능).
- **관련 자산**: 정본 `docs/03-analysis/data/semantic_summary.json`(`meta.page_basis`·`meta.run.reseg_agreement`·`corpora.*.detected_pages`), 영향표 `docs/03-analysis/data/occurrence_real_pages_impact.json`, HWPX 정본 `data/반도체 기초보고서_20260915_정본.hwpx`(비추적)·대조 JSON `docs/03-analysis/data/hwpx_results_refresh_20260915.json`, 규칙 `CLAUDE.md` "4. Semantic recount" 그룹 4·Safety Grading Scheme 예외 문단.

보관 문서:
- [Plan](occurrence-real-pages/occurrence-real-pages.plan.md)
- [Design](occurrence-real-pages/occurrence-real-pages.design.md)
- [Analysis (갭 + Act-1)](occurrence-real-pages/occurrence-real-pages.analysis.md)
- [Report](occurrence-real-pages/occurrence-real-pages.report.md)

## hwpx-methods-bridge-refresh

기초보고서 HWPX 2단계 — 제2장 5절 연구 방법 갱신 + 제3장 2절 " 4) 집계 기준의 변경과 이전 결과와의 관계" 신설 — 2026-09-16, Plan(연구책임자 "A+B3", D1~D6 모두 (a)) → Design → Do(TDD) → Check(gap-detector 109항목 98.2%) → Act-1(G1~G9, 100%) → Report. 커밋·PR 은 보관 뒤 `/ship`.

- **Problem**: 정본 HWPX 의 제3장 수치는 2026-09-15 정본인데 제2장 5절은 2026-04 방법(목차 기반 쪽 표식, "페이지·구역" 등급)을 설명하고 목차에는 본문에 없는 구고 소제목 8개가 남았다; 표 4 는 NCS 85종(제조 14·재료 22)으로 표 11 의 86종과 어긋났다; 제3장 2절은 등급3 21.7%(출현 기준)만 제시하고 쪽 단위 이전 기준(2026-09-06 발표, 2,189쪽·6.6%)과의 관계·블록→실제 쪽 전환 효과(등급 바뀐 출현 4,016건)를 설명하지 않았다.
- **Solution**: 새 모듈 `hwpx_methods_bridge.py`(사실 `MethodsFacts`·`BridgeFacts` — 추적 파일 11종(`MethodsPaths`) + `EXCEL_MAX_CHARS` 에서, 계보 가드 7종; 템플릿·분기)와 `hwpx_results_refresh.py` 2단계(문단 복제·삽입·삭제, 표 12 복제(고유 id), 범위/목차 탐지, 셀 문단 편집, 손댄 집합 장부 `check_untouched`, `.<sha16>.bak` 백업, 감사 범위 확장, 정본 산출물 재입력 선제 거부). `occurrence_real_pages_impact.py` 에 `pages.real_page_grades`(1,825/524/143)·`pages.교과서`(388: 335/45/8) 추가. 숫자는 전부 `Facts.value_index()` 경유 — 손으로 넣는 허용 숫자 0; JSON 에 없는 값(변환 보고서 4건·사전 개정 날짜·"출현 50건 이상")은 문장에서 제외(D3).
- **결과**: `data/반도체 기초보고서_20260915_정본.hwpx` 재생성(sha256 `161d2408…` — 대조 JSON `output_sha256`; 이전 파일 `.235ec03f.bak`·리뷰 전 출력 `.e9856fad.bak`·직전 출력 `.573484cb3e9a41b7.bak`) — 5절 표 5(7단계)·표 6(8행)·소제목 6·본문 7·삭제 6·재작성 2, 목차 8→6, 표 4 86/13/24, 2절 4) 문단 2·표 12-1(4,378/4,614/2,525 → 3,788/5,227/2,502, 1,785 블록 → 2,492쪽, 등급 변경 4,016건 34.9%)·표 12-2(이전 기준 2,189쪽 145(6.6%) ↔ 정본 쪽 2,492쪽 143(5.7%) ↔ 출현 2,502/11,517(21.7%), 공유 2,035쪽 일치 100%)·소결 5)·1절 교과서 불변 문장; 숫자 감사 1,052 토큰·미일치 0; 재실행 시 ZIP 항목·대조 JSON·review.html 동일. `test_hwpx_methods_bridge` 49(신규)·`test_hwpx_results_refresh` 44, 하니스 24/79/390/32/38. ship 리뷰(전문가 6·레드팀·커버리지·계획 감사)에서 critical 1(`main()` 스텁 KeyError)·informational 40여 건을 닫았다(레드팀: `direct_text` 꼬리 글, 사실 적재 계보 가드, 공유 쪽 하한, 장부의 원소 참조, 사전 판 표기의 한글 인접, 백업 원자성·검증).
- **한계·이월**(`TODOS.md` "기초보고서 보강 후속"): 숫자 감사는 문맥을 모른다(85 같은 작은 수 우연 일치); 한글(HWP) 쪽 넘김·표 열 너비 `[→E2E]`; 제안서 B1·B2·B4·B5·C·D·E·F 와 Codex 미반영 항목(원저자). 최대 표식 폭은 58(`;` 분리 — 초안의 53 은 `|` 분리 오류).
- **관련 자산**: 대조 JSON `docs/03-analysis/data/hwpx_results_refresh_20260915.json`(`methods`·`bridge`; 실행 환경은 담지 않는다), 검토 HTML `docs/03-analysis/hwpx-results-refresh/review.html`, 영향표 `docs/03-analysis/data/occurrence_real_pages_impact.json`, 규칙 `CLAUDE.md` 그룹 4 `hwpx_results_refresh.py` 2단계 문단, 제안서·문안 초안 `docs/04-report/features/research-content-{proposals-20260915,draft-A-B3-20260916}.md`(비추적).

보관 문서:
- [Plan](hwpx-methods-bridge-refresh/hwpx-methods-bridge-refresh.plan.md)
- [Design](hwpx-methods-bridge-refresh/hwpx-methods-bridge-refresh.design.md)
- [Analysis (갭 + Act-1)](hwpx-methods-bridge-refresh/hwpx-methods-bridge-refresh.analysis.md)
- [Report](hwpx-methods-bridge-refresh/hwpx-methods-bridge-refresh.report.md)

## ncs-book-concentration

기초보고서 HWPX 3단계 — 제3장 2절에 " 5) 교재별 집중과 편차"(표 12-3·12-4) 신설 + 정본 `books[]` + 대시보드 교재별 현황 — 2026-09-17, Plan(TODOS 후속 B1, 연구책임자 D1~D6) → Design → Do(TDD) → Check(gap-detector 118항목 89.8%) → Act-1(G1~G10, 100%) → Report. 커밋·PR 은 보관 뒤 `/ship`.

- **Problem**: 정본 대시보드·보고서는 NCS 등급 3 을 "11,517건 중 2,502건(21.7%)" 합산값 하나로만 제시해, 그 중 38.6%(965건)가 안전관리 전용 2권에 몰려 있고 86권 중 57권은 등급 3 이 0건이라는 분포를 가렸다. 교재별 집계는 비추적 워크북 `NCS_파일별` 시트를 세션마다 다시 세는 값뿐이라 인용할 추적 근거가 없었다.
- **Solution**: `semantic_keyword_recount.py`(정본 재실행 2026-09-17, 수치·해시 4종 불변)에 `corpora.*.books[]`(교재별 출현·등급·검출 쪽·쪽수, 매칭 0건 교재도 포함) 추가 + 쓰기 전 가드(`check_books` — 행 수·출현·등급 4종·Σ검출 쪽·분야별 4종·교재별 grade3_pages ≤ detected_pages) + `EXPECTED.books`/`books_digest`; 신규 `hwpx_methods_bridge.py` 3단계(`ConcentrationFacts`·`load_concentration_facts` — 전용 교재는 제목 "안전관리" + 기대 집합 `DEDICATED_EXPECTED_CODES` 고정, 파생값은 저장하지 않는다)와 `hwpx_results_refresh.py` 확장(2단계 블록 뒤 장부 `last_inserted` 로 삽입, 목차 2항목·소결 4)→6)); `docs/semantic_grade_dashboard.js`(NCS "교재별 현황" 절, 86행 등급 3 내림차순).
- **결과**: 안전관리 전용 2권 965/2,502(38.6%, 자체 43.1%) · 제외 84권 16.6% · 장비 분야 32.5→16.9%(전용 1권이 분야의 74.1%) · 재료 21.4→20.3% · 교재별 평균 8.5%·중앙값 0.0%·0건 57권(66.3%) · 상위 10권 2,015건(80.5%). HWPX `data/반도체 기초보고서_20260917_정본.hwpx`(비추적, sha256 `aa0f3453…`) — 문단 45·표 14·그림 3, 3단계 삽입 14(문단 2·표 12-3 8×4·표 12-4 11×4)·목차 삽입 2, 숫자 감사 1,168 토큰·미일치 0, `--force` 재실행 바이트 동일. unittest 246 OK·하니스 24/84/390/32/38(대시보드 79→84). 갭 10건(G1~G10, Medium 1·Low 9 — 분야별 등급 합 가드 누락·항등식·문서 계보·테스트 강도)을 정본 재실행 없이 Act-1 로 닫았다(가드·테스트·문구만). `/ship` 리뷰(전문가 5·레드팀·Codex 디자인/적대적/구조화 보이스·Claude 적대적)가 커버리지 갭 4건·유지보수성 9건·단순화 3건·레드팀 3건을 찾아 반영(미사용 필드 삭제, 낡은 주석·수치 정정, 테스트 중복 제거, 대시보드 절 제목·라벨·강조 개선, 평균·중앙값 표본 크기 분리, 표 12-4 캡션의 실제 행 수 반영)했고, Claude 적대적 리뷰가 찾은 3단계 삽입의 중복 빈 문단(선행 2단계 블록 종료 문단과 겹침)도 고쳤다(삽입 15 → 14, sha `aa0f3453…`).
- **한계·이월**(`TODOS.md` "기초보고서 보강 후속"): 한글(HWP) `[→E2E]`(3단계 절의 둘째 문단·목차 5)·6)·" 6) 소결"·쪽 넘김 — Polaris Office 9 대체 확인은 첫 문단·표 12-3·12-4 렌더 정상까지, 표 12-4 가 36/37쪽에 갈리는 문제 확인); B2 보조 분모(이제 `books[].pages` 로 계산 가능); C 교과서 보강·D/E/F·Codex 원저자 항목은 문안 초안 없음.
- **관련 자산**: 정본 `docs/03-analysis/data/semantic_summary.json`(`corpora.*.books[]`·`books_digest`), 대조 JSON `docs/03-analysis/data/hwpx_results_refresh_20260917.json`(`concentration` 블록), 검토 HTML `docs/03-analysis/hwpx-results-refresh/review.html`, 규칙 `CLAUDE.md` 그룹 4 `hwpx_results_refresh.py` "Third stage" 문단.

보관 문서:
- [Plan](ncs-book-concentration/ncs-book-concentration.plan.md)
- [Design](ncs-book-concentration/ncs-book-concentration.design.md)
- [Analysis (갭 + Act-1)](ncs-book-concentration/ncs-book-concentration.analysis.md)
- [Report](ncs-book-concentration/ncs-book-concentration.report.md)
