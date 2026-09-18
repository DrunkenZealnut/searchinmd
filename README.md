# SearchInMD — 마크다운 키워드 검색기

마크다운 문헌 더미에서 키워드를 찾아 Excel로 떨어뜨리는 브라우저 도구, 그리고 그 결과로 만든 안전보건 분석 대시보드.

청년노동자인권센터의 2026년 교과서 기초연구에서, NCS 반도체 교재 86권과 반도체 특성화고 교과서 9권이 안전보건을 어떻게 다루는지 조사하려고 만들었습니다.

## 대시보드 (GitHub Pages)

최신 키워드 검색·등급분류 결과는 [분리 분석 페이지](https://drunkenzealnut.github.io/searchinmd/keyword-analysis.html)에서 확인할 수 있습니다. NCS 교재 86권·교과서 9권 기준이며, 정본 실행(2026-09-17, `semantic_keyword_recount_20260917.xlsx` — NCS 출현을 실제 PDF 쪽에 놓고 교재별 집계를 더한 실행)의 산출물 `docs/03-analysis/data/semantic_summary.json` 하나에서 대시보드·분리 분석 페이지·이 README 의 수치가 나옵니다.

| 페이지 | 내용 |
|---|---|
| [NCS 교재 86권](https://drunkenzealnut.github.io/searchinmd/) | 의미 출현 11,517건(출현건수 기준)의 등급 분포, 영역별 현황, 교재별 현황(86권, 등급3 내림차순 — 안전관리 전용 2권의 집중도 표시), 키워드별 상세 · 이전 기준(실제 쪽 2,189쪽)과의 브리지 표 병기 |
| [반도체고 교과서 9권](https://drunkenzealnut.github.io/searchinmd/textbook.html) | 검출 362쪽·전체 2,055쪽 두 분모를 병기, NCS 대비 비교는 검출쪽 기준 |
| [OSHA 안전교육](https://drunkenzealnut.github.io/searchinmd/osha.html) | 미국 OSHA 반도체 화학물질 안전교육 과정과의 비교 |

핵심 수치 하나만 옮기면 — **구체적 안전대책(등급3) 페이지에 놓인 키워드 출현 비율은 NCS 21.7%, 교과서 9.5%** 입니다(둘 다 등급 확정 출현 분모: 2,502/11,517 과 115/1,207; 의미 출현 총계 NCS 11,517건 · 교과서 1,207건, 연구책임자 결정 2026-09-13 으로 분모를 출현건수로 바꿈; 사전 v2 — 2026-09-14 표현 점검으로 뜻이 다른 확장 표현을 걷어낸 결과이며, 이전 사전 v1fix 의 20.9%/9.2% 에서 오른 것은 분모가 줄어든 구성 효과입니다 — [표현 점검 결과](docs/03-analysis/expression-review.analysis.md) §6; 2026-09-15 부터 NCS 출현은 목차 블록이 아니라 **실제 PDF 쪽**에 놓고 그 쪽 본문에 규칙 하나로 판정합니다 — 블록 기준 v2 의 21.9%(4,378/4,614/2,525)에서 등급3 은 거의 그대로이고 등급1→2 이동이 큽니다, [영향표](docs/03-analysis/data/occurrence_real_pages_impact.json)). **이전 기준**(페이지 단위, 2026-09-06 재세그먼트)으로는 NCS 6.6%(145/2,189)·교과서 2.2%(8/362)이며, 두 값은 같은 실제 PDF 쪽 기준·같은 판정 규칙이지만 검출 쪽 집합은 다릅니다(의미 재검산이 닿은 실제 쪽 2,492개 vs 이전 기준 2,189쪽, 공유 쪽 2,035개는 등급이 전부 일치) — 비율 차이는 집계 단위(출현건수 vs 쪽)와 그 가중 때문이며 교재가 나아진 것이 아닙니다 — 대시보드의 "이전 기준과의 관계" 절과 [등급 결합 보고서](docs/04-report/features/semantic-occurrence-grades.report.md)의 브리지 표를 보십시오.

교과서는 전체 쪽수를 알기에 다른 각도로도 볼 수 있습니다 — **9권 2,055쪽 중 구체적 대책은 8쪽(0.39%)** 이고, 그중 6권은 0쪽입니다. NCS 는 전체 쪽수 대비 비율을 산출하지 않습니다(원본 PDF 86권 9,100쪽을 확보해 2026-09-15 부터 분야별 쪽수는 이 값이지만, 등급 비율의 분모는 출현건수·검출 쪽으로 통일했습니다). 분모가 다른 두 값을 나란히 빼면 안 됩니다.

## 검색 앱 실행

브라우저에서 도는 클라이언트 사이드 앱입니다. 문헌이 서버로 올라가지 않습니다.

```bash
python3 outputs/server.py          # 기본 3008 포트
python3 outputs/server.py 9000     # 포트 지정
# http://localhost:3008/search_in_md
```

**Chrome 또는 Edge가 필요합니다** — 폴더 선택에 File System Access API(`showDirectoryPicker`)를 씁니다. Safari·Firefox는 지원하지 않습니다.

처음이라면 [**첫 검색 튜토리얼**](docs/tutorial-first-search.md)이 저장소에 든 샘플 문서로 검색부터 내보내기까지 10분 만에 한 바퀴 돌려줍니다. 준비할 자료가 없습니다.

쓰는 법:

1. 키워드 하나당 시트 하나인 Excel 파일을 올립니다. **시트 이름이 곧 검색 키워드**이고, 각 시트의 1행 헤더가 결과 열 구성이 됩니다.
2. 마크다운 문헌이 든 폴더를 고릅니다. 하위 폴더까지 훑어 `.md`와 짝이 되는 `_meta.json`을 모읍니다.
3. 검색합니다. 문장·표·이미지를 각각 켜고 끌 수 있고, 대소문자 구분과 로컬 LLM 하이브리드 모드가 선택 사항입니다.
4. 내보내면 **원본 통합문서 구조를 보존한 채** 시트별로 결과 행이 추가됩니다.

방법론 전체는 `키워드기반_문서분류분석_방법론.hwpx`에 있습니다 — 6단계 파이프라인, 제목 판정 규칙, 행번호를 PDF 페이지로 맞추는 위치 정합 알고리즘.

## 산출물 재생성 (원본 보유 시)

대시보드 수치는 손으로 넣지 않았습니다. 정본은 원본 마크다운·엑셀에서 `semantic_keyword_recount.py` 로 뽑고(아래), 이전 기준인 NCS 쪽 단위 수치는 원본 PDF 까지 써서 `resegment.py` 로 냅니다.

**원본이 있어야 실행됩니다.** 없으면 커밋된 `docs/03-analysis/data/` 가 곧 산출물입니다 — 스크립트는 원본을 못 찾으면 안내 메시지를 내고 종료합니다.

```bash
pip install openpyxl
python3 recount_grades.py                    # data/ 에서 읽는다
python3 recount_grades.py --data /other/path # 다른 위치 지정
```

원본 워크북 2종을 읽어 통일 등급체계로 재매핑하고, **고유 페이지 단위로** 집계해 `docs/03-analysis/data/`에 CSV와 `summary.json`을 씁니다. 기대값 회귀 검증이 내장돼 있어 수치가 어긋나면 산출물을 쓰지 않고 멈춥니다.

원본 엑셀(`data/`, 67MB)은 저장소에 없습니다 — 비공개 교재에서 뽑은 자료라 `.gitignore` 대상입니다. 산출된 CSV·JSON만 커밋합니다.

원본이 있으면 검증용 스크립트 둘을 더 돌릴 수 있습니다. **둘 다 대시보드 수치를 바꾸지 않습니다.**

```bash
python3 regrade.py --validate    # 페이지 본문에서 등급을 다시 계산해 현재 규칙의 재현율만 확인
python3 regrade.py               # 결함별 영향도를 docs/03-analysis/data/regrade_impact.json 에 기록
python3 truncation_audit.py      # 엑셀 셀 한도에서 잘린 본문을 전수 재측정 (pip 패키지 불필요)
```

`regrade.py` 는 원본 채점 규칙을 되짚어 만든 재채점기입니다. 어떤 결함을 고치면 등급 분포가 어떻게 움직이는지 항목별로 떼어 보여줄 뿐, 발표 수치를 교체하지 않습니다 — 채택 여부는 `TODOS.md` P2 에 열린 채로 있습니다.

규칙의 정밀도·재현율을 AI 코더로 잰 **재코딩 파이프라인**(`make_coding_sheet.py` → `code_pages.py` → `score_coding.py`)도 원본이 있어야 돕니다. 코더 API 키가 필요하고 비용이 들며, 실행 순서와 결과는 [재코딩 결과 분석](docs/03-analysis/recoding-results.analysis.md) §9 에 있습니다. 채점 수치(`docs/03-analysis/data/recoding_scores*.json`)와 라벨(`coding_key.json`, `coding_A/B/C.json`)은 커밋돼 있고, 이것도 발표 수치를 바꾸지 않습니다.

**의미 단위 재검산**(`semantic_keyword_recount.py`)이 대시보드의 정본입니다. 원본은 `data_source/markdown/` (비추적, 연구책임자 지정; `data/markdown/` 은 그 복사본)이고, 2026-09-13 에 추가된 NCS 2권은 변환기가 마커를 0-based 로 심어 `shift_page_markers.py` 로 +1 했습니다(`python3 shift_page_markers.py <file.md> --by 1 --backup`, 자세한 절차는 [페이지 마커 how-to](docs/howto-page-markers.md); `semantic_keyword_recount.py` 는 마커가 1 미만인 파일을 만나면 실행을 거부합니다). 같은 실행에서 xlsx·보고서·`docs/semantic_recount_data.js`·`docs/03-analysis/data/semantic_summary.json`·분리 분석 HTML 3건이 나오며, 내장 `EXPECTED` 가드가 어긋나면 아무것도 쓰지 않습니다(`--force` 로 쓰고 나서 `EXPECTED` 를 갱신).

```bash
pip install openpyxl
python3 semantic_keyword_recount.py \
  --source-workbook data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx \
  --ncs-root data_source/markdown/ncs --school-root data_source/markdown/school-text \
  --xlsx-out data/semantic_keyword_recount_20260917.xlsx --report-out data/semantic_keyword_recount_20260917_report.md \
  --dashboard-data-out docs/semantic_recount_data.js --summary-out docs/03-analysis/data/semantic_summary.json \
  --analysis-dir docs --previous-basis docs/03-analysis/data/reseg_summary.json \
  --page-maps data/markdown/ncs_paged --reseg-csv docs/03-analysis/data/ncs_pages_reseg.csv
```

`--page-maps` 는 `resegment.py` 가 남긴 줄→실제 PDF 쪽 대응(`data/markdown/ncs_paged/<LM코드>.pages.json`, 84권, 비추적)입니다 — 2026-09-15 부터 NCS 출현은 목차 블록 표식이 아니라 이 대응으로 실제 쪽에 놓이고 그 쪽 본문에 규칙 하나로 등급이 판정됩니다(`occurrence-real-pages`; 대응이 없는 2권 `LM1903060408`·`LM1903060424` 는 표식이 실제 쪽이라 그대로, `REAL_PAGE_MARKER_BOOKS`). `--reseg-csv` 는 이전 기준 쪽 등급과의 일치(공유 쪽 2,035개 전부 일치)를 `meta.run.reseg_agreement` 에 남기고 `EXPECTED` 가 그 값을 고정합니다. 대응 없이 돌리면 `page_basis` 가 어긋나 정본으로 쓰이지 않습니다. 블록 기준(2026-09-14)과의 차이는 `python3 occurrence_real_pages_impact.py --source-workbook … --ncs-root … --school-root … --page-maps data/markdown/ncs_paged` 가 `docs/03-analysis/data/occurrence_real_pages_impact.json` 에 남깁니다(총계 불변, 등급 이동 4,016건). 교과서 등급 워크북(`ncs_keywords_in_markdown_results_교과서_results_20260415.xlsx`)은 `--source-workbook` 과 같은 폴더에서 자동으로 찾고, 없으면 멈춥니다(`--school-grade-workbook` 으로 따로 지정). 실행 명령·입력 파일별 sha256·git commit 은 `semantic_summary.json` 의 `meta.run` 에 남으므로, 수치가 어긋나면 어느 입력이 달라졌는지 거기서 추적합니다.

정본이 아닌 사전(`--dictionary v1` 또는 `v1fix`)은 **변형 실행**이라 `docs/` 아래와 정본 기본 이름으로는 쓰지 못하고, `EXPECTED` 불일치를 `meta.run` 에 기록만 합니다. 사전을 v2 로 고른 근거인 **표현 점검**(`expression_review.py sample` → `code_pages.py` 코더 2계열 → `score` → `impact`)은 실행 순서와 결과가 [표현 점검 결과](docs/03-analysis/expression-review.analysis.md) §8 에 있고, 대시보드 수치를 바꾸지 않습니다. 기초보고서 **HWPX 재작성**(`python3 hwpx_results_refresh.py --force` — 기존 정본이 있으면 `--force` 가 필요하고 그 파일은 `.bak` 로 남는다; 원본 `data/반도체 기초보고서_20260911.hwpx` → 새 파일 `…_{정본 실행일}_정본.hwpx`, 2026-09-17 정본이면 `…_20260917_정본.hwpx`)은 숫자를 추적된 `semantic_summary.json`·`accident_case_pages.json`·`summary.json` 에서만 가져와 제3장 1~3절의 문단·표·그림을 다시 쓰며, 그림에 ImageMagick(`magick`)이 필요하고 `--no-render` 면 그림 없이 점검만 합니다. 다시 쓴 절의 숫자가 하나라도 정본 값이 아니면 아무것도 쓰지 않습니다. 같은 실행의 2단계(2026-09-16)는 제2장 5절 연구 방법(표 4·5·6, 소제목 1)~6), 목차)과 제3장 2절 " 4) 집계 기준의 변경과 이전 결과와의 관계"(표 12-1·12-2)를 추적 파일 11종(`hwpx_methods_bridge.MethodsPaths`)의 숫자로 만들어 붙이며, 기존 정본 파일이 있으면 `--force` 가 있어야 하고 그때 기존 파일은 `<이름>.<sha16>.bak` 로 남깁니다. 쪽 단위 등급 수(2,492쪽 중 등급 3 143쪽)는 `occurrence_real_pages_impact.json` 의 `pages.real_page_grades` 에서 옵니다. 3단계(2026-09-17)는 제3장 2절에 " 5) 교재별 집중과 편차"(표 12-3·12-4)를 더하고 소결을 " 6) 소결" 로 바꿉니다(2단계만 있던 2026-09-16 정본에서는 5)) — 교재별 수치는 정본 `semantic_summary.json` 의 `corpora.*.books[]` 에서 파생합니다(안전관리 전용 2권이 NCS 등급 3 의 38.6%, 등급 3 0건 교재 57권). 손댄 문단(표 셀 포함)의 옛 줄 배치 캐시(`hp:linesegarray`)는 지우고 씁니다 — 한글은 다시 배치하지만 캐시를 믿는 뷰어(Polaris Office)는 긴 새 글을 한 줄에 눌러 그렸습니다(2026-09-17 확인). 캐시 없는 문단을 그리지 못하는 뷰어가 있으면 `--keep-line-layout-cache` 로 캐시를 남긴 채 다시 만들 수 있습니다.

원본 PDF 까지 있으면 **재세그먼트**(`resegment.py`)도 돌릴 수 있습니다 — 이전 기준(페이지 단위)의 정본이며, 2026-09-13 부터 대시보드 KPI 는 위 출현건수 기준이고 이 값은 병기됩니다. 2026-04 검색 당시 워크북의 '페이지' 라벨은 목차 단위라 여러 쪽을 한 라벨로 묶은 경우가 많았는데, 이 스크립트는 마크다운 줄을 PDF 쪽 텍스트에 정렬해 검출 행 7,769건을 실제 쪽에 다시 놓고 (교재, 쪽) 단위 등급을 다시 셉니다. 결과는 검출 1,847→2,189쪽, 등급3 108쪽(5.8%)→145쪽(6.6%)(2026-09-06 마커 결손 보정 후)이며 `docs/03-analysis/data/ncs_pages_reseg.csv`·`reseg_summary.json` 으로 커밋돼 있습니다. 2026-09-06~09-12 의 대시보드 KPI 는 이 산출물이었고, 지금은 "이전 기준"으로 병기됩니다([재세그먼트 결과](docs/03-analysis/resegment-results.analysis.md) §6).

```bash
pip install pymupdf openpyxl
export NCS_PDF_ROOT=/path/to/ncs/pdfs   # 원본 PDF (비공개)
python3 resegment.py                    # 약 30초. 내장 EXPECTED 회귀 검사가 어긋나면 산출물을 쓰지 않는다
```

### 등급이 뜻하는 것

| 등급 | 뜻 |
|:---:|---|
| 등급1 | 미흡·없음 — 안전 키워드 5건 이하 |
| 등급2 | 형식적 언급 — 키워드는 많지만 구체적 조치 없음 |
| 등급3 | 구체적 대책 — 안전 조치·대책을 실제로 제시 |

등급 판정 자체는 **페이지 속성**입니다. 페이지 품질을 비교할 때는 고유 페이지로 세어야 하며, 의미 출현 빈도를 비교하는 현재 NCS·교과서 대시보드는 각 출현에 해당 페이지 등급을 붙인 뒤 **출현건수**로 분포를 세어야 합니다. 두 분모를 혼용하면 안 됩니다. 또한 **한 페이지의 행끼리 등급이 갈리면 가장 낮은 등급을 택합니다**. 다수결은 같은 오판이 여러 행에 복제된 경우를 방어하지 못합니다.

판정 근거와 데이터 계보는 `docs/03-analysis/grade-recount.analysis.md`에 정리돼 있습니다.

## 테스트

프레임워크는 없습니다. 자체 하니스 5종이고 Node·Python 표준 라이브러리만 씁니다. 전부 exit 0/1 을 내며 **push·PR 마다 CI 에서 돕니다**(`.github/workflows/test.yml`).

```bash
node    outputs/test-search-equivalence.js   # 24 — 검색 동치성 + 청크 렌더 + 지연 캐시
node    outputs/test-dashboard-data.js       # 84 — 정본 요약(semantic_summary.json) ↔ data.js ↔ 대시보드·분리 분석·README·CLAUDE.md 교차검증, 이전 기준(reseg) 계보
python3 outputs/test-recount-grades.py       # 390 — 재집계·재채점·페이지 마커·절단 판정·재코딩(코더 호출·채점)·재세그먼트
node    outputs/run-core-logic-tests.js       # 32 — 제목 판정·정규화 (헤드리스)
node    outputs/test-sri.js                  # 38 — 외부 스크립트 SRI (--online 이면 CDN 대조)
```

Node 기반 하니스는 HTML과 실제 공통 렌더러를 `vm` + DOM mock으로 불러옵니다. 복사해 붙인 사본을 테스트하지 않습니다. `test-core-logic.html` 은 브라우저에서 열어 탭 제목으로 봐도 됩니다 — `run-core-logic-tests.js` 는 같은 HTML 을 헤드리스로 돌릴 뿐입니다. `test-recount-grades.py`는 `openpyxl`을 스텁으로 주입해 pip 패키지 없이도, 원본 엑셀 없이도 돕니다.

의미 재검산 자체(코퍼스 규칙, `EXPECTED` 가드, manifest, 결정론, 산출물 writer)는 `test_semantic_keyword_recount.py` 가 검증합니다 — `python3 -m unittest test_semantic_keyword_recount`, 이것만은 `openpyxl` 이 깔린 Python 이 필요합니다. 표현 점검(`expression_review.py` — 표본·정밀도 구간·재정·영향표)은 `test_expression_review.py` 가 검증하며 같은 조건입니다. 보고서 HWPX 재작성(`hwpx_results_refresh.py`)은 `test_hwpx_results_refresh.py` 가 fixture HWPX 로 검증하고(표준 라이브러리만; 그림 렌더는 ImageMagick 이 있을 때만), 2단계(제2장 5절·제3장 2절 4), `hwpx_methods_bridge.py`)는 `test_hwpx_methods_bridge.py` 가 검증합니다(역시 표준 라이브러리만). CI 는 위 하니스 5종 뒤에 `openpyxl` 을 설치하고 넷 다 돌립니다.

