# resegment-publish — 설계

> **Feature**: resegment-publish · **Date**: 2026-09-06 · **Plan**: `docs/01-plan/features/resegment-publish.plan.md`
> **Status**: Implemented — 결과는 `docs/03-analysis/resegment-results.analysis.md` §3.6

## 1. 하이브리드 배정 (`resegment.py`)

```
마커 교재(밀도 ≥ 0.8)                          정렬 교재
  marker_pages(lines) ─┐                          propagate(align_lines)
  align_lines → propagate(dp) ─┤
  hybrid_pages(lines, marker_lp, dp_lp, n_pages) ─┘
```

| 함수 | 입력 | 출력 | 규칙 |
|---|---|---|---|
| `hybrid_pages(lines, marker_lp, dp_lp, n_pages)` | 줄, 마커 줄→쪽, DP 줄→쪽(전파 완료), PDF 쪽수 | 줄→쪽 | 마커 N(줄 a) 다음 마커 M(줄 b) 이 M ≥ N+2 이면 줄 a+1..b-1 을 순서대로 보며 `cur`(초기 N) 를 DP 쪽 p 가 `cur ≤ p ≤ M-1` 일 때 p 로 올린다 — 근거 없는 줄은 `cur` 를 잇는다(구간 단조). 앵커: 구간 첫 본문 줄의 DP 가 N 보다 앞서면 그 차이를 구간의 모든 p 에서 뺀다(출하 전 리뷰 F1 — 마커 쪽이 비지 않게; `hybrid_emptied_marker_pages` 로 감시). 마지막 마커 뒤는 hi = n_pages. M = N+1 인 구간과 첫 마커 앞 줄은 마커 그대로 |
| `resegment_book(..., stats)` | | | `prefer_markers` 이고 `assigned` 가 있으면 `hybrid_pages` 적용, `stats['hybrid_lines']` = 쪽이 바뀐 줄 수 |
| `aggregate` | | `hybrid_lines` | 교재 합 (summary 최상위 키) |

왜 첫 마커 앞은 손대지 않나: 제목·머리말이라 마커 쪽이 맞고, DP 는 1쪽부터 어디든 놓을 수 있어 오히려 어긋난다.

## 2. 발표 수치의 정본

| 항목 | 정본 | 소비처 |
|---|---|---|
| NCS 쪽 단위(검출 쪽, 등급 분포, 영역별, 키워드별 검출 쪽, 사고사례 쪽) | `docs/03-analysis/data/reseg_summary.json` (`resegment.py`, `EXPECTED` 가드) | `docs/index.html`, `textbook.html` 비교표, `osha.html`, README, 보고서 표 10~12·그림 3·4 |
| NCS 행 단위(검출 7,769건, 키워드 표 검출건수·행 등급·사고사례 검출수) | `docs/03-analysis/data/summary.json` `ncs.rows/row_g/cases_rows` (`recount_grades.py`) | `docs/index.html` 키워드 표, 히어로 검출 항목 |
| 라벨 기준 쪽 단위(1,847 / 108) | `summary.json` `ncs.pages/page_g` + `ncs_pages.csv` — **계보 확인용, 발표하지 않음** | 하니스 D8a~c (그대로) |
| 교과서 | `summary.json.textbook` | `textbook.html` |

## 3. 하니스 (`outputs/test-dashboard-data.js`)

- D3d·D3e·D3e2·D4a·D4b·D4e~D4h 의 비교 대상을 `summary.ncs` → `reseg`(=`reseg_summary.json`) 로.
- D5c 첫 행 검출쪽(안전) = `reseg.kw_pages['안전']`, D9 osha 인용 = `reseg.pages` / `reseg.page_g['3']`.
- 신규 D13a~j(옛 D11 번호는 가로 스크롤 회귀 블록과 겹쳐 D13 으로): `index.html` 히어로 검출 페이지 = `reseg.pages`; 사고사례 표 행수 = `reseg.cases_pages`; 영역 카드 4장의 (쪽, 등급1·2·3) = `reseg.areas`; `textbook.html` 비교표 NCS 열(검출 쪽·등급 3행·0쪽 교재) = `reseg`; `ncs_pages_reseg.csv` 행수·등급 분포·사고사례 = `reseg`; `reseg.meta.expected` 가 있다(가드 통과 실행); D13k1~k4: 시사점·권고안의 교재 단위 파생 수치(등급3 0쪽 교재 총계·영역별, 안전 0쪽 교재, 등급3 보유 교재, 최다 교재 쪽수·비중, 등급1+2 비율, 오탐 10/13) = `reseg.per_book` + CSV 영역; D13l~p(커버리지 감사): c3 개별 값·범례, 영역 카드 비율·막대 폭, reseg 자기 정합, 산문 파생 수치, 구 라벨 수치 잔존 가드. D14·R17: README·CLAUDE.md 가 적은 하니스 단언 수 == 실제.

## 4. 문서

- 결과 문서 §3.6 (Act-3 전후표), 요약·§3.2·§3.3·§4·§6 수치 교체, §6 판단 3건 → 결정 기록.
- `resegment.design.md` §2 표에 `hybrid_pages` 행, `resegment.plan.md` Status 갱신, TODOS 결정 반영, CLAUDE.md 대시보드 정본 규칙·수치, 계보 배너(grade-recount 등)의 2,173→2,189.

## 5. 보고서 (`data/`, gitignore)

0906본을 만든 로컬 편집 스크립트(저장소 밖, 미공개 — hwpx 를 zip+lxml 로 열어 문단·표 셀·그림을 치환)를 Act-3 수치로 바꿔 0905 원본에서 다시 생성(`…_수정0906_2.hwpx`; 수정목록 `…_수정목록0906_2.md` 는 전판 111건 목록에 대한 수치 변경 부록으로만 쓰고, 3장 마크다운 `…_제3장_1-3절_수정0906_2.md` 는 토큰 치환으로 파생): 표 10~12 캡션·셀, 그림 3·4 이미지, 본문 문단(453·511·532 이하)의 2,173/147/6.8%/1,502/524/69.1/24.1/323/561/18.2/14.9/25.8/41.1 → Act-3 값. 3장 마크다운은 토큰 치환으로 파생, 수정목록은 델타 부록.
