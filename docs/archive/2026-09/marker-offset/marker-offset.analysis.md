# marker-offset — 설계·구현 갭 분석 (PDCA Check)

> **Feature**: marker-offset · **Date**: 2026-09-07 · **Phase**: Check (gap-detector 에이전트 대조 + 팀 리드 즉시 수정)
> **대조 문서**: `docs/archive/2026-09/marker-offset/marker-offset.plan.md` (FR-01~FR-07, NFR-01·02, §4 성공 기준, §6 열린 질문) · `docs/archive/2026-09/marker-offset/marker-offset.design.md` (Do 반영판, §0~§7)
> **구현 파일**: `resegment.py` · `outputs/test-recount-grades.py` · `outputs/test-dashboard-data.js`
> **산출물**: `docs/03-analysis/data/reseg_summary.json` · `docs/03-analysis/data/ncs_pages_reseg.csv`
> **문서**: `docs/03-analysis/resegment-results.analysis.md` · `docs/03-analysis/data/README.md` · `CLAUDE.md` · `TODOS.md` · `README.md`
> **브랜치**: `feat/regrade-safety` (변경분 미커밋)

## Match Rate

| 시점 | Match Rate | 산식 |
|---|---|---|
| 1차 대조 (gap-detector) | **93.8% (30 / 32)** | 설계 §2 함수 계약 10항 + §3 산출물 5항 + §4 영향표 1항 + §6 테스트 7항 + §7 문서 2항 + 계획 FR/NFR 7항 = 32항. `✅` 를 일치로, `⚠️`·`❌` 를 불일치로 셈(가중 없음). 연구 책임자 결정 대기인 FR-05·FR-06 과 그에 종속된 §7 세 번째 항목(채택 시 연구자 보고서)은 분모에서 제외 |
| Act-1 (갭 G1~G4 즉시 수정) 후 | **100% (32 / 32)** | ⚠️ 2항(상수 주석, 22권 범위 행)을 고쳤고 Low 갭 G3·G4 도 같이 닫음. 하니스 379/379 · 153/153. gap-detector 재검증 §5 |

## 표 1 — 설계 §2 함수 계약 대조

