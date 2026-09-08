# marker-offset — 설계

> **Feature**: marker-offset · **Date**: 2026-09-07 · **Plan**: `docs/archive/2026-09/marker-offset/marker-offset.plan.md`
> **Status**: Do 반영판 — §0 의 수치는 구현(`resegment.py` 진단 실행, `EXPECTED.marker_offset`)의 분류 기준으로 다시 적었고, §2·§3 은 구현과 같다. 결정 게이트(§5)는 열려 있다.

## 0. 실측 (설계 근거)

마커 쪽 P 의 md 본문(마커 P 와 다음 마커 사이, `norm_text`, 30자 이상)을 PDF P−3..P+3 쪽과 문자 3-gram 포함률로 대조해 최적 오프셋을 셌다. 정렬(DP) 결과는 쓰지 않는다. 분류는 §2 `classify_offset` 기준(±1 은 최적 포함률 ≥ 0.5 이고 마진 ≥ 0.10 일 때만).

| 구분 | 마커 쪽 | `0` | `1` | `-1` | `amb` | `other` (±2·3) | `short` |
|---|---:|---:|---:|---:|---:|---:|---:|
| 23권 합계 | 2,035 | **1,772 (87.1%)** | 63 | 30 | 59 | 99 | 12 |
| 『반도체 장비 안전관리』 | 154 | 98 (64%) | **26** | 7 | 12 | 8 | 3 |
| 나머지 22권 (각각) | 63~141 | 79~94% | 0~5 | 0~2 | 1~5 | 3~7 | 0~2 |

- ±1 이 뚜렷한 쪽은 93(4.6%)이고 그중 33이 『반도체 장비 안전관리』다. 이 책의 오차는 **연속 구간**이다(55~61 −1, 112~119·142~147 +1). 나머지 22권은 책 단위 상수 오프셋이 없다 → **쪽 단위 보정, ±1 만**.
- `-1` 30 중 20 은 22권의 마지막 마커(마지막 PDF 쪽이 빈 뒷면, 블록은 앞 쪽의 정형 문구) — 보정하면 앞 마커와 같은 쪽으로 합쳐진다.
- ±2·±3 99쪽은 그림·표 위주 쪽이나 반복 정형구로, 최적 포함률 중앙값이 0.10(머리글 수준)이라 옮기지 않는다.
- 포함률 하한 0.5: 마진만 보면 ±1 이 104 인데 그중 11 은 본문의 절반도 인접 쪽에서 못 찾는다(예: 0.16 → 0.31). 그런 쪽으로는 옮기지 않는다(`amb`).
- 마진 중앙값: 장비 안전관리 0.36, 그 밖 0.03~0.20 → 마진 0.10 이면 장비 안전관리의 +1 은 대부분 살고 다른 책의 미세 차이는 `amb` 로 남는다. 민감도는 0.05 / 0.10 / 0.20 으로 영향표(§4)에 병기.
- 사고사례 쪽 8개(33·53·97·103·105·107·110·112) 중 112 만 +1 (0.563 → 0.708); 나머지 7개는 0.
- 연속 구간의 끝 마커는 다음 마커와 한 쪽을 나눠 갖는다(112~119 +1 뒤에 120 이 0). "이웃과 순서가 어긋나면 옮기지 않는다" 를 엄격(strict)하게 두면 구간 끝이 막히고 그 앞이 연쇄로 막혀 **구간 전체가 안 옮겨진다**(설계 초안의 규칙 — 데이터로 기각). 그래서 비감소(같은 쪽 허용)로 정했다.

## 1. 데이터 흐름

