# Markdown 보고서 4영역 구성 대칭화 설계

> **Summary**: 확정 통계를 변경하지 않고 NCS·교과서 4영역 표와 연구상 교과서 대응 근거를 Markdown에 생성한다.
>
> **Project**: searchinmd
> **Version**: 1.0
> **Author**: Codex
> **Created**: 2026-09-19
> **Status**: Approved — 사용자 실행 지시
> **Level**: Starter
> **Plan**: `docs/01-plan/features/semantic-report-area-symmetry.plan.md`

---

## 1. 결정

- 『반도체 인프라 일반』은 네 비교 영역 중 `반도체장비`로 배정한다.
- 근거는 교재의 주요 구성이 반도체 인프라 전기설비, 공조, 유틸리티, 제조환경과 설비 운용·안전이어서 개발·재료·개별 제조공정보다 장비·시설 계통에 가깝다는 점이다.
- 이 배정은 공식 교육과정 분류가 아니라 NCS 4영역과 비교하기 위한 연구상 대응이다.
- 키워드·등급·전체 출현은 재계산하지 않고, 기존 교과서별 확정값을 네 영역으로 합산하는 위치만 바꾼다.

## 2. 데이터 흐름

```text
AnalysisResult
  → dashboard_payload(result).corpora.*.groups[]
  → semantic_report_areas.area_for(corpus, group)
  → 영역별 documents/total/grades 합산
  → 합계 불변식 검사
  → Markdown의 NCS 표 + 교과서 표 + 교과서 대응 근거표
```

XLSX writer와 등급 판정기는 이 흐름에 포함하지 않는다. Markdown-only 실행은 기존 분석·EXPECTED 검사를 수행하되 `write_workbook()` 호출만 차단한다.

## 3. 공용 분류 인터페이스

`semantic_report_areas.py`가 다음을 제공한다.

```python
AREA_ORDER = ("개발", "제조", "장비", "재료")
AREA_DISPLAY = {
    "개발": "반도체개발",
    "제조": "반도체제조",
    "장비": "반도체장비",
    "재료": "반도체재료",
}
NCS_GROUP_TO_AREA: dict[str, str]
TEXTBOOK_GROUP_TO_AREA: dict[str, str]
TEXTBOOK_CLASSIFICATION_ROWS: tuple[tuple[str, str, str], ...]

def area_for(corpus: str, group: str) -> str:
    """알 수 없는 말뭉치·그룹은 ValueError로 중단한다."""
```

교과서 대응은 개발 3권, 제조 4권, 장비 2권, 재료 0권이다. HWPX 생성 코드는 이 공용 정의를 import하되 현재 HWPX 파일은 이번 작업에서 재생성하지 않는다.

## 4. Markdown 구조

`## 키워드별 집계`와 `## 키워드 순위 통계` 사이에 다음을 넣는다.

1. `## 4영역별 키워드·등급 분포`
2. 단위·분모 설명
3. `### NCS`와 4영역 표
4. `### 교과서`와 연구상 분류 주의 문구
5. 교과서 9권 대응 근거표
6. 교과서 4영역 표

두 분포표의 열은 `영역 | 자료 수 | 전체 | 등급 1 | 등급 2 | 등급 3 | 출현 비율`로 동일하다. 네 영역을 항상 모두 출력하므로 교과서 반도체재료 행도 0건으로 남긴다.

## 5. 불변식과 오류 처리

- 영역별 자료 수 합 = 해당 말뭉치 문서 수
- 영역별 전체 합 = 해당 말뭉치 의미 출현 총계
- 영역별 등급 1·2·3·미확정 합 = 해당 말뭉치 등급별 총계
- 알 수 없는 그룹 = `ValueError`
- XLSX 쓰기 차단 실행에서 XLSX 바이트와 mtime 불변
- NCS 11,517건·교과서 1,207건 및 manifest 네 해시 불변

## 6. 테스트 설계

- 공용 대응표가 교과서 9권을 정확히 한 번씩 포함하는지 검사한다.
- 『반도체 인프라 일반』이 `장비`인지 검사한다.
- 알 수 없는 교과서 제목이 자동 추정되지 않는지 검사한다.
- Markdown에 동일 열의 NCS·교과서 표가 생성되는지 검사한다.
- 교과서 장비 행 `2권·772·276/385/111`, 재료 행 0을 고정한다.
- report-only 실행 전후 XLSX 바이트와 mtime을 비교한다.
- 기존 HWPX·대시보드 회귀 테스트를 실행한다.

## 7. 비범위

- XLSX, 요약 JSON, 대시보드, 현재 HWPX 파일 갱신
- 키워드 사전·등급 판정 변경
- 교과서 총계나 개별 교과서 집계 변경

## Version History

| Version | Date | Changes | Author |
|---|---|---|---|
| 1.0 | 2026-09-19 | 장비 배정과 Markdown-only 생성 설계 확정 | Codex |
