# semantic-report-area-symmetry 완료 보고

> Date: 2026-09-19 | Level: Starter | Status: Complete

## 결과

`data/semantic_keyword_recount_20260917_report.md`에 NCS와 교과서의 대칭 4영역 키워드·등급 분포표를 추가했다. 교과서 9권의 배정표와 연구상 분류 주석을 함께 제시했으며, 『반도체 인프라 일반』은 반도체장비로 배정했다.

## 주요 변경

- 4영역 분류를 공용 모듈로 통합
- Markdown에 NCS·교과서 4영역 표와 교과서 9권 근거표 추가
- 알 수 없는 그룹의 자동 추정을 금지하고 생성 중단
- XLSX를 쓰지 않는 `--skip-xlsx-write` 실행 경로 추가
- HWPX 생성 코드도 동일한 공용 대응표를 사용하도록 정리

## 검증

- Python 회귀검사 226개 통과
- 대시보드 검증 84/84 통과
- 확정 XLSX의 SHA-256과 mtime 불변
- 요약 JSON과 현재 HWPX의 SHA-256 불변
- NCS 11,517건, 교과서 1,207건 및 manifest 4종 해시 불변

## 범위 메모

현재 HWPX 정본은 계획에 따라 재생성하지 않았다. 따라서 HWPX 파일 자체는 생성 당시의 영역 배정을 유지하며, 다음 HWPX 재생성부터 공용 분류표의 `반도체 인프라 일반→반도체장비` 대응이 적용된다.

> 후속(2026-09-21): `report-area-crosswalk` 가 그 재생성을 했다 — `docs/archive/2026-09/report-area-crosswalk/` 참조.