```
마커 교재(밀도 ≥ 0.8)                                      main() 안, resegment_book 앞
  lines ──marker_positions──▶ marks [(idx, P)]
  marks + lines ──marker_bodies──▶ {P: 본문}   ┐
  pages_text ──grams──▶ pg[P±k]                ├─▶ marker_offsets(): {P: (best, same, best_c) | None}   ← DP 와 독립
                                               ┘        │
                                    classify_offset(margin) → '0' | '1' | '-1' | 'amb' | 'other' | 'short'
                                                        │
   --marker-correct 없음(기본) ─────────────────────────┼──▶ 진단만: lines 그대로, info(pages·dist·flagged·final_cls)
   --marker-correct MARGIN ───▶ corrected_markers(marks, cls) → marks'(비감소, 같은 쪽 허용; 어긋나면 amb)
                                ──▶ apply_marker_correction(lines, marks') → lines'  ──▶ resegment_book(prefer_markers) 이 lines' 로
                                    marker_pages · hybrid_pages · check_alignment · gap_lines · emptied_marker_pages 전부 보정 마커를 본다
```

`correct_markers(lines, pages_text, margin=None)` 한 함수가 두 경로를 다 맡고 `(lines2, info)` 를 돌려준다. `resegment_book` 의 서명은 바꾸지 않았다(보정은 그 앞 단계). 정렬 교재 61권과 미해결 2권은 손대지 않는다.

## 2. 함수 계약 (`resegment.py`)

| 함수 | 입력 | 출력 | 규칙 |
|---|---|---|---|
| `marker_bodies(lines, marks)` | 줄, 마커 목록 | `{P: 본문(정규화)}` | 마커 P 줄 다음부터 다음 마커 전까지의 줄을 이어 `norm_text`. 마지막 마커는 파일 끝까지. 같은 쪽 번호 마커가 둘이면 첫 것 |
| `marker_offsets(lines, pages_text, k=OFFSET_WINDOW, min_chars=OFFSET_MIN_CHARS)` | 줄, PDF 쪽 텍스트 | `{P: (best, same, best_c) \| None}` | 본문 < min_chars 또는 PDF 범위 안의 후보가 없으면 `None`. best = argmax 포함률(동점이면 \|offset\| 작은 쪽), same = 오프셋 0 포함률, best_c = 최적 포함률. 쪽 3-gram 은 교재 안에서 캐시 |
| `classify_offset(m, margin=OFFSET_MARGIN, min_contain=OFFSET_MIN_CONTAIN)` | 위 튜플 또는 None | `OFFSET_CLASSES` 중 하나 | None → `short`; best == 0 → `0`; \|best\| ≥ 2 → `other`; \|best\| == 1 이고 best_c ≥ min_contain 이며 round(best_c − same, 6) ≥ margin → `1`/`-1`, 아니면 `amb`. 옮기는 것은 `1`/`-1` 뿐 |
| `corrected_markers(marks, cls)` | 마커 목록, {원 쪽: 분류} | `(marks2, cls2)` | `1`/`-1` 만 P±1. 옮긴 쪽은 이웃 마커의 **최종** 쪽 사이(비감소, 같은 쪽 허용)에 들어야 한다. 한 회전에서 어긋난 마커를 모두 원위치·`amb` 로 되돌리고 반복(동시 판정 → 순서 무관, 서로 자리를 바꾸려는 두 마커는 둘 다 막힘). 입력 불변 |
| `apply_marker_correction(lines, marks2)` | 줄, 보정 마커 | 새 줄 목록 | 마커 줄의 숫자만 바꾼다. 입력 불변 |
| `correct_markers(lines, pages_text, margin=None, k, min_chars)` | | `(lines2, info)` | margin None: 진단만(분류는 `OFFSET_MARGIN`), lines2 = lines. margin: 그 임계로 분류 → 보정 → 마커 줄 교체. info = pages(마커 쪽 수)·dist(`OFFSET_CLASSES` 별)·moved·blocked(이웃과 어긋나 못 옮긴 ±1)·flagged{원 쪽: 분류, `0` 제외}·final_cls{최종 쪽: 분류, 한 쪽에 둘이면 `;`}·moved_markers[[줄 idx, 구, 신]] |
| `aggregate` | | + `marker_offset` | 교재의 `marker_offset`(마커 교재만, 정렬·미해결은 None/없음)을 합쳐 `{books, pages, dist, moved, blocked}` |
| `check_expected` | | | `marker_offset` 은 비특수 키라 dict 동등 비교로 자동 대조 |
| `main()` | `--marker-correct MARGIN` | | dense 교재에서 `correct_markers` → 쪽 레코드 `marker_cls`(CSV) · `books[..].marker_offset` · `per_book.marker_offset`(+flagged) · `paged_out.marker_correct/moved_markers` · `meta.marker_correct`. 변형이면 `--limit` 과 같은 경로 가드, `EXPECTED` 불일치는 종료 대신 `meta.expected_mismatch` 에 기록(`meta.expected` None) |