대시보드 데이터는 `semantic_keyword_recount.py` 한 실행이 `docs/semantic_recount_data.js` 와 `docs/03-analysis/data/semantic_summary.json` 에 같은 JSON 으로 씁니다. `test-dashboard-data.js` 는 그 요약 파일을 기준으로 대시보드·분리 분석 페이지·README·`CLAUDE.md` 의 인용값을 대조하므로(S2~S8), 수치는 손으로 고치지 말고 정본 실행을 다시 돌리세요. 위 블록의 단언 수 두 개(`test-dashboard-data.js`, `test-recount-grades.py`)는 하니스가 README·`CLAUDE.md` 의 인용값과 직접 대조하므로(S9, R17), 하니스가 찍는 수를 두 파일에 옮기세요.

## 저장소 구성

```
outputs/markdown-search-app.html   검색 앱 (HTML+CSS+JS 단일 파일, ~2,040줄)
outputs/server.py                  개발 서버 (표준 라이브러리만, LM Studio 프록시 포함)
recount_grades.py                  원본 엑셀 → 등급 재집계 → CSV/JSON
regrade.py                         페이지 본문에서 등급 재채점 (검증용, 미발표)
semantic_keyword_recount.py        30개 키워드 의미 단위 재검산 + 출현별 등급 결합 → xlsx·보고서·대시보드 데이터·semantic_summary.json·분리 분석 HTML (발표 정본, 2026-09-13 부터; EXPECTED 가드)
shift_page_markers.py              <!-- page: N --> 마커 값 일괄 이동 (0-based 로 변환된 파일을 1-based 로)
expression_review.py               의미 표현 사전 도메인 점검 — 표본·코더 채점(정밀도 CP 구간·κ)·사전 v1/v1fix/v2 영향표 (연구용, 미발표)
hwpx_results_refresh.py            기초보고서 HWPX 제3장 1~3절(교과서·NCS·사고사례)의 문단·표 7개·그림 3개를 정본 수치로 재작성 (숫자 감사 통과 시에만 새 파일 출력)
occurrence_real_pages_impact.py    블록 기준(2026-09-14) vs 실제 쪽 기준(2026-09-15) 등급 이동 영향표 (연구용, 계보 검증)
resegment.py                       워크북 페이지 라벨을 원본 PDF 실제 쪽으로 재배치해 등급 재집계 (NCS 쪽 단위 — 이전 기준의 정본, 병기용)
make_coding_sheet.py, code_pages.py, score_coding.py  코딩 표본 생성 · AI 코더 항목별 호출 · 교차 판정 채점
truncation_audit.py                엑셀 셀 한도 절단 전수 실측 (pip 불필요)
*_downloader.py                    OSHA·KOSHA·NIOSH·EU-OSHA·SafeWork AU 발간물 수집기
page_utils.py 외                   PDF→마크다운→Excel 페이지 매핑 유틸
docs/                              대시보드 3종 + 분석 문서 (GitHub Pages)
docs/03-analysis/data/             정본 요약 semantic_summary.json + 재집계 산출물 (CSV, summary.json) + 재채점·재코딩·재세그먼트 수치 (regrade_impact.json, recoding_scores*.json, ncs_pages_reseg.csv, reseg_summary.json)
data_source/ (비추적)               원본 마크다운·이미지·PDF — 연구책임자 지정 정본 소스. data/markdown/ 은 복사본
docs/03-analysis/data/README.md    산출물 계보 — 어느 파일이 발표 정본이고 어느 것이 계보 확인용인지
```