| 함수 | 설계 | 구현 | 판정 | 비고 |
|---|---|---|---|---|
| `marker_bodies(lines, marks)` | `{P: 정규화 본문}`, 마커 다음 줄~다음 마커 전, 마지막은 파일 끝, 중복 쪽은 첫 것 | `resegment.py` — `zip(marks, marks[1:] + [(len(lines), None)])` + `setdefault` | ✅ | R16z22 |
| `marker_offsets(lines, pages_text, k, min_chars)` | `{P: (best, same, best_c) \| None}`, 동점은 \|offset\| 작은 쪽, 쪽 3-gram 교재 내 캐시 | `max(cont, key=lambda o: (cont[o], -abs(o)))`, `pg` 딕셔너리 캐시 | ✅ | 본문 < `min_chars` 또는 후보 없음 → `None` |
| `classify_offset(m, margin, min_contain)` | `None→short`, `best 0→'0'`, `\|best\|≥2→other`, ±1 은 `best_c ≥ min_contain` 이고 `round(best_c−same, 6) ≥ margin` 일 때만 부호, 아니면 `amb` | 조건·반올림까지 동일 | ✅ | R16z23 (6클래스·경계·`margin` 인자·상수 4종) |
| `corrected_markers(marks, cls)` | `(marks2, cls2)`, `1`/`-1` 만 P±1, 이웃의 **최종** 쪽 사이 비감소, 어긋난 것은 한 회전에서 모두 되돌리고 `amb`, 입력 불변 | `while True` 로 `bad` 를 모아 일괄 되돌림, `cls2 = dict(cls)`, 새 리스트 반환 | ✅ | R16z24 (자리 맞바꿈·연쇄·꼬리 −1), R16z28 |
| `apply_marker_correction(lines, marks)` | 마커 줄의 숫자만 교체, 입력 불변 | `MARKER_RE.search` 후 `group(1)` 스팬만 치환, `out = list(lines)` | ✅ | 줄 중간 마커도 앞뒤 보존 |
| `correct_markers(lines, pages_text, margin, k, min_chars)` | `(lines2, info)`, `margin None` 이면 진단만, info 7키 | 반환 키 `pages`·`dist`·`moved`·`blocked`·`flagged`·`final_cls`·`moved_markers` | ✅ | `flagged` 는 `0` 제외, `final_cls` 는 최종 쪽 기준 `;` 결합 (R16z25·R16z28) |
| `aggregate` + `marker_offset` | 교재별 값을 `{books, pages, dist, moved, blocked}` 로 합산, 키 없는 교재 제외 | 구현 동일 | ✅ | R16z26 |
| `check_expected` | `marker_offset` 은 비특수 키라 dict 동등 비교로 자동 대조 | `special` 목록에 없음 | ✅ | 불일치를 한 줄로 보고 (R16z26) |
| `main()` | `--marker-correct MARGIN`, `marker_cls`·`per_book.marker_offset`·`paged_out`·`meta.marker_correct`, `--limit` 과 같은 경로 가드, EXPECTED 불일치는 종료 대신 기록 | 플래그·가드·호출 위치·기록 전부 구현 | ✅ | 변형 실행은 `meta.expected = None` + `expected_mismatch`, `sys.exit` 안 함 (R16z27) |
| 상수 5종 (`OFFSET_WINDOW` 3, `OFFSET_MIN_CHARS` 30, `OFFSET_MARGIN` 0.10, `OFFSET_MIN_CONTAIN` 0.5, `OFFSET_CLASSES`) | 값 + "근거는 §0 의 주석으로 코드에 달았다" | 값 전부 일치; 1차 대조 때 주석의 근거 수치 2개(2,023 쪽 / ±2·3 45쪽)가 실측(2,035 / 99)과 불일치 | ⚠️ → ✅ | 갭 G1 — Act-1 에서 정정 |

## 표 2 — 설계 §3 산출물 · §4 영향표 · §6 테스트 · §7 문서 대조

