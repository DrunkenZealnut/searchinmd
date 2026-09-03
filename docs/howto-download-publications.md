# How to 기관 발간물 대량 수집하기

산업안전보건 기관 5곳의 발간물 PDF를 받습니다. 받은 PDF를 마크다운으로 바꾸면 [검색 앱](tutorial-first-search.md)의 입력이 됩니다.

수집기는 검색 앱과 별개로 도는 오프라인 스크립트입니다. 웹 앱은 이 스크립트를 호출하지 않습니다.

## 준비

수집기는 pip 패키지 두 개가 필요합니다. 저장소에 `requirements.txt` 는 없습니다.

```bash
pip install requests beautifulsoup4
```

저장 위치를 정합니다. **정하지 않으면 저장소 안 `downloads/` 로 받습니다**(`.gitignore` 대상이라 커밋되지는 않습니다).

```bash
export DOWNLOAD_ROOT="/path/to/안전보건공단"
```

한 번만 설정하면 5개 스크립트가 각자 자기 하위 폴더를 만들어 씁니다. 셸을 새로 열 때마다 다시 설정해야 하니, 계속 쓸 거면 `~/.zshrc` 에 넣으세요.

## 수집기 고르기

| 스크립트 | 기관 | `DOWNLOAD_ROOT` 아래 저장 폴더 |
|---|---|---|
| `osha_downloader.py` | 미국 OSHA | `OSHA_Publications` |
| `kosha_downloader.py` | 한국 산업안전보건연구원 | `연구보고서` |
| `niosh_downloader.py` | 미국 NIOSH (CDC) | `NIOSH_Publications` |
| `eu_osha_downloader.py` | 유럽 EU-OSHA | `EU-OSHA_Publications` |
| `safework_au_downloader.py` | 호주 SafeWork | `SafeWork_AU` |

## 실행

인자는 없습니다. 그냥 돌립니다.

```bash
python3 osha_downloader.py
```

스크립트가 목록 페이지를 훑고, 각 항목의 PDF 링크를 찾아 내려받습니다. 요청 사이에 딜레이를 넣어 상대 서버를 두드리지 않습니다.

## 수집 범위 조절

범위는 명령행 옵션이 아니라 **파일 위쪽 상수**로 정합니다. 바꾸려면 파일을 직접 편집하세요.

| 상수 | 뜻 | 값이 있는 스크립트 |
|---|---|---|
| `MIN_YEAR` | 이 연도 이후 발간물만 | OSHA `2020` · NIOSH `2000` · EU-OSHA `2000` |
| `TOTAL_PAGES` | 훑을 목록 페이지 수 | OSHA `26` · EU-OSHA `334` · SafeWork AU `105` |
| `ARTICLE_LIMIT` | 목록 페이지당 항목 수 | KOSHA `100` |
| `DELAY` | 요청 간 대기 초 | OSHA·KOSHA·SafeWork AU `1.0` · NIOSH `0.8` |

`eu_osha_downloader.py` 만 `DELAY` 상수가 없습니다. `time.sleep(2)` 를 코드에 직접 박아 쓰고, 실패 시 `3 * (시도횟수)` 초로 물러납니다. 이 스크립트의 속도를 바꾸려면 상수가 아니라 해당 `sleep` 호출을 고쳐야 합니다.

먼저 작게 확인하고 싶으면 `TOTAL_PAGES` 를 `1` 로 낮춰 한 페이지만 받아 보세요.

## 중단하고 다시 시작하기

Ctrl+C로 끊어도 받아둔 PDF는 남고, 다시 실행하면 이어서 받습니다. 다만 **어느 단계에서 끊었는지에 따라 다시 하는 양이 다릅니다.**

수집기는 두 단계로 돕니다 — 먼저 목록 페이지를 전부 훑어 항목 목록을 만들고(1단계), 그 다음 PDF를 하나씩 받습니다(2단계).
**항목 목록은 1단계가 끝난 뒤에 한 번만 저장됩니다.** 1단계 도중에 끊으면 목록이 저장되지 않아 다음 실행이 목록 수집부터 다시 합니다(PDF는 안 받았으니 잃는 건 목록 훑는 시간뿐입니다). 2단계 도중에 끊으면 목록은 그대로 재사용하고 안 받은 PDF부터 이어갑니다.

2단계 재개는 두 갈래로 동작합니다.

1. **파일이 이미 디스크에 있으면 건너뜁니다.** 콘솔에 `[12/340] 이미 존재: <파일명>` 으로 찍힙니다.
2. **진행 상황이 JSON에 남습니다.** `$DOWNLOAD_ROOT/<저장폴더>/_download_progress.json`

```json
{
  "downloaded": ["...받은 항목..."],
  "failed": ["...실패한 항목..."],
  "articles": ["...목록에서 찾은 항목..."]
}
```

처음부터 다시 받고 싶으면 저장 폴더를 통째로 지우거나, `_download_progress.json` 과 받아둔 PDF를 함께 지우세요. **JSON만 지우면 안 됩니다** — 파일이 남아 있는 한 1번 규칙이 계속 건너뜁니다.

## 확인

```bash
# 받은 개수 (-iname 이어야 합니다 — 기관에 따라 .PDF 대문자로 내려옵니다)
find "$DOWNLOAD_ROOT/OSHA_Publications" -iname '*.pdf' | wc -l

# 실패 목록
python3 -c "
import json, os
p = os.path.join(os.environ['DOWNLOAD_ROOT'], 'OSHA_Publications', '_download_progress.json')
d = json.load(open(p, encoding='utf-8'))
print('받음:', len(d['downloaded']), '/ 실패:', len(d['failed']), '/ 목록:', len(d['articles']))
for f in d['failed'][:10]:
    print('  실패:', f)
"
```

실패 항목은 자동으로 재시도되지 않습니다. 다시 받으려면 그 항목의 PDF가 없는 상태에서 스크립트를 한 번 더 돌리세요 — 1번 규칙이 건너뛰지 않으므로 다시 시도합니다.

## 다음 단계

받은 PDF를 마크다운으로 변환한 뒤(변환기는 이 저장소에 없습니다), `_meta.json` 이 함께 나온다면 [페이지 마커를 주입](howto-page-markers.md)하세요. 그래야 검색 결과에 줄 번호 대신 실제 PDF 쪽수가 붙습니다.

그 다음은 [검색 튜토리얼](tutorial-first-search.md) 흐름 그대로입니다.

## 막혔을 때

**`ModuleNotFoundError: No module named 'requests'`**
`pip install requests beautifulsoup4` 를 하지 않았습니다.

**저장소 안에 `downloads/` 가 생겼다**
`DOWNLOAD_ROOT` 를 설정하지 않은 채 돌렸습니다. `.gitignore` 대상이라 커밋되지는 않습니다. 옮기려면 폴더째 원하는 위치로 이동한 뒤 `DOWNLOAD_ROOT` 를 그쪽으로 잡으세요.

**받은 게 0개다**
기관이 사이트 구조를 바꾸면 파싱이 조용히 빈 목록을 냅니다. `_download_progress.json` 의 `articles` 가 비어 있으면 목록 파싱 단계에서 실패한 것입니다. 스크립트의 `BASE_URL` / `LIST_URL` 을 브라우저로 열어 페이지가 아직 그 모양인지 확인하세요.

**중간에 계속 실패한다**
`DELAY` 를 올려 보세요. 기관 서버가 속도 제한을 걸었을 수 있습니다.
