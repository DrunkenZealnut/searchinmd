# Archive Index — 2026-09

보관 산출물 목록. `coding-v1` 은 **폐기된 라벨의 기록**, `recoding` 은 완료된 PDCA 기능 문서다.

| Item | 종류 | 보관일 | 보관 파일 |
|------|------|--------|-----------|
| [coding-v1](coding-v1/) | 1차 수기 코딩 라벨 (무효) | 2026-09-04 | coding_key.json · coding_A.json · coding_B.json |
| [recoding](recoding/) | PDCA 기능 (완료, Match Rate 99.1%) | 2026-09-04 | plan · design · analysis(갭) · report |

## coding-v1

`TODOS.md` P2 와 `docs/04-report/regrade-audit-response.report.md` §1 이 무효로 판정한 69쪽
(분쟁군 39 + 대조군 30) 이중코딩 라벨. 발표된 κ 0.796 / 일치 88.4% 의 **유일한 원자료**라
삭제하지 않고 옮겼다.

- **왜 무효인가**: 코더 A 가 규칙 작성 당사자였고, 코딩 시트가 D1 의 동음이의 가정과
  방향성 동점 규칙을 두 코더에게 흘렸으며, 표본틀이 C-2 버그를 가진 카운터로 뽑혔다.
- **왜 재채점할 수 없는가**: `coding_key.json` 이 `sample_digest` 가드(`9773312`)보다 먼저
  생성돼 지문이 없다. 채점기는 "구버전 산출물" 로 멈춘다 — 가드가 옳다.
- **후속**: `recoding` (docs/01-plan·02-design/features/recoding.*). 루트의 `coding_key.json` 은
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