| 구분 | 설계 | 구현·산출물 | 판정 | 비고 |
|---|---|---|---|---|
| §3 `reseg_summary.json` | 최상위 `marker_offset {books, pages, dist, moved, blocked}`, `per_book.marker_offset {pages, dist, moved, blocked, flagged}`, `meta.marker_correct` | `{books: 23, pages: 2035, dist: {0:1772, 1:63, -1:30, amb:59, other:99, short:12}, moved: 0, blocked: 0}`; 마커 교재 23권만 `per_book` 키 보유(5키); `meta.marker_correct = null` | ✅ | `per_book` 합 == 최상위 합, `dist` 합 == `pages` |
| §3 `ncs_pages_reseg.csv` | 13열, `마커오프셋` 12번째, `구라벨` 마지막, 마커 쪽만 값 | 헤더 13열, 인덱스 11 = `마커오프셋`, 12 = `구라벨`; 2,189행 전부 13열; 값은 `0`·`1`·`-1`·`amb`·`other`·`short`·빈 칸만 | ✅ | 직전 커밋 CSV 와 12번째 열을 뺀 나머지가 완전 동일 — 발표 수치 불변 |
| §3 `EXPECTED` 17키 | `marker_offset` 합계 dict 고정 | 값이 `reseg_summary.json` 과 문자 단위 동일, 키 수 17 (16 → +1). `meta.expected` 도 17키 | ✅ | |
| §3 `pages.json` | `marker_correct` 값과 `moved_markers` | 코드로 확인 (gitignore) | ✅ | R16z27 이 임시 디렉터리 실행으로 두 필드 검증 |
| §3 CLI 가드 | 변형은 기본 `--out`/`--paged-dir` 거부 | `--limit` 과 같은 `realpath` 비교, 메시지에 플래그명 표시 | ✅ | R16z27 이 세 가지 거부 경로 검증 |
| §4 영향표 | 마진 0.05/0.10/0.20 3열, 8항목 | 결과 문서 §3.7 표에 13항목으로 실림 — 설계 §4 의 8항목 값이 전부 일치 | ✅ | 결과 문서가 분야별·`hybrid_lines`·`page_grade_digest` 등 5항목 추가 |
| §6 R16z22 | `marker_bodies`·`marker_offsets` 픽스처 9종 | 0/+1/−1, `min_chars` 조정, 동점, k=0, PDF 범위 밖, 중복 마커, 빈 입력 | ✅ | |
| §6 R16z23 | `classify_offset` 6클래스·마진 경계·포함률 하한·`margin` 인자·상수 4종 | 12개 케이스 + 상수 튜플 비교 | ✅ | 경계값 `= margin` 이 옮겨지는지(부동소수 반올림)까지 |
| §6 R16z24 | `corrected_markers` 7시나리오 + `apply_marker_correction` | 연속 구간 끝·자리 맞바꿈·꼬리 −1·불변 클래스·첫 마커·3↔4 충돌·빈 입력·입력 불변 | ✅ | |
| §6 R16z25 | `correct_markers` 진단/보정/고임계 + `resegment_book` 연동 | 5쪽 PDF 픽스처로 행 배치·hybrid·비워진 쪽·자기 검증 대조 | ✅ | 보정 줄 기준 `exact == lines`, 원 마커 기준 `exact < lines` |
| §6 R16z26 | `aggregate` 합·`EXPECTED`·`check_expected`·CSV 열 | 구현 | ✅ | |
| §6 R16z27 | `main` 진단/변형 완주 + 경로 거부 | 가짜 `fitz` 로 두 번 완주, 사고사례 쪽 3, `moved_markers`, `align` 전부 정확, `meta.marker_correct`·`expected` None | ✅ | Act-1 에서 G4 문구 단언 추가 |
| §6 R16z28 (Act-1 추가) | — | 자리 맞바꿈(`blocked` 2)·`final_cls` `;` 결합·CSV 반영 | ✅ | 갭 G3 |
| §6 D13i / D13q | CSV 13열 / 발표 실행은 보정 없음 | D13q 가 `moved`·`blocked` 0, `meta.marker_correct === null`, `dist` 합 == `pages`, `per_book` 합 == 최상위, CSV 값 집합 검증 | ✅ | |
| §7 결과 문서 | §3.7 실측·영향표, §4 한계, §5 재현, §6 6 결정 대기 | 모두 반영, §3.1 은 설계대로 미수정; 1차 대조 때 §3.7 측정표의 "나머지 22권 (각각)" 범위가 산출물과 불일치 | ⚠️ → ✅ | 갭 G2 — Act-1 에서 정정 |
| §7 기타 문서 | CLAUDE.md `resegment.py` 항목·Testing·Test Coverage, `data/README.md`, TODOS ④, 단언 수 | 반영; 인용 단언 수는 README·CLAUDE.md 양쪽 379/153 으로 동일 — R17·D14 가 두 곳 모두 파싱 | ✅ | |

## 표 3 — 계획 FR/NFR 충족표

