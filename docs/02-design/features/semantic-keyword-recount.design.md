# 의미 단위 키워드 재검산 설계

> **Summary**: 30개 키워드를 통합하지 않고 각각의 의미 표현 사전으로 원문을 재검산하는 데이터 파이프라인
>
> **Author**: Codex
> **Created**: 2026-09-09
> **Status**: Approved
> **Level**: Starter

---

## 1. 구성요소

| 구성요소 | 역할 |
|---|---|
| 입력 판독기 | 원본 XLSX의 30개 시트와 Markdown 98개를 읽고 헤더·페이지 마커 예외 처리 |
| 표현 규칙부 | 키워드별 정확·동등·구체 표현과 동음이의 제외 조건 관리 |
| 매칭부 | Unicode 정규화, 키워드 내 최장 일치, 원문 위치 보존 |
| 집계부 | 키워드·표현·파일·페이지별 결과와 검증 해시 산출 |
| 출력부 | XLSX와 Markdown 보고서 생성 |

## 2. 핵심 데이터 흐름

```text
원본 XLSX + Markdown 98개
          ↓
입력 정규화와 페이지/줄 위치 부여
          ↓
키워드별 독립 표현 규칙 적용
          ↓
동음이의 제외 + 의미 표현 매칭
          ↓
상세행 → 표현별/파일별/키워드별 집계
          ↓
XLSX + Markdown 보고서 + 검증 해시
```

## 3. 불변 규칙

- 기존 30개 키워드를 병합하거나 서로의 확장 표현으로 사용하지 않는다.
- 신규 표현은 정확히 하나의 기존 키워드에만 귀속한다.
- 같은 키워드 안에서는 최장 표현을 한 번만 계수한다.
- 애매한 문맥은 보류하며 포함으로 추정하지 않는다.
- 원본 파일은 수정하지 않는다.

## 4. 상세 명세와 테스트

- 전체 설계: [semantic keyword recount spec](../../superpowers/specs/2026-09-08-semantic-keyword-recount-design.md)
- 실행 계획: [implementation plan](../../superpowers/plans/2026-09-09-semantic-keyword-recount.md)
- 테스트: `python3 -m unittest -v test_semantic_keyword_recount.py`

## 5. 완료 조건

- 30개 키워드, NCS 89개, 교과서 9개 전수 처리
- 상세행과 모든 집계 교차 일치
- 독립 2회 생성 결과의 의미 해시 일치
- XLSX 재열기와 ZIP 무결성 검사 통과

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 1.0 | 2026-09-09 | 승인 명세의 PDCA 설계 요약 | Codex |
