# Design: D2 페이지 마커 자동 삽입 + C2 대시보드 Excel 업로드

> Plan 참조: `docs/01-plan/features/feature-proposals.plan.md` (D2, C2)

## 1. D2: 페이지 마커 자동 삽입 스크립트

### 1.1 배경

| 항목 | 현재 | 목표 |
|------|------|------|
| 마커 있는 .md | 88개 | 전체 |
| 마커 없는 .md | 64개 (52개는 _meta.json 보유) | 0개 (가능한 것 모두 삽입) |
| 페이지 매핑 방식 | Strategy 2 (TOC DP) fallback | Strategy 1 (`<!-- page: N -->`) 직접 사용 |

### 1.2 구현 설계

**신규 파일**: `insert_page_markers.py`

```
실행: python3 insert_page_markers.py [NCS_DIR] [NCS_DIR2] ...
기본: 두 NCS 디렉토리 모두 처리
```

**알고리즘**:

```
for each .md file without <!-- page: N --> markers:
    1. 같은 폴더에서 _meta.json 찾기
    2. _meta.json 없으면 → skip (로그 출력)
    3. buildPageMapping의 Python 버전으로 heading→page 매핑 생성
       (add_fullpage.py의 build_page_map() 재사용)
    4. 매핑 결과를 기반으로 페이지 전환점에 <!-- page: N --> 삽입
    5. 원본 .md 파일 덮어쓰기 (백업 옵션 제공)
```

**마커 삽입 규칙**:

```python
# page_map: dict[line_number(1-based)] -> page_number(1-based)
# 페이지가 바뀌는 줄 바로 위에 마커 삽입

prev_page = None
output_lines = []
for i, line in enumerate(lines):
    ln = i + 1  # 1-based
    current_page = page_map.get(ln)
    if current_page and current_page != prev_page:
        output_lines.append(f'<!-- page: {current_page} -->')
        prev_page = current_page
    output_lines.append(line)
```

**CLI 옵션**:

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--dry-run` | 변경 없이 처리할 파일 목록만 출력 | false |
| `--backup` | 원본을 `.md.bak`으로 백업 | false |
| `--force` | 이미 마커 있는 파일도 재처리 | false |

**build_page_map 재사용**: `add_fullpage.py`에 이미 구현된 `build_page_map()` 함수를 공통 모듈로 추출하거나 `insert_page_markers.py`에서 import.

### 1.3 데이터 플로우

```
insert_page_markers.py
│
├─ scan NCS directories for .md files
├─ filter: 이미 마커 있는 파일 skip
│
├─ for each .md:
│   ├─ find _meta.json (같은 폴더)
│   ├─ build_page_map(lines, metadata)
│   ├─ insert markers at page transitions
│   └─ write back to .md
│
└─ report: N files processed, M skipped, K errors
```

### 1.4 코드 변경 요약

| # | 변경 | 파일 | 타입 |
|---|------|------|------|
| 1 | `build_page_map()` 공통 모듈 추출 | `page_utils.py` (신규) | 리팩터 |
| 2 | `add_fullpage.py`에서 import | `add_fullpage.py` | 수정 |
| 3 | `insert_page_markers.py` | 신규 | 신규 스크립트 |

---

## 2. C2: 대시보드 Excel 업로드 기능

### 2.1 배경

현재 `docs/index.html` 대시보드는 데이터가 `var KW=[...]` 형태로 하드코딩되어 있어, 새로운 분석 결과가 나올 때마다 HTML을 수정해야 합니다.

### 2.2 구현 설계

**변경 파일**: `docs/index.html`

**핵심 원리**: SheetJS(XLSX.js)를 CDN으로 로드하여 브라우저에서 Excel 파싱 → 기존 차트/테이블을 동적으로 업데이트.

### 2.3 UI 변경

Hero 섹션 아래에 업로드 영역 추가:

```html
<section class="card upload-section">
  <h3>Excel 분석 결과 업로드</h3>
  <p class="ts">ncs_keywords_in_markdown_results 파일을 업로드하면 대시보드가 자동 갱신됩니다</p>
  <div class="upload-area">
    <button class="upload-btn" id="uploadBtn">📊 Excel 파일 선택</button>
    <input type="file" id="excelInput" accept=".xlsx,.xls" hidden>
    <span class="upload-status" id="uploadStatus"></span>
  </div>
</section>
```

### 2.4 Excel 파싱 로직

```javascript
// 지원하는 Excel 구조:
// 각 시트 = 키워드 (안전, 사망, 부상, ...)
// 열: number, 영역, filename, contents, page, 페이지전체내용, 사고사례여부, 등급, 등급사유

