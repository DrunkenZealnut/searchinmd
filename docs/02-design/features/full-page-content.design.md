# Design: 키워드 매치 페이지 전체 내용 가져오기

> Plan 참조: `docs/01-plan/features/full-page-content.plan.md`

## 1. 구현 설계

### 1.1 변경 파일 및 순서

단일 파일 변경: `outputs/markdown-search-app.html`

```
구현 순서:
  1. extractPageContent() 함수 신규 작성
  2. performSearch() 에서 fullPageContent 필드 추가 + 캐시 로직
  3. CSS toggle 스타일 추가
  4. renderResultsTable() 에 새 컬럼 + toggle UI
  5. exportToExcel() 에 새 컬럼 (template + no-template 양쪽)
```

### 1.2 신규 함수: extractPageContent()

**위치**: `buildPageMapping()` 바로 아래 (약 line 1260 부근)

```javascript
function extractPageContent(lines, pageMap, targetPageNum, matchedLineNumber) {
    // Case 1: pageMap이 있고 targetPageNum이 있으면 → 해당 페이지의 모든 줄
    if (pageMap && targetPageNum) {
        const pageLines = [];
        for (const [lineNum, pageNum] of pageMap) {
            if (pageNum === targetPageNum) {
                pageLines.push(lines[lineNum - 1]); // lineNum is 1-based
            }
        }
        return pageLines.join('\n');
    }

    // Case 2: pageMap 없음 → matchedLineNumber 기준 ±20줄 fallback
    const start = Math.max(0, matchedLineNumber - 1 - 20);
    const end = Math.min(lines.length, matchedLineNumber - 1 + 21);
    return lines.slice(start, end).join('\n');
}
```

**설계 포인트**:
- `pageMap`은 `Map<lineNumber(1-based), pageNumber(1-based)>` 구조
- pageMap을 순회하면 해당 페이지에 속하는 모든 줄번호를 수집 가능
- Map 순회는 삽입 순서를 보장하므로 줄 순서가 유지됨 (buildPageMapping이 오름차순으로 삽입)
- fallback은 매칭 줄 중심 ±20줄 (총 41줄 범위)

### 1.3 performSearch() 변경

**위치**: 기존 `performSearch()` 내부, 파일 단위 루프의 `pageMap` 생성 직후

```
변경 전 (현재 구조):
  pageMap = buildPageMapping(lines, metadata)
  sentencesWithLines = extract...
  tablesWithLines = extract...
  imagesWithLines = extract...
  for (keyword of keywords) {
      // 각 match에 type, filename, content, lineNumber, pageNumber, hasPage 저장
  }

변경 후:
  pageMap = buildPageMapping(lines, metadata)
  const pageContentCache = new Map()  ← [신규] 파일 단위 캐시
  sentencesWithLines = extract...
  tablesWithLines = extract...
  imagesWithLines = extract...
  for (keyword of keywords) {
      // 각 match에서:
      const pageNum = pageMap ? pageMap.get(item.lineNumber) : null
      let fullPageContent
      if (pageNum && pageContentCache.has(pageNum)) {
          fullPageContent = pageContentCache.get(pageNum)     ← 캐시 히트
      } else {
          fullPageContent = extractPageContent(lines, pageMap, pageNum, item.lineNumber)
          if (pageNum) pageContentCache.set(pageNum, fullPageContent) ← 캐시 저장
      }
      result.fullPageContent = fullPageContent                ← 결과에 추가
  }
```

**searchResult 객체 변경**:

```javascript
// 기존
{ type, filename, content, lineNumber, pageNumber, hasPage, headingContext }

// 변경 후 (3가지 매치 타입 모두 동일하게)
{ type, filename, content, lineNumber, pageNumber, hasPage, headingContext, fullPageContent }
//                                                                          ^^^^^^^^^^^^^^^^^
```

문장, 표, 이미지 **3군데** 모두 `fullPageContent` 필드를 추가해야 함.

### 1.4 CSS 추가

**위치**: 기존 `.content-preview` 스타일 아래 (약 line 347 부근)

```css
.fullpage-cell {
    max-width: 300px;
    position: relative;
}

.fullpage-preview {
    max-height: 60px;
    overflow: hidden;
    font-family: monospace;
    font-size: 11px;
    background: #f0f4ff;
    padding: 6px 8px;
    border-radius: 4px;
    white-space: pre-wrap;
    word-break: break-all;
    color: #495057;
}

.fullpage-preview.expanded {
    max-height: none;
}

.fullpage-toggle {
    display: inline-block;
    margin-top: 4px;
    font-size: 11px;
    color: #667eea;
    cursor: pointer;
    border: none;
    background: none;
    padding: 0;
    text-decoration: underline;
}
```

