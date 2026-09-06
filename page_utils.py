#!/usr/bin/env python3
"""
공통 유틸리티: 페이지 매핑, 파일 검색, NFC 정규화, 엑셀 셀 절단 판정
add_fullpage.py, insert_page_markers.py, recount_grades.py, regrade.py 에서 공유
"""

import os
import re
import json
import unicodedata

EXCEL_MAX_CHARS = 32767          # 엑셀 셀 한도. add_fullpage.py 가 여기서 가져다 쓴다
# 재코딩 표본의 층 이름. make_coding_sheet(추출)·score_coding(채점)이 같이 쓴다 — 두 벌로 타이핑하면
# 층을 하나 늘릴 때 한쪽만 고쳐지고 조용히 어긋난다. score_coding 은 regrade(openpyxl 가드)를 못
# 부르므로 의존성 없는 이 모듈이 소유한다.
CODING_GROUPS = ('disputed', 'control', 'boundary', 'recall')
BASELINE = 'baseline'            # 재현 기준선(현행 규칙)의 변형 라벨. 다른 변형 라벨은 regrade.variant_grid() 가 소유한다
TRUNCATION_MARK = '...'
GRADE_LABEL = {1: '미흡·없음', 2: '형식적 언급', 3: '구체적 대책'}   # 출하 등급 라벨 — recount_grades.py·resegment.py 가 공유한다
PAGE_MARKER_RE = re.compile(r'<!--\s*page:\s*(\d+)\s*-->')          # <!-- page: N --> 마커 — build_page_map·insert_page_markers.py·resegment.py 가 공유한다


def nfc(s):
    """NFC normalize a string."""
    return unicodedata.normalize('NFC', s) if s else s


def is_cell_truncated(text):
    """엑셀 셀 한도에 붙어 잘린 본문인지 판정한다.

    add_fullpage.py 는 `full_content[:EXCEL_MAX_CHARS - 3] + '...'` 로 자르므로
    잘린 셀은 정확히 32,767자이고 '...' 로 끝난다. 두 조건을 **모두** 요구한다.

      길이만 보면  원래 정확히 32,767자였던 본문을 절단으로 오판한다. 그런 본문은
                   `len > EXCEL_MAX_CHARS` 가 거짓이라 자르지 않고 통과하므로
                   '...' 가 붙지 않는다 — 마커가 이 둘을 가른다.
      마커만 보면  '...' 로 끝나는 짧은 본문을 전부 절단으로 오판한다.

    남는 오탐은 "원래 정확히 32,767자이면서 '...' 로 끝나는 본문" 하나뿐이다.
    실측 NCS 1,847쪽·교과서 362쪽에서 두 조건이 갈리는 사례는 0건이었다.

    **원시 셀 값으로 부르라.** str.strip() 을 거친 값을 넘기면 앞뒤 공백이 사라져
    길이가 32,767 미만으로 줄고 탐지에 실패한다.
    """
    return (isinstance(text, str)
            and len(text) == EXCEL_MAX_CHARS
            and text.endswith(TRUNCATION_MARK))


def find_md_and_meta(ncs_bases, rel_path):
    """
    Excel B열의 상대 경로로 여러 NCS 디렉토리에서 .md 파일과 _meta.json을 찾습니다.
    """
    parts = rel_path.split('/')
    if len(parts) < 3:
        return None, None

    category = parts[0]
    folder = parts[1]
    md_name = parts[2]
    md_base = md_name.replace('.md', '').replace('.markdown', '')

    for ncs_base in ncs_bases:
        folder_path = os.path.join(ncs_base, category, folder)
        if not os.path.isdir(folder_path):
            continue

        md_file = None
        meta_file = None

        for f in os.listdir(folder_path):
            f_nfc = nfc(f)
            if f_nfc.endswith('.md') and md_base in f_nfc:
                md_file = os.path.join(folder_path, f)
            elif f_nfc.endswith('_meta.json') and md_base in f_nfc:
                meta_file = os.path.join(folder_path, f)

        if md_file:
            return md_file, meta_file

    return None, None