function parseExcel(workbook) {
    var result = { keywords: [], areas: {}, total: 0 };
    var areaGrade = {};  // area -> {g1,g2,g3,cases,total}

    workbook.SheetNames.forEach(function(sheetName) {
        var ws = workbook.Sheets[sheetName];
        var rows = XLSX.utils.sheet_to_json(ws);

        var kwStat = { k: sheetName, t: rows.length, g1:0, g2:0, g3:0, cs:0,
                       dev:0, mfg:0, eq:0, mat:0 };

        rows.forEach(function(row) {
            var area = row['영역'] || '';
            var grade = parseInt(row['등급']) || 0;
            var isCase = row['사고사례여부'] === '예';

            // Grade counts
            if (grade === 1) kwStat.g1++;
            else if (grade === 2) kwStat.g2++;
            else if (grade === 3) kwStat.g3++;
            if (isCase) kwStat.cs++;

            // Area mapping
            var areaKey = mapAreaKey(area); // '반도체개발' -> 'dev'
            if (areaKey) kwStat[areaKey]++;

            // Area aggregation
            if (!areaGrade[area]) areaGrade[area] = {total:0,g1:0,g2:0,g3:0,cases:0};
            areaGrade[area].total++;
            if (grade === 1) areaGrade[area].g1++;
            else if (grade === 2) areaGrade[area].g2++;
            else if (grade === 3) areaGrade[area].g3++;
            if (isCase) areaGrade[area].cases++;

            result.total++;
        });

        result.keywords.push(kwStat);
    });

    result.keywords.sort(function(a,b) { return b.t - a.t; });
    result.areas = areaGrade;
    return result;
}

function mapAreaKey(area) {
    if (area.includes('개발')) return 'dev';
    if (area.includes('제조')) return 'mfg';
    if (area.includes('장비')) return 'eq';
    if (area.includes('재료')) return 'mat';
    return null;
}
```

### 2.5 대시보드 업데이트 함수

```javascript
function updateDashboard(data) {
    // 1. KW 전역 변수 교체
    KW = data.keywords;

    // 2. Hero 숫자 업데이트
    updateHeroStats(data.total, data.keywords.length, ...);

    // 3. KPI 카드 업데이트
    updateKPICards(data);

    // 4. 영역 카드 업데이트
    updateAreaCards(data.areas);

    // 5. 차트 재빌드
    buildCharts();

    // 6. 키워드 테이블 재렌더
    rKT();
}
```

### 2.6 상태 관리

```
초기 로드 (DOMContentLoaded)
│
├─ localStorage에 저장된 데이터 있음?
│   ├─ 예 → 저장된 데이터로 대시보드 렌더
│   └─ 아니오 → 하드코딩된 KW 기본값으로 렌더
│
└─ Excel 업로드 시:
    ├─ parseExcel() → data
    ├─ localStorage.setItem('dashboard-data', JSON.stringify(data))
    ├─ updateDashboard(data)
    └─ 업로드 상태 표시: "✓ 30개 시트, 7,769행 로드됨"
```

### 2.7 코드 변경 요약

| # | 변경 | 위치 | 타입 |
|---|------|------|------|
| 1 | XLSX.js CDN 추가 | `<head>` | script 태그 |
| 2 | 업로드 UI 섹션 | Hero 아래 | HTML 추가 |
| 3 | `.upload-*` CSS | `<style>` | CSS 추가 |
| 4 | `parseExcel()` | `<script>` | JS 함수 신규 |
| 5 | `updateDashboard()` | `<script>` | JS 함수 신규 |
| 6 | `updateHeroStats()` | `<script>` | JS 함수 신규 |
| 7 | `updateKPICards()` | `<script>` | JS 함수 신규 |
| 8 | `updateAreaCards()` | `<script>` | JS 함수 신규 |
| 9 | Hero 숫자를 동적으로 변경 | 기존 `data-count` → id 추가 | HTML 수정 |
| 10 | KPI 값을 동적으로 변경 | 기존 하드코딩 → id 추가 | HTML 수정 |
| 11 | 영역 카드를 동적으로 변경 | id 추가 또는 JS 렌더 | HTML 수정 |
| 12 | localStorage 저장/로드 | DOMContentLoaded | JS 추가 |

### 2.8 제약사항

- Excel 열 순서가 달라도 **헤더명**으로 매핑 (number, 영역, filename, 등급, 사고사례여부)
- 시트 이름이 키워드 역할 (기존 SearchInMD와 동일 패턴)
- 32MB 이상 파일은 브라우저 메모리 이슈 가능 → 경고 메시지

---

## 3. 구현 순서

```
Step 1: page_utils.py 공통 모듈 추출
Step 2: insert_page_markers.py 작성 + dry-run 테스트
Step 3: add_fullpage.py에서 page_utils import
Step 4: docs/index.html에 XLSX.js CDN + 업로드 UI
Step 5: parseExcel() + updateDashboard() 구현
Step 6: Hero/KPI/영역카드 동적 업데이트
Step 7: localStorage 캐시
Step 8: 수동 테스트
```

## 4. 체크리스트

### D2 (페이지 마커)
- [ ] `page_utils.py` 공통 모듈 (build_page_map, find_md_and_meta)
- [ ] `insert_page_markers.py` 스크립트
- [ ] --dry-run 모드
- [ ] --backup 모드
- [ ] 52개 .md 파일에 마커 삽입 확인
- [ ] `add_fullpage.py`에서 page_utils import

### C2 (대시보드 업로드)
- [ ] XLSX.js CDN 추가
- [ ] 업로드 UI (버튼 + 상태)
- [ ] parseExcel() 함수
- [ ] updateDashboard() 함수
- [ ] Hero 숫자 동적 업데이트
- [ ] KPI 카드 동적 업데이트
- [ ] 영역 카드 동적 업데이트
- [ ] 차트 재빌드
- [ ] 키워드 테이블 재렌더
- [ ] localStorage 저장/로드