### 1.5 renderResultsTable() 변경

**위치**: 기존 thead와 tbody 부분

```
변경 사항:
1. <thead>에 새 컬럼 추가:
   <th style="width: 300px;">페이지 전체</th>

2. <tbody> 각 행에 새 <td> 추가:
   <td class="fullpage-cell">
     <div class="fullpage-preview" id="fp-${i}">
       ${escapeHtml((r.fullPageContent || '').substring(0, 200))}
     </div>
     ${(r.fullPageContent || '').length > 200
       ? '<button class="fullpage-toggle" onclick="...">[더보기]</button>'
       : ''}
   </td>

3. toggle 클릭 핸들러:
   - 클릭 시 div에 .expanded 클래스 토글
   - 버튼 텍스트 [더보기] ↔ [접기] 전환
   - 전체 내용은 data-full 속성 또는 searchResults에서 직접 참조
```

**toggle 구현 방식**: 
- inline onclick 사용 (기존 코드 패턴과 일관성 유지)
- `data-full` 속성에 전체 내용 저장하지 않음 (DOM 비대화 방지)
- 대신 접힘 상태에서는 200자, 펼침 상태에서는 전체 내용을 `escapeHtml`로 렌더

```javascript
// renderResultsTable() 함수 끝에 toggle 이벤트 바인딩 추가
document.querySelectorAll('.fullpage-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
        const idx = parseInt(btn.dataset.idx);
        const preview = document.getElementById('fp-' + idx);
        const result = results[idx];
        const full = result.fullPageContent || '';
        if (preview.classList.contains('expanded')) {
            preview.classList.remove('expanded');
            preview.textContent = full.substring(0, 200);
            btn.textContent = '[더보기]';
        } else {
            preview.classList.add('expanded');
            preview.textContent = full;
            btn.textContent = '[접기]';
        }
    });
});
```

### 1.6 exportToExcel() 변경

**2군데** 모두 변경 필요:

#### A. Template 있는 경우 (line ~1694)

```javascript
// 기존 alias 목록에 추가:
const fullpageAliases = ['fullpage', '페이지전체내용', '전체내용', 'full page', 'full content', 'page content'];

// 컬럼 인덱스:
let fullpageCol = findCol(fullpageAliases);
if (fullpageCol === -1) fullpageCol = maxCol + 1;   // 기존 컬럼 뒤에 추가

// maxCol 업데이트:
const maxCol = Math.max(numberCol, filenameCol, contentsCol, pageCol, fullpageCol);

// 데이터 행 추가 (results.forEach 내부):
let fullpage = r.fullPageContent || '';
if (fullpage.length > EXCEL_MAX_CHARS) {
    fullpage = fullpage.substring(0, EXCEL_MAX_CHARS - 3) + '...';
}
newSheet[XLSX.utils.encode_cell({ r: rowIndex, c: fullpageCol })] = { t: 's', v: fullpage };

// 기본 헤더 (origSheet 없을 때):
newSheet[XLSX.utils.encode_cell({ r: 0, c: fullpageCol })] = { t: 's', v: '페이지전체내용' };

// 기본 열 너비:
newSheet['!cols'][fullpageCol] = { wch: 100 };
```

#### B. Template 없는 경우 (line ~1660)

```javascript
// wsData 헤더:
const wsData = [['number', 'filename', 'contents', 'page', 'line', 'fullpage']];

// wsData 행:
wsData.push([
    i + 1,
    r.filename,
    content,
    r.hasPage ? r.pageNumber : '',
    r.lineNumber,
    (r.fullPageContent || '').substring(0, 32767)  // truncation
]);

// 열 너비:
ws['!cols'] = [{ wch: 8 }, { wch: 40 }, { wch: 80 }, { wch: 8 }, { wch: 8 }, { wch: 100 }];
```

## 2. 데이터 플로우 다이어그램