| ID | 상태 | 근거 |
|---|---|---|
| FR-01 `marker_offsets` (DP 독립 측정) | 충족 | 정렬 결과를 인자로도 내부에서도 쓰지 않고 `marker_positions` + PDF 쪽 텍스트만 사용. 서명은 설계 §2 가 확정한 형태(편차 D4) |
| FR-02 진단을 산출물에 실음 | 충족 | 최상위·`per_book`(`flagged` 포함)·CSV 12번째 열·`EXPECTED`. 커밋된 산출물로 확인 |
| FR-03 보정 규칙 변형 `--marker-correct` | 충족 | 기본 None, 추적 산출물 거부, 비감소 규칙, 마커 줄 교체, `marker_pages`·`hybrid_pages`·자기 검증이 모두 보정 마커를 봄 |
| FR-04 영향표 | 충족 | 결과 문서 §3.7 — 마진 3종, 옮긴/막힌 마커·검출 쪽·등급 분포·사고사례·수기 표 일치·`nogap_*`·`hybrid_emptied_marker_pages` |
| FR-05 연구 책임자 결정 게이트 | **대기** | 결과 문서 §6 6 "[결정 대기]", `TODOS.md` ④. 선택지 (a) 미채택 / (b) 채택+마진, 권고 마진 0.10 기록 |
| FR-06 채택 시 적용 | **대기** | FR-05 종속. 현재 `EXPECTED.marker_offset.moved = 0`, 대시보드·README·보고서 미변경 |
| FR-07 하니스 | 충족 | R16z22~R16z28, D13i·D13q; 갱신분 R16j·R16u·R16v(17키)·R16z5(13열) |
| NFR-01 실행 시간 (+10초 미만) | 충족 (구조 판단) | PDF 쪽 3-gram 을 교재 내 딕셔너리에 지연 캐시해 쪽당 1회만 계산. 추가 비용은 교재당 `쪽 수` 회의 gram 생성 + `마커 수 × 7` 회의 집합 교집합 — 이미 도는 `align_lines`(`줄 수 × 쪽 수` 회)의 소수점 아래 비율. 실측 실행도 종전과 같은 약 30초 |
| NFR-02 재현성 | 충족 | `EXPECTED` 17키, 변형·부분 실행의 추적 산출물 거부, 변형은 `meta.expected` None + `expected_mismatch` 기록, 진단 실행은 `--force` 없이는 종료 |

계획 §4 성공 기준 4개 중 1·2·4 는 충족, 3 은 결정 기록만 완료·채택 반영은 대기. 1의 후반부 "『반도체 장비 안전관리』의 값이 리뷰 실측(0: 64%, +1: 23%)과 ±2%p 안에서 재현" 은 `0` 은 63.6%(98/154)로 충족하지만 `+1` 은 16.9%(26/154)로 미충족이며, 원인은 설계에서 새로 넣은 포함률 하한이다(편차 D2 — 결과 문서 §3.7 마지막 불릿이 설명).

커버리지: 신규 코드 약 100줄(마커 오프셋 함수 6개 + `aggregate`·`main` 배선)에 대해 R16z22~z28 7개 단언이 6함수 전부와 `aggregate`·`check_expected`·`write_outputs`·`main`(진단·변형·거부 3종)을 덮는다. 1차 대조에서 미실행이던 분기 2개(G3)는 R16z28 이 지난다 — 목표 80% 초과.

## 4. 갭 목록과 Act-1 조치

| ID | 심각도 | 위치 | 내용 | 조치 (2026-09-07, Check 중 즉시) |
|---|---|---|---|---|
| G1 | Low | `resegment.py` 상수 주석 | 근거 수치 2개가 같은 파일의 `EXPECTED` 와 어긋남 — "2,023 마커 쪽"(측정된 쪽 수 = 2,035 − short 12 를 마커 쪽 수로 적음), "±2·±3 45쪽"(프로브 중간값; `other` 는 99) | 정정: "2,035 마커 쪽", "±2·±3 은 99쪽(…, 최적 포함률 중앙값 0.10)" |
| G2 | Medium | 결과 문서 §3.7 측정표 · 설계 §0 표 | "나머지 22권 (각각)" 행 다섯 칸이 `per_book.marker_offset` 재집계와 불일치(마커 쪽 63~158 은 PDF 쪽 수 최댓값을 섞은 것, `-1` 하한 1 은 0 인 교재가 있어 틀림) | 두 문서 모두 `63~141 \| 79~94% \| 0~5 \| 0~2 \| 1~5 \| 3~7 \| 0~2` 로 정정. 결론("책 단위 상수 오프셋 없음")은 불변 |
| G3 | Low | `correct_markers` 의 `blocked` 집계, `final_cls` 의 `;` 결합 | 두 분기를 지나는 픽스처가 없었다(R16z25 는 `blocked` 0, 고임계 실행은 `classify_offset` 단계에서 전부 `amb`; `;` 는 분류가 다른 두 마커가 같은 쪽에 놓여야 발동) | R16z28 추가: 자리 맞바꿈 픽스처(`blocked` 2·`moved` 0·`amb`·줄 불변), 마커 1(+1)이 마커 2(0)와 같은 쪽에 합류하는 픽스처(`final_cls {2: '1;0'}`, `moved_markers [[0, 1, 2]]`) + CSV 열에 `1;0` 반영 |
| G4 | Low | `main()` EXPECTED 경고 print | 변형 실행은 `--force` 없이 쓰는데 콘솔에 "(--force 로 씀)" 이 항상 출력됨 | `args.force` 로 분기("--force 로 씀" / "변형 실행이라 기록만 함"); R16z27 에 두 실행의 출력 문구 단언 추가 |

