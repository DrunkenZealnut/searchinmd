# SearchInMD — 마크다운 키워드 검색기

마크다운 문헌 더미에서 키워드를 찾아 Excel로 떨어뜨리는 브라우저 도구, 그리고 그 결과로 만든 안전보건 분석 대시보드.

청년노동자인권센터의 2026년 교과서 기초연구에서, NCS 반도체 교재 86권과 반도체 특성화고 교과서 9권이 안전보건을 어떻게 다루는지 조사하려고 만들었습니다.

## 대시보드 (GitHub Pages)

| 페이지 | 내용 |
|---|---|
| [NCS 교재 86권](https://drunkenzealnut.github.io/searchinmd/) | 검출 1,847쪽의 등급 분포, 영역별 현황, 사고사례 원문 대조 |
| [반도체고 교과서 9권](https://drunkenzealnut.github.io/searchinmd/textbook.html) | 검출 362쪽·전체 2,055쪽 두 분모를 병기, NCS 대비 비교는 검출쪽 기준 |
| [OSHA 안전교육](https://drunkenzealnut.github.io/searchinmd/osha.html) | 미국 OSHA 반도체 화학물질 안전교육 과정과의 비교 |

핵심 수치 하나만 옮기면 — **구체적 안전대책이 담긴 페이지 비율은 NCS 5.8%, 교과서 2.2%** 입니다(둘 다 키워드 검출 페이지 분모: 108/1,847 과 8/362).

교과서는 전체 쪽수를 알기에 다른 각도로도 볼 수 있습니다 — **9권 2,055쪽 중 구체적 대책은 8쪽(0.39%)** 이고, 그중 6권은 0쪽입니다. NCS 는 교재 원본 총 쪽수를 모르므로 같은 계산을 할 수 없습니다. 분모가 다른 두 값을 나란히 빼면 안 됩니다.

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

대시보드 수치는 손으로 넣지 않았습니다. 원본 엑셀에서 스크립트로 뽑습니다.

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

### 등급이 뜻하는 것

| 등급 | 뜻 |
|:---:|---|
| 1 | 미흡·없음 — 안전 키워드 5건 이하 |
| 2 | 형식적 언급 — 키워드는 많지만 구체적 조치 없음 |
| 3 | 구체적 대책 — 안전 조치·대책을 실제로 제시 |

두 가지가 함정입니다. **등급은 페이지 속성이지 키워드 히트 속성이 아닙니다** — 행으로 세면 키워드가 여럿 걸린 페이지가 중복 계수돼 상위 등급이 부풀려집니다(NCS 등급3은 2,228 히트지만 108쪽). 그리고 **한 페이지의 행끼리 등급이 갈리면 가장 낮은 등급을 택합니다** — 다수결은 원본 채점 버그가 같은 오판을 여러 행에 남긴 경우 그 중복 수가 표가 돼 버립니다.

판정 근거와 데이터 계보는 `docs/03-analysis/grade-recount.analysis.md`에 정리돼 있습니다.

## 테스트

프레임워크는 없습니다. 자체 하니스 5종이고 Node·Python 표준 라이브러리만 씁니다. 전부 exit 0/1 을 내며 **push·PR 마다 CI 에서 돕니다**(`.github/workflows/test.yml`).

```bash
node    outputs/test-search-equivalence.js   # 24 — 검색 동치성 + 청크 렌더 + 지연 캐시
node    outputs/test-dashboard-data.js       # 122 — 대시보드 데이터·표 렌더·정렬
python3 outputs/test-recount-grades.py       # 364 — 재집계·재채점·페이지 마커·절단 판정·재코딩(코더 호출·채점)
node    outputs/run-core-logic-tests.js       # 32 — 제목 판정·정규화 (헤드리스)
node    outputs/test-sri.js                  # 38 — 외부 스크립트 SRI (--online 이면 CDN 대조)
```

Node 기반 하니스 세 개는 HTML 안의 실제 `<script>` 블록을 `vm` + DOM mock으로 불러옵니다. 복사해 붙인 사본을 테스트하지 않습니다. `test-core-logic.html` 은 브라우저에서 열어 탭 제목으로 봐도 됩니다 — `run-core-logic-tests.js` 는 같은 HTML 을 헤드리스로 돌릴 뿐입니다. `test-recount-grades.py`는 `openpyxl`을 스텁으로 주입해 pip 패키지 없이도, 원본 엑셀 없이도 돕니다.

대시보드의 하드코딩 데이터 배열은 **자기 자신이 아니라 `summary.json`에 대조**합니다.

## 저장소 구성

```
outputs/markdown-search-app.html   검색 앱 (HTML+CSS+JS 단일 파일, ~2,040줄)
outputs/server.py                  개발 서버 (표준 라이브러리만, LM Studio 프록시 포함)
recount_grades.py                  원본 엑셀 → 등급 재집계 → CSV/JSON
regrade.py                         페이지 본문에서 등급 재채점 (검증용, 미발표)
make_coding_sheet.py, code_pages.py, score_coding.py  코딩 표본 생성 · AI 코더 항목별 호출 · 교차 판정 채점
truncation_audit.py                엑셀 셀 한도 절단 전수 실측 (pip 불필요)
*_downloader.py                    OSHA·KOSHA·NIOSH·EU-OSHA·SafeWork AU 발간물 수집기
page_utils.py 외                   PDF→마크다운→Excel 페이지 매핑 유틸
docs/                              대시보드 3종 + 분석 문서 (GitHub Pages)
docs/03-analysis/data/             재집계 산출물 (CSV, summary.json) + 재채점·재코딩 수치 (regrade_impact.json, recoding_scores*.json)
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
| [페이지 마커 주입 how-to](docs/howto-page-markers.md) | How-to | 검색 결과의 줄 번호를 실제 PDF 쪽수로 바꾸기 |
| [등급 재집계 분석](docs/03-analysis/grade-recount.analysis.md) | 설명 | 등급 체계를 왜 이렇게 통일했는지, 페이지 단위 집계가 왜 필요한지 |
| [재코딩 결과 분석](docs/03-analysis/recoding-results.analysis.md) | 설명 | 538쪽 AI 재코딩으로 잰 현행 규칙의 정밀도·재현율, 어느 변형도 채택하지 않은 이유 |
| [어휘 누락 탐색](docs/03-analysis/vocab-search.analysis.md) | 설명 | 규칙 사전에 빠진 안전어·조치어 21종과 그것이 등급3 비율에 미치는 영향 |
| [`CLAUDE.md`](CLAUDE.md) | 레퍼런스 | 아키텍처, 페이지 매핑 알고리즘, 제목 판정 규칙, 디자인 토큰 |
| `키워드기반_문서분류분석_방법론.hwpx` | 설명 | 방법론 원본 — 6단계 파이프라인과 위치 정합 알고리즘 |

## 알려진 한계

- 부분 문자열 일치라 동의어·표기 변형을 놓칩니다. 반도체 문맥의 동음이의(장비 진동, 파티클 먼지)도 걸러지지 않습니다. `regrade.py` 에 단어 경계 보정이 들어 있지만 발표 수치에는 적용하지 않았습니다.
- 원본 채점 규칙에 확인된 결함이 둘 있습니다 — 단어 경계 없는 부분 문자열 매칭, 그리고 페이지 길이와 무관한 고정 임계. 결함별 영향도는 `docs/03-analysis/data/regrade_impact.json` 에 있고, `recount_grades.py` 는 보수적 규칙으로 우회할 뿐 원본을 고치지 않습니다. 이전 판에 적혀 있던 "총계/내역 불일치 버그" 는 **철회합니다** — 불일치 171건 중 168건은 등급사유 문자열이 상위 5개만 보여주는 표시 절단이었고, 실제로 어긋난 것은 3쪽(0.16%)뿐입니다.
- 사람 코딩 검증이 아직 없습니다. 69쪽 이중코딩은 코딩 시트가 판정 규칙의 가정을 두 코더 모두에게 흘려 **라벨을 무효 처리**했고, 2026-09-04 에 538쪽을 새로 뽑아 AI 코더 세 명(Claude `claude-opus-5`, OpenAI `gpt-5.6-sol` ×2)이 다시 코딩했습니다. 그 결과 현행 규칙은 **정밀도 80~84%, 재현율 13~21%** 이고, 코더 기준 진짜 등급3은 22~37% 입니다([재코딩 결과 분석](docs/03-analysis/recoding-results.analysis.md)). AI 두 계열의 일치는 사람 이중코딩이 아니며, 어느 변형도 채택하지 않았습니다.
- NCS 16쪽은 원본 엑셀의 셀 한도(32,767자)에서 본문이 잘려 있고, 원본이 그 엑셀뿐이라 **복구할 수 없습니다.** 등급별로 고르지 않습니다 — 등급1 은 1,270쪽 중 0쪽, 등급3 은 108쪽 중 12쪽(11.1%)입니다. 텍스트가 지워지면 등급은 내려가는 방향으로만 움직이므로 등급3 은 108~112쪽(5.8~6.1%) 구간에 있습니다. 교과서 쪽은 0쪽입니다.
- 일부 교재에 마크다운 변환·페이지 매핑 결손이 있습니다. `반도체 장비 안전관리` 는 검출 페이지가 p.46 과 p.136~154 20쪽뿐이고 p.47~135 가 통째로 비어 있습니다. 등급3 108쪽과 사고사례 판정의 신뢰도에 영향을 줍니다.

그래서 5.8% 는 이렇게까지만 읽어야 합니다 — **결함이 확인된 현행 규칙의 출력값이며, 두 계열의 AI 코더 기준 재현율이 13~21%(진짜 등급3 22~37%)라 참값의 상한으로 해석할 수 없습니다. 사람 코딩은 아직 없습니다.**

남은 과제는 `TODOS.md`에 있습니다.

## 개발

에이전트로 작업할 때의 지침은 `CLAUDE.md`에 있습니다 — 아키텍처, 페이지 매핑 알고리즘, 제목 판정 규칙, 등급체계, 테스트 커버리지 기준.
