# Gap Analysis: semantic-occurrence-grades

> **2026-09-14 정본 갱신 (semantic-recount-remediation).** 아래 2026-09-09 수치는 코퍼스가 오염된 실행(NCS 89파일 = 교재 84 + 변환기 요약본 4 + 중복 1)의 값이라 **폐기**됐다. 정본은 NCS 86권(2026-09-13 추가 2권 포함)·교과서 9권을 `data_source/markdown` 에서 읽은 2026-09-14 실행이며, 수치는 `docs/03-analysis/data/semantic_summary.json` 이 원본이다. 갱신된 표에는 "정본" 표기가 있다. 외부감사(2026-09-13, 등급 F)와 연구책임자 결정 8건은 `docs/01-plan/features/semantic-recount-remediation.plan.md` §1.2.

> Date: 2026-09-09 | Design: `docs/02-design/features/semantic-occurrence-grades.design.md`

---

## 설계 항목 구현률: 100%

> 2026-09-09 의 "Match Rate" 는 설계 항목이 구현됐는지의 비율이지 의미 정확성(정밀도·재현율·판정자 일치)이 아니다 (감사 m5). 정밀도 검증은 `docs/03-analysis/recoding-results.analysis.md` 계열이 담당한다.

## Summary

설계한 10개 핵심 항목을 모두 구현했다. 기존 페이지 등급은 지정된 NCS·교과서 Excel에서 승계하고, 인덱스에 없는 페이지만 기준선 규칙으로 판정했다. Excel, Markdown 보고서, 대시보드가 같은 출현건수 집계를 사용한다.

## Implemented Items

- [x] `(corpus, canonical_document, page)` 기준의 기존 등급 인덱스
- [x] NCS 능력단위 코드·Unicode·타임스탬프·확장자 정규화
- [x] 정규화 문서명·LM 별칭 중복 시 기존 등급 승계 차단
- [x] NCS 원등급 유지와 교과서 통일 등급 재매핑
- [x] 기존 페이지 승계, 신규 페이지 기준선 판정, 마커 없는 출현 문맥 판정/등급1 (2026-09-13 승인으로 "미확정 분리" 대체)
- [x] 출현 레코드별 등급·등급명·사유·출처 저장
- [x] 요약·파일별·상세 Excel 시트의 등급 출현건수 출력
- [x] Markdown 보고서의 등급별 출현건수 출력
- [x] NCS·교과서 공통 렌더러와 동일한 섹션 순서
- [x] 페이지 수 대신 의미 출현건수를 등급 분모로 사용
- [x] Python·Node 회귀 검사, XLSX 무결성·계보 검사, 실제 Chrome 렌더 확인

## Missing Items

없음.

## Changed Items (Deviations from Design)

- [x] 기존 HTML 틀을 대규모로 재작성하지 않고 `semantic_grade_dashboard.js`가 두 페이지의 내용 영역을 공통 데이터로 렌더하도록 했다. 이는 표시 흐름을 하나로 유지하려는 설계 목적에 부합한다.

## Verification Evidence

- `python3.13 -m unittest test_semantic_keyword_recount.py`: 21/21
- `python3.13 outputs/test-recount-grades.py`: 379/379
- `node outputs/run-core-logic-tests.js`: 32/32
- `node outputs/test-search-equivalence.js`: 24/24
- `node outputs/test-sri.js`: 38/38
- `node outputs/test-dashboard-data.js`: 62/62 (2026-09-14 하니스 복원, S1~S9)
- XLSX ZIP 무결성: 오류 없음
- 등급 계보 검사: NCS 12,062건, 교과서 1,293건의 기존/신규 키 관계 일치

## Recommendations

1. 후속 재집계도 같은 CLI 인자로 등급 원본과 대시보드 데이터를 함께 갱신한다.
2. (해소, 2026-09-14) 813건은 요약본·중복 파일이 원인이었고 코퍼스 정제로 1건만 남아 문맥 판정됐다.

## Next Steps

- [x] 완료 보고 단계로 진행
