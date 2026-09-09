# 의미 단위 키워드 재검산 완료 보고

> **Feature**: semantic-keyword-recount
> **Completed**: 2026-09-09
> **Match Rate**: 100%

## 완료 내용

- 30개 기존 키워드를 병합하지 않고 각각 독립 사전으로 유지했다.
- NCS 89개와 교과서 9개 Markdown을 전수 검색했다.
- 정확 문자열, 동음이의 제외, 동등 표현, 구체 표현을 분리 집계했다.
- 채택 표현 75개와 보류·제외·미출현 후보 25개를 문맥 근거와 함께 기록했다.
- XLSX 10개 시트와 Markdown 결과 보고서를 생성했다.

## 산출물

- `data/semantic_keyword_recount_20260909.xlsx`
- `data/semantic_keyword_recount_20260909_report.md`
- `semantic_keyword_recount.py`
- `test_semantic_keyword_recount.py`
- `docs/03-analysis/semantic-keyword-recount.analysis.md`

## 검증 결과

- Python 단위 테스트 13개 통과
- 기존 JavaScript 회귀 테스트 32개 통과
- XLSX ZIP 무결성 및 openpyxl 재열기 통과
- 요약·표현·파일·상세 집계 전부 일치
- 독립 2회 생성의 source/rule/detail/summary 해시 일치
- 기존 키워드 간 상호 확장 0건, 신규 표현 다중 귀속 0건

## 해석 주의

원본 워크북은 검색 결과 행 수이고 새 결과는 실제 표현 출현 수이므로 증감률을 직접 비교하지 않는다. `전체`는 키워드들을 합친 값이 아니라 각 키워드에 대해 NCS와 교과서 범위를 합친 값이다.
