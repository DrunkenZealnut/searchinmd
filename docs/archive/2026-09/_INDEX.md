# Archive Index — 2026-09

보관 산출물 목록. `coding-v1` 은 **폐기된 라벨의 기록**, `recoding`·`resegment`·`resegment-publish` 는 완료된 PDCA 기능 문서다.

| Item | 종류 | 보관일 | 보관 파일 |
|------|------|--------|-----------|
| [coding-v1](coding-v1/) | 1차 수기 코딩 라벨 (무효) | 2026-09-04 | coding_key.json · coding_A.json · coding_B.json |
| [recoding](recoding/) | PDCA 기능 (완료, Match Rate 99.1%) | 2026-09-04 | plan · design · analysis(갭) · report |
| [resegment](resegment/) | PDCA 기능 (완료, Match Rate 99%) | 2026-09-07 | plan · design · analysis(갭 Check-1/2) · report |
| [resegment-publish](resegment-publish/) | PDCA 기능 (완료, Match Rate 93%) | 2026-09-07 | plan · design · analysis(갭 Check-1/2) · report |

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
