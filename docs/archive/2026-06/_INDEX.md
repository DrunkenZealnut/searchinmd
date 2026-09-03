# Archive Index — 2026-06

완료된 PDCA 기능의 보관 문서 목록.

| Feature | Match Rate | 완료일 | 보관 문서 |
|---------|:----------:|--------|-----------|
| [keyword-search-perf](keyword-search-perf/) | 98% | 2026-06-21 | plan · design · analysis · report |

## keyword-search-perf

키워드 문서분석 루틴 성능개선 — `outputs/markdown-search-app.html`.

- **Problem**: 재검색마다 코퍼스 전체 재파싱 + 키워드 수만큼 반복 소문자화 → 지연 누적.
- **Solution**: `getParsedDoc` WeakMap 캐시 + 소문자 precompute + 검색 루프 전환 + 정규식 호이스팅 + 청크 렌더.
- **결과**: `toLowerCase` 재검색 **99.2%↓**(24,200→200), 결과 완전 동일, 회귀 11/11 PASS, Match Rate 98%.
- **관련 자산**: 회귀 테스트 `outputs/test-search-equivalence.js`(node vm), 백업 `outputs/markdown-search-app.html.bak-20260621`.

보관 문서:
- [Plan](keyword-search-perf/keyword-search-perf.plan.md)
- [Design](keyword-search-perf/keyword-search-perf.design.md)
- [Analysis](keyword-search-perf/keyword-search-perf.analysis.md)
- [Report](keyword-search-perf/keyword-search-perf.report.md)