def build_page_map(lines, metadata):
    """
    markdown-search-app.html의 buildPageMapping 로직을 Python으로 포팅.
    Strategy 1: <!-- page: N --> 마커
    Strategy 2: TOC 기반 매칭 (unique title match + propagation)

    Returns: dict[line_number(1-based)] -> page_number(1-based), or None
    """
    page_map = {}

    # Strategy 1: Page markers
    marker_count = 0
    current_page = None
    for i, line in enumerate(lines):
        m = PAGE_MARKER_RE.search(line)
        if m:
            current_page = int(m.group(1))
            marker_count += 1
        if current_page is not None:
            page_map[i + 1] = current_page

    if marker_count > 0:
        return page_map if page_map else None

    # Strategy 2: TOC-based
    if not metadata or 'table_of_contents' not in metadata:
        return None

    toc = metadata['table_of_contents']

    def normalize(text):
        text = re.sub(r'^#+\s*', '', text)
        text = text.replace('**', '').replace('\n', ' ')
        return re.sub(r'\s+', ' ', text).strip()

    def is_heading(trimmed):
        if re.match(r'^#+\s', trimmed): return True
        if re.match(r'^[○●◆◇■□▶▷]+\s', trimmed): return True
        if re.match(r'^\(?[가-힣\d]+[.\)]\s', trimmed): return True
        return False

    def is_standalone_title(trimmed, prev_empty):
        if not prev_empty: return False
        if len(trimmed) > 25: return False
        if re.match(r'^[•·\-*]\s', trimmed): return False
        if re.search(r'[다.!?。！？]$', trimmed): return False
        if not re.search(r'[가-힣]', trimmed): return False
        if re.match(r'^\s*\|', trimmed) or '![' in trimmed: return False
        return True

    heading_lines = []
    prev_empty = True
    in_code = False
    for i, line in enumerate(lines):
        trimmed = line.strip()
        if trimmed.startswith('```'):
            in_code = not in_code
            prev_empty = False
            continue
        if in_code:
            prev_empty = False
            continue
        if not trimmed:
            prev_empty = True
            continue
        if is_heading(trimmed) or is_standalone_title(trimmed, prev_empty):
            heading_lines.append((i + 1, normalize(trimmed)))
        prev_empty = False

    toc_by_title = {}
    for ti, item in enumerate(toc):
        if not item.get('title'): continue
        key = normalize(item['title'])
        if not key: continue
        toc_by_title.setdefault(key, []).append((item.get('page_id', 0), ti))

    md_by_title = {}
    for ln, txt in heading_lines:
        md_by_title.setdefault(txt, []).append(ln)

    heading_page_map = {}
    toc_used = set()
    for title, toc_entries in toc_by_title.items():
        md_headings = md_by_title.get(title)
        if not md_headings: continue
        if len(toc_entries) == 1 and len(md_headings) == 1:
            toc_used.add(toc_entries[0][1])
            heading_page_map[md_headings[0]] = toc_entries[0][0] + 1

    if not heading_page_map:
        return None

    sorted_headings = sorted(heading_page_map.keys())
    if sorted_headings:
        first_page = heading_page_map[sorted_headings[0]]
        for ln in range(1, sorted_headings[0]):
            page_map[ln] = first_page

    for idx in range(len(sorted_headings)):
        start = sorted_headings[idx]
        end = sorted_headings[idx + 1] - 1 if idx + 1 < len(sorted_headings) else len(lines)
        page = heading_page_map[start]
        for ln in range(start, end + 1):
            page_map[ln] = page

    return page_map if page_map else None


def extract_page_content(lines, page_map, target_page, matched_line):
    """해당 페이지의 전체 내용을 추출합니다."""
    if page_map and target_page:
        page_lines = []
        for ln, pn in sorted(page_map.items()):
            if pn == target_page:
                page_lines.append(lines[ln - 1])
        if page_lines:
            return '\n'.join(page_lines)
        all_pages = sorted(set(page_map.values()))
        if all_pages:
            max_page = max(all_pages)
            total_lines = len(lines)
            est_start = int((target_page - 1) / max(max_page, 1) * total_lines)
            est_end = int(target_page / max(max_page, 1) * total_lines)
            est_start = max(0, est_start - 5)
            est_end = min(total_lines, est_end + 5)
            return '\n'.join(lines[est_start:est_end])

    center = max(0, matched_line - 1)
    start = max(0, center - 20)
    end = min(len(lines), center + 21)
    return '\n'.join(lines[start:end])