상수: `OFFSET_WINDOW = 3`, `OFFSET_MIN_CHARS = 30`, `OFFSET_MARGIN = 0.10`, `OFFSET_MIN_CONTAIN = 0.5`, `OFFSET_CLASSES = ('0', '1', '-1', 'amb', 'other', 'short')`. 근거는 §0 의 주석으로 코드에 달았다.

## 3. 산출물

| 파일 | 변경 | 비고 |
|---|---|---|
| `reseg_summary.json` | `marker_offset`(최상위 합계 `{books, pages, dist, moved, blocked}`), `per_book.marker_offset`(`{pages, dist, moved, blocked, flagged}` — 마커 교재만; `flagged` 는 `0` 이 아닌 마커 `{원 쪽: 분류}`), `meta.marker_correct`(None 또는 마진) | 진단은 항상, 보정은 채택 후에만 기본 |
| `ncs_pages_reseg.csv` | `마커오프셋` 열을 **`구라벨` 앞**에 추가(13열, `구라벨` 마지막 유지). 마커 교재에서 마커가 (최종적으로) 놓인 쪽만 값, 그 밖은 빈 칸. 보정 실행은 최종 쪽 기준(한 쪽에 마커 둘이면 `;`) | R16j·R16u·D13i 열 수·인덱스 갱신 |
| `EXPECTED` | `marker_offset` 합계 dict(진단: `{'books': 23, 'pages': 2035, 'dist': {'0': 1772, '1': 63, '-1': 30, 'amb': 59, 'other': 99, 'short': 12}, 'moved': 0, 'blocked': 0}`). 채택 시 지문·총계·사고사례 지문과 함께 재고정 | 17키 |
| `data/markdown/ncs_paged/<코드>.pages.json` | `marker_correct` 값과 `moved_markers` | gitignore |

CLI: `--marker-correct MARGIN`(float, 기본 None). 채택 전에는 `--limit` 과 같은 가드 — `--out`/`--paged-dir` 가 기본 경로면 거부한다. 채택 시 기본값을 `OFFSET_MARGIN` 으로 켜고 가드를 푼다.

## 4. 영향표 (결과 문서 §3.7 에 실린 값)

| 항목 | 현행(진단) | 0.05 | 0.10 | 0.20 |
|---|---|---|---|---|
| 옮긴 마커 (23권 / 장비 안전관리) · 막힌 마커 | 0 / 0 · 0 | 100 / 34 · 0 | 93 / 33 · 0 | 82 / 29 · 0 |
| 검출 쪽 / 등급 1·2·3 | 2,189 / 1,519·525·145 | 2,181 / 1,513·521·147 | 2,181 / 1,513·521·147 | 2,181 / 1,511·524·146 |
| 사고사례 쪽 목록 변화 (13쪽 중) | — | 112→113 | 112→113 | 112→113 |
| 『반도체 장비 안전관리』 등급3 (번호가 바뀐 쪽) | 42 | 43 (21) | 43 (21) | 43 (17) |
| 수기 사고사례 표(33·102·105·107·110·111·113)와 일치 — 정확 / ±1 | 4/7 · 7/7 | 5/7 · 7/7 | 5/7 · 7/7 | 5/7 · 7/7 |
| `nogap_*` 자기 검증 (보정 마커 기준) | 88.6 / 98.5 | 90.5 / 98.7 | 90.5 / 98.7 | 90.5 / 98.7 |
| `hybrid_emptied_marker_pages` | 0 | 0 | 0 | 0 |

임계에 둔감(0.05 = 0.10, 0.20 은 등급 3 1쪽 차이). 권고 마진 0.10.