다운로더는 저장 위치를 환경변수로 받습니다:

```bash
export DOWNLOAD_ROOT="/path/to/안전보건공단"
python3 osha_downloader.py
```

미설정 시 저장소 안 `downloads/`(gitignore)로 받습니다. `requests`와 `beautifulsoup4`가 필요하고 `requirements.txt`는 없습니다. 기관별 저장 위치·수집 범위·중단 후 재개는 [발간물 수집 how-to](docs/howto-download-publications.md)에 있습니다.

## 문서

| 문서 | 종류 | 내용 |
|---|---|---|
| [첫 검색 튜토리얼](docs/tutorial-first-search.md) | 튜토리얼 | 샘플 문서로 검색 → 내보내기까지 처음부터 끝까지 |
| [발간물 수집 how-to](docs/howto-download-publications.md) | How-to | OSHA·KOSHA·NIOSH·EU-OSHA·SafeWork AU 발간물 대량 수집 |
| [페이지 마커 주입 how-to](docs/howto-page-markers.md) | How-to | 검색 결과의 줄 번호를 실제 PDF 쪽수로 바꾸기 · 0-based 로 심긴 마커를 `shift_page_markers.py` 로 옮기기 |
| [등급 재집계 분석](docs/03-analysis/grade-recount.analysis.md) | 설명 | 등급 체계를 왜 이렇게 통일했는지, 페이지 단위 집계가 왜 필요한지 |
| [재코딩 결과 분석](docs/03-analysis/recoding-results.analysis.md) | 설명 | 538쪽 AI 재코딩으로 잰 현행 규칙의 정밀도·재현율, 어느 변형도 채택하지 않은 이유 |
| [어휘 누락 탐색](docs/03-analysis/vocab-search.analysis.md) | 설명 | 규칙 사전에 빠진 안전어·조치어 21종과 그것이 등급3 비율에 미치는 영향 |
| [표현 점검 결과](docs/03-analysis/expression-review.analysis.md) | 설명 | 의미 재검산 사전의 확장 표현 22개를 AI 코더 2계열로 점검한 정밀도(CP 95% 구간)·κ 0.965, 사전 v2 를 고른 근거와 v1/v1fix/v2 영향표; §8 이 재현 순서 |
| [재세그먼트 결과](docs/03-analysis/resegment-results.analysis.md) | 설명 | 워크북 페이지 라벨을 원본 PDF 실제 쪽으로 풀면 검출 쪽수·등급3 비율이 어떻게 바뀌는지(1,847→2,189쪽, 5.8→6.6%); 대시보드는 2026-09-06~09-12 이 수치를 발표했고 지금은 이전 기준으로 병기 |
| [`CLAUDE.md`](CLAUDE.md) | 레퍼런스 | 아키텍처, 페이지 매핑 알고리즘, 제목 판정 규칙, 디자인 토큰 |
| `키워드기반_문서분류분석_방법론.hwpx` | 설명 | 방법론 원본 — 6단계 파이프라인과 위치 정합 알고리즘 |

