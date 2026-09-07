# resegment-publish — 재세그먼트 수치 발표 + 마커 결손 하이브리드 배정 (Plan)

> **Feature**: resegment-publish · **Date**: 2026-09-06 · **Status**: Done (같은 날 구현)
> 선행: `resegment.plan.md` / `resegment-results.analysis.md` (PR #13, 2026-09-06 머지)
> 결정 근거: 연구 책임자 결정 2026-09-06 — ① 발표 수치를 재세그먼트 기준으로 교체, ② 마커 결손 쪽의 하이브리드 배정 채택, ③ 짧은 정형구 카운터는 현행 유지

## Executive Summary

| 관점 | 내용 |
|---|---|
| **Problem** | PR #13 이 재세그먼트(실제 쪽 기준 2,173쪽·등급3 147쪽)를 만들었지만 공개 대시보드·README 는 라벨 기준(1,847쪽·108쪽·5.8%)을 그대로 발표했고, 리뷰가 찾은 마커 결손 병합(마커 교재에서 마커가 빠진 쪽이 앞 쪽에 뭉침)은 문서화만 돼 있었다. |
| **Solution** | `resegment.py` 에 `hybrid_pages()`(마커 사이가 2쪽 이상 비면 DP 배정 사용)를 넣어 재실행하고, 그 수치로 `docs/index.html`·`textbook.html`·`osha.html`·README 를 교체하며, 대시보드 하니스의 NCS 쪽 단위 교차검증 정본을 `summary.json.ncs` 에서 `reseg_summary.json` 으로 옮긴다. |
| **Function UX Effect** | 대시보드가 실제 쪽 기준 2,189쪽·등급 1/2/3 = 1,519/525/145(69.4/24.0/6.6%)·사고사례 13쪽을 보여 주고, 라벨 기준 수치는 "이전 발표" 로만 남는다. 연구자 보고서(0906본)의 표 10~12·그림 3·4 도 같은 수치로 맞춘다. |
| **Core Value** | 공개 수치·보고서·저장소 산출물이 하나의 정본(`reseg_summary.json`, `EXPECTED` 회귀 가드)에서 나오고, 마커 결손으로 과다 계수되던 등급3 2쪽이 빠진다. |

## 1. 배경

- PR #13 결과 문서 §6 이 연구 책임자 판단 3건을 남겼다. 2026-09-06 결정: ① 수치 교체, ② 하이브리드 채택, ③ 정형구 카운터 현행 유지 (이 번호를 TODOS·결과 문서 §6 도 같이 쓴다).
- 출하 전 리뷰 F1: 마커 교재 23권은 밀도 0.8 이상이면 마커를 그대로 쓰는데, 마커가 빠진 쪽의 줄이 앞 마커 쪽에 붙는다. CSV `md자수`/`pdf자수` 로 마크다운 본문이 PDF 쪽 본문의 1.7배를 넘는 쪽(PDF 쪽 300자 이상)이 59쪽(마커 교재 48).

## 2. 요구사항

| ID | 요구사항 | 우선순위 | 상태 |
|---|---|---|---|
| FR-01 | `hybrid_pages(lines, marker_lp, dp_lp, n_pages)`: 마커 N 다음 마커가 N+2 이상이면 그 사이 줄은 DP 배정이 [N, 다음−1] 안에 들 때 DP 쪽, 근거 없는 줄은 앞 줄을 잇는다(구간 단조). 마지막 마커 뒤는 PDF 끝쪽까지. 빠진 쪽이 없는 구간·첫 마커 앞은 마커 그대로 | High | Done |
| FR-02 | `resegment_book` 이 마커 교재에서 이를 적용하고 `hybrid_lines`(쪽이 바뀐 줄 수)를 stats·summary 에 남긴다 | High | Done |
| FR-03 | `EXPECTED` 를 Act-3 실행값으로 고정하고 추적 산출물(CSV·JSON)을 재생성한다 | High | Done |
| FR-04 | `docs/index.html` 의 쪽 단위 수치 전부(히어로·KPI·도넛·영역 카드·c1/c3·키워드 표 `pg`·사고사례 표 13행·시사점·권고안)를 Act-3 값으로 교체; 행 단위 수치(7,769건, 키워드 표 검출건수)는 그대로 | High | Done |
| FR-05 | `docs/textbook.html` 비교표 NCS 열, `docs/osha.html` 인용 2곳, README 핵심 수치·알려진 한계 교체 | High | Done |
| FR-06 | `outputs/test-dashboard-data.js` 의 NCS 쪽 단위 검증(D3d·D3e·D3e2·D4a·D4b·D4e~h)을 `reseg_summary.json` 으로 옮기고, `ncs_pages_reseg.csv`·비교표·사고사례 표 행수·시사점/권고안 파생 수치(D13a~k) 교차검증을 추가; 라벨 기준 `summary.json`/`ncs_pages.csv` 검증은 계보 확인용으로 유지 | High | Done |
| FR-07 | 결과 문서·설계·CLAUDE.md·TODOS 에 Act-3 수치와 결정 3건 반영 | Medium | Done |
| FR-08 | 연구자 보고서(0906본)의 표 10~12·그림 3·4·본문 수치를 Act-3 값으로 재생성(`data/`, gitignore) | Medium | Done |

## 3. 범위 밖

- 판정 규칙 변경, 재검색, 교과서 대시보드의 교과서 수치, `recount_grades.py`(라벨 기준 계보 산출물은 그대로 둔다).
- 첫 마커 앞 줄의 DP 보정(제목·머리말이라 마커 쪽이 맞다).

## 4. 성공 기준

- [x] 가드 실행이 EXPECTED 를 통과하고 하니스 5종이 전부 통과한다(대시보드 하니스가 새 정본과 대조).
- [x] 대시보드·README·보고서·결과 문서가 같은 수치(2,189 / 1,519·525·145 / 13쪽)를 인용한다.
- [x] 마크다운 본문이 PDF 쪽 본문의 1.7배를 넘는 쪽(정규화 길이, PDF 쪽 300자 이상 기준 — 결과 문서 §3.6)이 줄어든다(59 → 47쪽; 마커 교재 48 → 36).