하니스: 갭 수정 후 `test-recount-grades.py` 379/379, `test-dashboard-data.js` 153/153 (README·CLAUDE.md 인용 수치 379/153 갱신, R17·D14 통과). 나머지 세 하니스(24/24, 32/32, 38/38)는 이 기능과 무관하며 변경 전 확인.

## 5. 문서화된 편차 (갭 아님)

| ID | 편차 | 기록 위치 |
|---|---|---|
| D1 | 이웃 순서 제약을 **엄격 → 비감소**(같은 쪽 허용)로 변경. 엄격하게 두면 연속 구간의 끝 마커가 막히고 그 앞이 연쇄로 막혀 구간 전체가 안 옮겨진다 — 데이터로 기각 | 설계 §0 마지막 불릿, §2 `corrected_markers` 행, 결과 문서 §3.7 |
| D2 | 계획에 없던 **포함률 하한 `OFFSET_MIN_CONTAIN` 0.5** 추가. 부수 효과로 계획 §4 의 "+1 23% ±2%p" 성공 기준은 재현되지 않는다(하한 없이 세면 +1 이 31, 하한 적용 26) | 설계 §0 5번째 불릿, §2 `classify_offset`, 결과 문서 §3.7 마지막 불릿 |
| D3 | 보정을 `resegment_book` 의 인자가 아니라 `main()` 안 `correct_markers` 의 전단계로 배치 — `resegment_book` 서명 불변 | 설계 §1 마지막 문단 |
| D4 | 계획 FR-01 의 `marker_offsets(lines, marker_lp, pages_text, …)` 에서 `marker_lp` 인자 제거(내부에서 `marker_positions` 로 유도) | 설계 §2 서명 |
| D5 | 계획의 상수명 `MARKER_SHIFT_MARGIN` → `OFFSET_MARGIN` + CLI 인자화 | 설계 §2 상수 문단 |
| D6 | 계획 FR-02 의 `per_book.marker_offset {pages, dist, ambiguous}` → `{pages, dist, moved, blocked, flagged}` (`ambiguous` 는 `dist.amb` 로 흡수) | 설계 §3 표 |

gap-detector 재검증 (Act-1 후, 2026-09-07): G1~G4 모두 닫힘을 확인 — 상수 주석 2건이 `EXPECTED`·`reseg_summary.json` 과 일치, 22권 범위 행이 두 문서에서 같고 `per_book.marker_offset` 재집계와 전부 일치, R16z28 이 `blocked`·`;` 결합 분기를 실제 호출로 지나며 CSV 반영까지 단언, R16z27 이 경고 문구 세 조건을 단언. 인용 단언 수 379/153 정합. **갱신된 Match Rate 32/32 = 100%, 미해결 갭 없음.**

## 6. 권고

**Match Rate 100% (32 / 32, Act-1 후; 1차 93.8%) ≥ 90% → `/pdca report marker-offset` 진행.** 기능·산출물·하니스·문서 배선은 설계와 일치하고, 발표 수치는 진단 열 추가를 빼면 직전 커밋과 완전히 동일하다(CSV 는 12번째 열만 삽입, JSON 은 `marker_offset`·`per_book.marker_offset`·`meta.marker_correct` 세 필드만 추가). FR-05·FR-06(채택 여부·마진)은 연구 책임자 결정 대기이며 보고서에는 "결정 대기" 로 적는다.