## 알려진 한계

- 부분 문자열 일치라 동의어·표기 변형을 놓칩니다. 반도체 문맥의 동음이의(장비 진동, 파티클 먼지)도 걸러지지 않습니다. `regrade.py` 에 단어 경계 보정이 들어 있지만 발표 수치에는 적용하지 않았습니다.
- 원본 채점 규칙에 확인된 결함이 둘 있습니다 — 단어 경계 없는 부분 문자열 매칭, 그리고 페이지 길이와 무관한 고정 임계. 결함별 영향도는 `docs/03-analysis/data/regrade_impact.json` 에 있고, `recount_grades.py` 는 보수적 규칙으로 우회할 뿐 원본을 고치지 않습니다. 이전 판에 적혀 있던 "총계/내역 불일치 버그" 는 **철회합니다** — 불일치 171건 중 168건은 등급사유 문자열이 상위 5개만 보여주는 표시 절단이었고, 실제로 어긋난 것은 3쪽(0.16%)뿐입니다.
- 사람 코딩 검증이 아직 없습니다. 69쪽 이중코딩은 코딩 시트가 판정 규칙의 가정을 두 코더 모두에게 흘려 **라벨을 무효 처리**했고, 2026-09-04 에 538쪽을 새로 뽑아 AI 코더 세 명(Claude `claude-opus-5`, OpenAI `gpt-5.6-sol` ×2)이 다시 코딩했습니다. 그 결과 현행 규칙은 **정밀도 80~84%, 재현율 13~21%** 이고, 코더 기준 진짜 등급3은 22~37% 입니다([재코딩 결과 분석](docs/03-analysis/recoding-results.analysis.md)). AI 두 계열의 일치는 사람 이중코딩이 아니며, 어느 변형도 채택하지 않았습니다.
- **NCS 의 '페이지'는 실제 쪽이 아니라 목차 단위 블록인 경우가 많습니다.** 2026-04 검색 당시 마크다운의 페이지 마커가 목차에서 유도된 것이라, 워크북 페이지 라벨 하나가 실제 10~58쪽을 묶기도 합니다. 엑셀 셀 한도(32,767자)에 닿은 라벨 16개는 그 증상이며, 이전 판의 "16쪽이 잘려 있어 등급3 은 108~112쪽 구간" 이라는 해석은 **철회합니다**(외부감사 C1, 2026-09-04). `resegment.py` 로 검출 행을 원본 PDF 실제 쪽에 다시 놓으면 검출 1,847→2,189쪽, 등급3 108쪽(5.8%)→145쪽(6.6%)이고, 정렬 오차는 ±1쪽 수준입니다. 이 실제 쪽 기준 값은 2026-09-13 부터 "이전 기준"으로 병기되고, 공식 KPI 는 출현건수 기준입니다([재세그먼트 결과](docs/03-analysis/resegment-results.analysis.md)).
- 라벨 블록의 극단 사례가 `반도체 장비 안전관리` 입니다. 라벨 기준으로는 검출 페이지가 p.46 과 p.136~154 의 20쪽뿐이라 p.47~135 가 통째로 빈 것처럼 보이지만, 실제로는 그 20개 라벨이 136쪽을 묶은 블록이었습니다(라벨 p.154 한 칸의 273행이 실제 58쪽에 흩어집니다). 재세그먼트 후 등급3 145쪽 중 42쪽이 이 한 권에서 나옵니다. 라벨 기준 수치(1,847쪽·등급3 108쪽)는 이 때문에 더 이상 발표하지 않습니다.

그래서 21.7%(이전 기준 6.6%)는 이렇게까지만 읽어야 합니다 — **결함이 확인된 현행 규칙의 출력값이며(출현건수 기준도 같은 페이지 등급을 물려받습니다), 두 계열의 AI 코더 기준 재현율이 13~21%(진짜 등급3 22~37%)라 참값의 상한으로 해석할 수 없습니다. 사람 코딩은 아직 없습니다.**

남은 과제는 `TODOS.md`에 있습니다.

## 개발

에이전트로 작업할 때의 지침은 `CLAUDE.md`에 있습니다 — 아키텍처, 페이지 매핑 알고리즘, 제목 판정 규칙, 등급체계, 테스트 커버리지 기준.
