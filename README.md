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

### 등급이 뜻하는 것

| 등급 | 뜻 |
|:---:|---|
| 1 | 미흡·없음 — 안전 키워드 5건 이하 |
| 2 | 형식적 언급 — 키워드는 많지만 구체적 조치 없음 |
| 3 | 구체적 대책 — 안전 조치·대책을 실제로 제시 |

두 가지가 함정입니다. **등급은 페이지 속성이지 키워드 히트 속성이 아닙니다** — 행으로 세면 키워드가 여럿 걸린 페이지가 중복 계수돼 상위 등급이 부풀려집니다(NCS 등급3은 2,228 히트지만 108쪽). 그리고 **한 페이지의 행끼리 등급이 갈리면 가장 낮은 등급을 택합니다** — 다수결은 원본 채점 버그가 같은 오판을 여러 행에 남긴 경우 그 중복 수가 표가 돼 버립니다.

판정 근거와 데이터 계보는 `docs/03-analysis/grade-recount.analysis.md`에 정리돼 있습니다.

## 테스트

프레임워크는 없습니다. 자체 하니스 4종이고 Node·Python 표준 라이브러리만 씁니다. 전부 exit 0/1 을 내며 **push·PR 마다 CI 에서 돕니다**(`.github/workflows/test.yml`).

```bash
node    outputs/test-search-equivalence.js   # 24 — 검색 동치성 + 청크 렌더 + 지연 캐시
node    outputs/test-dashboard-data.js       # 92 — 대시보드 데이터·표 렌더·정렬
python3 outputs/test-recount-grades.py       # 87 — recount_grades.py 로직
node    outputs/run-core-logic-tests.js       # 32 — 제목 판정·정규화 (헤드리스)
```

Node 기반 하니스 세 개는 HTML 안의 실제 `<script>` 블록을 `vm` + DOM mock으로 불러옵니다. 복사해 붙인 사본을 테스트하지 않습니다. `test-core-logic.html` 은 브라우저에서 열어 탭 제목으로 봐도 됩니다 — `run-core-logic-tests.js` 는 같은 HTML 을 헤드리스로 돌릴 뿐입니다. `test-recount-grades.py`는 `openpyxl`을 스텁으로 주입해 pip 패키지 없이도, 원본 엑셀 없이도 돕니다.

대시보드의 하드코딩 데이터 배열은 **자기 자신이 아니라 `summary.json`에 대조**합니다.

## 저장소 구성

```
outputs/markdown-search-app.html   검색 앱 (HTML+CSS+JS 단일 파일, ~2,040줄)
outputs/server.py                  개발 서버 (표준 라이브러리만, LM Studio 프록시 포함)
recount_grades.py                  원본 엑셀 → 등급 재집계 → CSV/JSON
*_downloader.py                    OSHA·KOSHA·NIOSH·EU-OSHA·SafeWork AU 발간물 수집기
page_utils.py 외                   PDF→마크다운→Excel 페이지 매핑 유틸
docs/                              대시보드 3종 + 분석 문서 (GitHub Pages)
docs/03-analysis/data/             재집계 산출물 (CSV, summary.json)
```

다운로더는 저장 위치를 환경변수로 받습니다:

```bash
export DOWNLOAD_ROOT="/path/to/안전보건공단"
python3 osha_downloader.py
```

미설정 시 저장소 안 `downloads/`(gitignore)로 받습니다. `requests`와 `beautifulsoup4`가 필요하고 `requirements.txt`는 없습니다.

## 알려진 한계

- 부분 문자열 일치라 동의어·표기 변형을 놓칩니다. 반도체 문맥의 동음이의(장비 진동, 파티클 먼지)도 걸러지지 않습니다.
- 원본 채점 알고리즘에 총계/내역 불일치 버그가 있습니다. `recount_grades.py`는 보수적 규칙으로 우회할 뿐 원본을 고치지 않습니다.
- 분류 정확도 검증(이중 코딩, precision/recall)이 아직 없습니다.
- 일부 교재에 마크다운 변환·페이지 매핑 결손이 있습니다. `반도체 장비 안전관리` 는 검출 페이지가 p.46 과 p.136~154 20쪽뿐이고 p.47~135 가 통째로 비어 있습니다. 등급3 108쪽과 사고사례 판정의 신뢰도에 영향을 줍니다.

남은 과제는 `TODOS.md`에 있습니다.

## 개발

에이전트로 작업할 때의 지침은 `CLAUDE.md`에 있습니다 — 아키텍처, 페이지 매핑 알고리즘, 제목 판정 규칙, 등급체계, 테스트 커버리지 기준.
