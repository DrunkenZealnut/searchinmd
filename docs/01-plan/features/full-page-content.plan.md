# Plan: 키워드 매치 페이지 전체 내용 가져오기

## Executive Summary

| 항목 | 내용 |
|------|------|
| Feature | full-page-content (페이지 전체 내용 셀 추가) |
| 작성일 | 2026-04-01 |
| 브랜치 | feature/full-page-content |

| 관점 | 설명 |
|------|------|
| **Problem** | 키워드 검색 결과에 매칭된 문장만 표시되어, 해당 문장이 속한 페이지의 전체 맥락을 파악하려면 원본 문서를 다시 열어야 한다 |
| **Solution** | 검색 결과에 해당 페이지의 전체 내용을 별도 셀로 추가하여 Excel Export 시 원본 확인 없이 맥락 파악 가능 |
| **Function UX Effect** | Excel에서 키워드 매치 내용 옆에 페이지 전체 내용이 함께 표시되어, 문서를 다시 열지 않고 한 번에 검토 가능 |
| **Core Value** | 검색→검토 워크플로우에서 원본 참조 단계를 제거하여 작업 속도를 크게 향상 |

## 1. 배경 및 목적

### 현재 상태
- 키워드 검색 시 매칭된 **문장**, **표**, **이미지**만 `content` 셀에 저장
- 페이지 번호(또는 줄 번호)는 별도 컬럼에 표시
- 해당 페이지의 전후 맥락을 보려면 원본 마크다운 파일을 직접 열어야 함

### 목표
- 검색 결과 각 행에 **"페이지 전체 내용"** 셀을 추가
- `pageMap`을 활용하여 매칭된 줄이 속한 페이지의 모든 줄을 추출
- UI 결과 테이블과 Excel Export 모두에 반영

## 2. 기능 요구사항

### FR-01: 페이지 전체 내용 추출
- `performSearch()` 에서 각 매칭 결과에 `fullPageContent` 필드 추가
- `pageMap`에서 해당 `lineNumber`의 페이지 번호를 조회
- 같은 페이지 번호를 가진 **모든 줄**을 결합하여 전체 내용 생성
- `pageMap`이 없는 경우(페이지 정보 없음): 빈 문자열 또는 매칭 줄 전후 일정 범위(±20줄) 제공

### FR-02: Excel Export에 새 컬럼 추가
- `exportToExcel()` 에서 기존 4개 컬럼(번호, 파일명, 내용, 페이지) 뒤에 **"페이지전체내용"** 컬럼 추가
- 컬럼 헤더 alias: `['fullpage', '페이지전체내용', '전체내용', 'full page', 'full content']`
- Excel 셀 32,767자 제한 적용 (truncation with `...`)

### FR-03: UI 결과 테이블 표시
- 결과 테이블에 "페이지 전체" 컬럼 추가
- 내용이 길므로 접기/펼치기(toggle) UI 제공
- 기본 상태: 접힘 (첫 100자 + "더보기" 버튼)

### FR-04: 페이지 내용 캐싱
- 같은 파일+같은 페이지에서 여러 매칭이 발생하면 동일한 페이지 내용을 공유
- 파일 단위로 `pageContentCache: Map<pageNumber, string>` 생성
- 메모리 효율: 파일 처리 완료 후 캐시 해제

## 3. 기술 분석

### 변경 대상

```
markdown-search-app.html
├── performSearch()         — fullPageContent 필드 추가
├── extractPageContent()    — [신규] 페이지 번호로 전체 내용 추출
├── renderResultsTable()    — 새 컬럼 렌더링 + toggle UI
├── exportToExcel()         — 새 컬럼 추가 (template / no-template 양쪽)
└── CSS                     — toggle 스타일
```

### 핵심 로직: extractPageContent(lines, pageMap, pageNumber)

```
INPUT: lines[], pageMap (Map<lineNumber, pageNumber>), targetPage
OUTPUT: string (해당 페이지의 모든 줄을 합친 텍스트)

1. pageMap 순회하여 targetPage와 같은 pageNumber를 가진 lineNumber 수집
2. 해당 lineNumber들의 lines[lineNumber-1] 결합
3. 결과 반환

pageMap이 null인 경우:
  → matchedLineNumber 기준 ±20줄 범위 반환
```

### 데이터 플로우

```
performSearch()
  │
  ├── pageMap = buildPageMapping(lines, metadata)
  │
  ├── for each match:
  │     pageNum = pageMap.get(lineNumber)
  │     fullPageContent = extractPageContent(lines, pageMap, pageNum)
  │     result.fullPageContent = fullPageContent
  │
  └── searchResults[keyword].push({ ..., fullPageContent })
          │
          ├── renderResultsTable()  → 새 컬럼 (toggle)
          └── exportToExcel()       → 새 컬럼 (fullpageCol)
```

## 4. 제약사항 및 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 메모리 증가 | 페이지 전체 내용이 결과마다 중복 저장될 수 있음 | FR-04 캐싱으로 같은 페이지 참조 시 문자열 공유 |
| Excel 셀 크기 | 페이지 내용이 32,767자 초과 가능 | truncation 적용 |
| pageMap 없는 경우 | 페이지 구분 불가 | ±20줄 fallback 범위 제공 |
| UI 렌더링 성능 | 수백 개 결과에 긴 텍스트가 있으면 DOM 무거움 | 접기 기본 + lazy rendering |

## 5. 구현 범위

### In Scope
- `extractPageContent()` 함수 신규 작성
- `performSearch()` 에서 `fullPageContent` 필드 추가
- `renderResultsTable()` 에 toggle 가능한 새 컬럼
- `exportToExcel()` 두 경로 모두에 새 컬럼
- CSS 스타일 추가

### NOT In Scope
- 페이지 내용의 별도 탭/모달 뷰어
- 페이지 내용에 대한 2차 키워드 하이라이팅
- 페이지 내용 기반 추가 검색 기능

## 6. 완료 기준

- [ ] 검색 결과에 `fullPageContent` 필드가 포함됨
- [ ] UI 테이블에 "페이지 전체" 컬럼이 toggle로 표시됨
- [ ] Excel Export에 "페이지전체내용" 컬럼이 추가됨
- [ ] pageMap 있는 경우: 정확한 페이지 내용 추출
- [ ] pageMap 없는 경우: ±20줄 fallback 동작
- [ ] 같은 파일+페이지 중복 시 캐시 사용으로 메모리 절약
- [ ] 32,767자 초과 시 truncation 정상 동작