## 5. 결정 게이트

연구 책임자가 §4 를 보고 (a) 미채택 — 진단만 발표(현 상태), (b) 채택 + 마진 선택 을 정한다. (b) 면 FR-06: 기본 켬, `EXPECTED` 재고정, 대시보드 사고사례 표 쪽 번호·README·연구자 보고서(3절, 표 13 대조 문단) 갱신, 결과 문서 §3.1 자기 검증을 보정 마커 기준(90.5/98.7)으로 재기록.

## 6. 테스트 (`outputs/test-recount-grades.py` R16z22~R16z28, `test-dashboard-data.js` D13i·D13q)

| ID | 대상 |
|---|---|
| R16z22 | `marker_bodies`·`marker_offsets`: 오프셋 0 / +1 / −1 픽스처, 30자 미만 `None`(`min_chars` 조정), 동점은 \|offset\| 작은 쪽, k=0, PDF 범위 밖(후보 없음 → `None`, 후보 일부만 → 남은 것 중 최적), 중복 마커 쪽은 첫 것, 마커 없으면 `{}` |
| R16z23 | `classify_offset`: `short`/`0`/`1`/`-1`/`amb`/`other`, 마진 경계(= margin 은 옮김 — 부동소수 반올림), 포함률 하한, `margin` 인자, 상수 4종 |
| R16z24 | `corrected_markers`: +1 연속 구간 끝은 다음 마커와 같은 쪽(허용), 서로 자리를 바꾸려는 둘은 모두 `amb`, 꼬리 −1 은 앞 마커와 같은 쪽, `amb`/`other`/`short` 불변, 첫 마커, 3→4·4→3 충돌은 둘만 막히고 앞은 산다, 빈 입력, 입력 불변; `apply_marker_correction` 은 숫자만 바꾼다 |
| R16z25 | `correct_markers`: 진단(margin None) info, 보정(0.10) 줄·moved_markers·final_cls, 임계 0.9 면 전부 `amb`; 보정 줄로 `resegment_book` → 행이 3·4쪽(진단이면 2·3쪽), 결손 2쪽은 hybrid, 마커 쪽 안 빔, 자기 검증이 보정 마커 기준 전부 정확(원 마커 기준이면 아님) |
| R16z26 | `aggregate.marker_offset` 합(키 없는 교재 제외, 없으면 0), `EXPECTED.marker_offset`(books 23·moved 0·blocked 0), `check_expected` 가 불일치를 한 줄로 짚음, CSV 13열·`마커오프셋` 12번째·`구라벨` 마지막·분류 없는 쪽 빈 칸 |
| R16z27 | `main`: 진단 실행의 JSON/CSV/pages.json 필드, `--marker-correct 0.1` 실행의 행 이동(사고사례 쪽 3)·CSV 최종 쪽 기준·`moved_markers`·`align` 전부 정확·`meta.marker_correct`·`expected` None, 기본 `--out`/`--paged-dir` 거부 |
| R16z28 | 갭 분석 G3: 서로 자리를 바꾸려는 두 마커는 둘 다 막혀 `blocked` 2·`amb`, 분류가 다른 두 마커가 같은 최종 쪽에 놓이면 `final_cls` 는 `;` 로 잇고 CSV 에 그대로 실린다 |
| D13i / D13q | CSV 13열·`마커오프셋`·`구라벨` 마지막 / 발표 실행은 보정 없음(`moved` 0, `meta.marker_correct` null), dist 합 = pages, per_book 합 = 최상위, CSV 값은 분류값뿐 |

## 7. 문서

- 결과 문서 §3.7(실측 + 영향표), §4 한계 문구, §5 재현(변형 명령), §6 6 결정 대기 — 반영.
- CLAUDE.md `resegment.py` 항목(진단·플래그·상수·17키), Testing/Test Coverage 블록(R16z22~z28, D13q, 단언 수 379/153), `docs/03-analysis/data/README.md`(열·키 설명), TODOS ④ — 반영.
- 채택 시 연구자 보고서 3절·표 13 대조 문단.
