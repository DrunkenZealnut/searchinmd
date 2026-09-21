# report-area-crosswalk 완료 보고

> Date: 2026-09-22 | Level: Starter | Status: Complete | Match Rate: 97.4%

## Executive Summary

| 관점 | 내용 |
|---|---|
| **Problem** | 2026-09-19 에 교과서 4영역 대응(『반도체 인프라 일반』 재료 → 장비)이 공용 모듈로 결정됐지만 그 계획은 정본 HWPX·추적 대조 JSON·검토 HTML 을 범위 밖으로 뒀다. 그 결과 코드는 "장비", 출하 문서는 "재료"로 갈라졌고, `CommittedDiffTests` 는 옛 대응을 `mock.patch.dict` 로 되살려 그 불일치를 가리고 있었다. |
| **Solution** | 공용 대응표는 그대로 두고 `hwpx_results_refresh.py` 의 교과서 절 템플릿을 권수로 분기(0권 한 문장·2권 이상 『』 제목 나열)하도록 고치고, 근거 교재가 있는 사고·SDS/GHS 문단을 장부(`_Ledger`)로 장비 블록 뒤에 옮긴 뒤, 원본에서 1·2·3단계를 `--force` 로 재생성했다. 정본 수치·해시·XLSX·`semantic_summary.json` 은 손대지 않았다. |
| **Function/UX Effect** | 보고서 1절 2)는 이제 "장비 분야 2권(『반도체 장비 유지보수』·『반도체 인프라 일반』), 총 414쪽(20.1%)"과 "(4) 반도체 재료 분야 — 반도체 재료 분야로 분류한 교과서는 없었다."로, 표 8 의 재료 행은 0으로 읽힌다. Markdown 4영역 표·HWPX·코드가 같은 대응표 하나를 가리킨다. |
| **Core Value** | "코드가 말하는 분류 = 출하 문서가 말하는 분류". 09-19 결정을 정본 산출물 끝까지 적용하고 역사 mock 을 제거해, 이 리포지토리의 원칙(hwpx-ncs-section-refresh 이후)을 지켰다. |

## 결과

『반도체 인프라 일반』 → 장비 대응(연구책임자 결정, 2026-09-19 확정·2026-09-21 재확인)을 정본 기초보고서 HWPX·추적 대조 JSON·검토 HTML 에 반영했다. 정본 HWPX(`data/반도체 기초보고서_20260917_정본.hwpx`, sha256 `1b46474225e03233…`)의 1절 2) 는 장비 분야가 2권(414쪽, 20.1%, 출현 772건 64.0%)으로 바뀌었고, 재료 분야는 0권(0쪽, 0건)이 되어 표 8 재료 행이 전부 0 이다. 사고·SDS/GHS 문단(근거 교재 『반도체 인프라 일반』)은 장비 블록 끝으로 옮겨졌고, (4) 소제목은 "반도체 재료 분야"로 다시 써서 목차와 일치한다.

## 주요 변경

- `hwpx_results_refresh.py`: `corpus_facts` 가 영역별 교재 제목(`titles`, 대응표 선언 순)을 보존; `area_sentence`(2권 이상 『』 나열, 0권 거부)·`empty_area_sentence`; 리드 문단·본문 소제목 "(4)" 의 영역명을 `AREA_LABEL` 에서 생성; `relocate_accident_paragraph` 가 사고·SDS 문단을 `_Ledger` 로 장비 블록 끝에 이동(복제 삽입 + 원본 삭제, 빈 문단 포함); 문단 루프가 절마다 먼저 전부 찾고 나서 쓰도록 변경(재작성된 문단이 다른 locator 로 시작할 수 있어서).
- `test_hwpx_results_refresh.py`: `CommittedDiffTests` 의 역사 mock 제거, 양쪽 분기(권수 0/1/2 이상)·리드 문단·역방향 감사·0권 거부·E2E 문단 순서·표 8·`relocation` 기록을 검증하는 테스트 추가.
- 정본 산출물 재생성: HWPX(문단 46·표 14·그림 3, 감사 1,167 토큰·미일치 0, layout 126/914/126), 대조 JSON(`hwpx_results_refresh_20260917.json`, 이름은 정본 실행일 그대로), `review.html`. 재실행 바이트 동일(결정론).
- 문서: CLAUDE.md(공용 모듈 불릿·hwpx_results_refresh.py 문단·recount `--skip-xlsx-write` 서술·Test Coverage), README, data README(계보 표기), TODOS(항목 3·5·6).
- 2026-09-19 Codex 세션의 PDCA 문서 4건(`semantic-report-area-symmetry`)을 `docs/archive/2026-09/semantic-report-area-symmetry/` 로 보관, 분석 문서에 "HWPX SHA 는 Polaris 재저장본 기준" 주석 추가.

## 검증

- Python 회귀검사(unittest) **257개** 통과 (`test_semantic_keyword_recount test_hwpx_methods_bridge test_hwpx_results_refresh test_expression_review`)
- 대시보드 검증 **84/84** 통과, 그 외 하니스 24/24·390/390·32/32·38/38 통과
- 정본 HWPX sha256 `1b46474225e03233…` — `--force` 재실행 시 대조 JSON·review.html·HWPX 모두 바이트 동일
- 기존 정본(2026-09-19 13:28 Polaris Office 재저장본, sha `9ef93187…`)은 `<이름>.9ef93187cd38f10e.bak` 로 보존(연구책임자 결정 D4 — 본문 대조는 하지 않음)
- `semantic_summary.json`·`docs/semantic_recount_data.js`·확정 XLSX·대시보드·`reseg_summary.json` — `git diff` 무변경
- 대조 JSON HEAD 대비: 실질 변경은 교과서 절 7문단(리드·개발·제조·장비·소제목·재료·사고 SDS)·표 8·`relocation` 블록뿐; NCS·사고·2·3단계 블록은 숫자·조건 동일(값 출처 `keys` 만 재료→장비로 이동)

## 설계 대비 편차 (Do 단계 수정 1.1)

설계 초안(§3.2)은 재료가 0권일 때 두 원본 문단의 **텍스트를 서로 교환**하는 안이었다. 구현 중 원본에 별도의 본문 소제목 문단("  (4) 반도체 재료·인프라 분야", 목차는 이미 "반도체 재료 분야")이 있음을 실측해, 텍스트 교환만으로는 사고·SDS 문단이 여전히 (4) 블록 안에 남아 "장비 문단 뒤로 이동"(연구책임자 결정 D3 W1)을 만족하지 못했다. 그래서 소제목 재작성 + 2단계 편집 장부(`_Ledger.insert`/`remove`)를 이용한 실제 구조 이동으로 바꿨다(design §3.2a). 이 편차는 결정의 취지를 그대로 지키면서 실측에 맞춰 구현 방법만 바꾼 것으로, 갭 분석에서 결정 위반 없음을 확인했다.

## 남은 항목(이월)

- Polaris Office/한글에서 새 정본의 1절 2) 문단 7개·표 8 렌더 확인 — `[→E2E]`, TODOS "기초보고서 보강 후속" 5. Polaris 는 열람 문서를 Drive 에 자동 업로드하므로 열기 전 계정 설정 확인 필요.
- `docs/archive/2026-09/_INDEX.md` 에 이 기능 절·표 2행과 09-19 기능과의 상호 링크 — archive 단계에서 처리.
- 메모리 갱신(`ncs-book-concentration.md` 의 정본 sha·layout, 신규 `report-area-crosswalk.md`) — 이 보고서 직후 처리.