```
performSearch() — 파일 단위 루프
│
├─ lines = file.content.split('\n')
├─ pageMap = buildPageMapping(lines, metadata)
├─ pageContentCache = new Map()           ← [신규]
│
├─ sentencesWithLines = extract...(lines)
├─ tablesWithLines = extract...(lines)
├─ imagesWithLines = extract...(lines)
│
└─ for each keyword:
    ├─ for each sentence match:
    │   ├─ pageNum = pageMap.get(lineNumber)
    │   ├─ fullPageContent = cache.get(pageNum) ?? extractPageContent(...)
    │   └─ push { ..., fullPageContent }
    │
    ├─ for each table match:
    │   ├─ pageNum = pageMap.get(lineNumber)
    │   ├─ fullPageContent = cache.get(pageNum) ?? extractPageContent(...)
    │   └─ push { ..., fullPageContent }
    │
    └─ for each image match:
        ├─ pageNum = pageMap.get(lineNumber)
        ├─ fullPageContent = cache.get(pageNum) ?? extractPageContent(...)
        └─ push { ..., fullPageContent }

                    ↓
        searchResults[keyword]
                    ↓
    ┌───────────────┴───────────────┐
    │                               │
renderResultsTable()          exportToExcel()
    │                               │
    ├─ <th>페이지 전체</th>         ├─ fullpageCol 추가
    ├─ <td>200자 미리보기</td>      ├─ 32767자 truncation
    └─ [더보기] toggle              └─ 셀 쓰기
```

## 3. 캐시 전략

```
파일 1 처리 시작
  pageContentCache = new Map()     ← 파일마다 새로 생성
  
  keyword "반도체" match at line 50 → page 3
    cache miss → extractPageContent() → cache.set(3, content)
  
  keyword "제품" match at line 52 → page 3
    cache hit → cache.get(3)       ← 동일 페이지, 재계산 없음
  
  keyword "설계" match at line 120 → page 7
    cache miss → extractPageContent() → cache.set(7, content)

파일 1 처리 완료
  // pageContentCache는 다음 파일에서 새로 생성되므로 자동 GC
```

**캐시 효과**: 같은 파일 내 같은 페이지에서 N개 키워드가 매칭되면, `extractPageContent()`를 N번이 아닌 **1번**만 호출.

## 4. 코드 변경 위치 요약

| # | 변경 | 위치 (현재 line) | 타입 |
|---|------|-----------------|------|
| 1 | `extractPageContent()` | ~line 1260 (buildPageMapping 뒤) | 신규 함수 |
| 2 | `pageContentCache` 생성 | ~line 1289 (pageMap 생성 직후) | 1줄 추가 |
| 3 | 문장 매치에 `fullPageContent` | ~line 1333 (push 호출부) | 캐시 조회 + 필드 추가 |
| 4 | 표 매치에 `fullPageContent` | ~line 1352 (push 호출부) | 캐시 조회 + 필드 추가 |
| 5 | 이미지 매치에 `fullPageContent` | ~line 1370 (push 호출부) | 캐시 조회 + 필드 추가 |
| 6 | CSS `.fullpage-*` 스타일 | ~line 347 (content-preview 아래) | CSS 추가 |
| 7 | `<thead>` 새 컬럼 | ~line 1609 | th 추가 |
| 8 | `<tbody>` 새 셀 + toggle | ~line 1613 | td 추가 |
| 9 | toggle 이벤트 바인딩 | ~line 1625 (renderResultsTable 끝) | JS 추가 |
| 10 | export (template) `fullpageCol` | ~line 1700 | alias + 데이터 + 헤더 |
| 11 | export (no-template) `fullpage` | ~line 1660 | 헤더 + 데이터 + 너비 |

## 5. 엣지 케이스

| 케이스 | 동작 |
|--------|------|
| `pageMap` null (메타데이터 없음) | ±20줄 fallback 반환 |
| `pageMap` 있지만 해당 줄에 페이지 매핑 없음 | `pageNum`이 null → fallback |
| 페이지 내용이 비어있음 | 빈 문자열 반환, UI에 "-" 표시 |
| 페이지 내용 > 32,767자 | Excel export 시 truncation |
| 같은 파일+같은 페이지 여러 매칭 | 캐시로 1번만 추출 |
| LLM 모드 사용 시 | `sentencesWithLines` 출처가 다를 뿐, `lineNumber`로 pageMap 조회하는 로직은 동일 |
| 검색 결과 0건인 키워드 | fullPageContent 관련 코드 진입 안함 |

## 6. 구현 순서 체크리스트

- [ ] 1. `extractPageContent()` 함수 작성
- [ ] 2. `performSearch()` 내 `pageContentCache` + fullPageContent 로직 추가 (3군데)
- [ ] 3. CSS `.fullpage-*` 스타일 추가
- [ ] 4. `renderResultsTable()` 에 새 컬럼 + toggle
- [ ] 5. `exportToExcel()` template 경로에 fullpageCol 추가
- [ ] 6. `exportToExcel()` no-template 경로에 fullpage 추가
- [ ] 7. 수동 테스트: test-samples/ 로 검색 후 UI 확인
- [ ] 8. 수동 테스트: Excel export 후 새 컬럼 확인
