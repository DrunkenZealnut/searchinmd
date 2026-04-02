#!/usr/bin/env python3
"""
Excel 첫 번째 탭의 각 행에서 D열(페이지 번호)를 읽고,
해당 마크다운 파일에서 그 페이지의 전체 내용을 E열에 추가합니다.
"""

import os
import re
import json
import unicodedata
from pathlib import Path
from openpyxl import load_workbook

# === 설정 ===
EXCEL_PATH = "/Users/zealnutkim/Documents/청년노동자인권센터/2026년/교과서 기초연구/ncs_keywords&reworkinglist.xlsx"
NCS_BASES = [
    "/Users/zealnutkim/Documents/청년노동자인권센터/교과서/교과서/NCS",
    "/Users/zealnutkim/Documents/DEV/SafeFactory/documents/semiconductor/ncs/data",
]
OUTPUT_PATH = EXCEL_PATH.replace(".xlsx", "_with_fullpage.xlsx")
EXCEL_MAX_CHARS = 32767


def nfc(s):
    """NFC normalize a string."""
    return unicodedata.normalize('NFC', s) if s else s


def find_md_and_meta(ncs_bases, rel_path):
    """
    Excel B열의 상대 경로(예: 반도체개발/LM1903060101_.../LM1903060101_...md)로
    여러 NCS 디렉토리에서 실제 .md 파일과 _meta.json을 찾습니다.
    """
    parts = rel_path.split('/')
    if len(parts) < 3:
        return None, None

    category = parts[0]  # 반도체개발, 반도체제조, etc.
    folder = parts[1]    # LM1903060101_23v6_반도체_제품_기획
    md_name = parts[2]   # LM1903060101_23v6_반도체_제품_기획.md
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
    Strategy 2: TOC 기반 매칭 (simplified: unique title match + propagation)

    Returns: dict[line_number(1-based)] -> page_number(1-based)
    """
    page_map = {}

    # Strategy 1: Page markers
    marker_count = 0
    current_page = None
    for i, line in enumerate(lines):
        m = re.search(r'<!--\s*page:\s*(\d+)\s*-->', line)
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

    # Find heading lines
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

    # Group TOC by normalized title
    toc_by_title = {}
    for ti, item in enumerate(toc):
        if not item.get('title'): continue
        key = normalize(item['title'])
        if not key: continue
        toc_by_title.setdefault(key, []).append((item.get('page_id', 0), ti))

    # Group MD headings by title
    md_by_title = {}
    for ln, txt in heading_lines:
        md_by_title.setdefault(txt, []).append(ln)

    # Pass 1: unique matches
    heading_page_map = {}
    toc_used = set()
    for title, toc_entries in toc_by_title.items():
        md_headings = md_by_title.get(title)
        if not md_headings: continue
        if len(toc_entries) == 1 and len(md_headings) == 1:
            toc_used.add(toc_entries[0][1])
            heading_page_map[md_headings[0]] = toc_entries[0][0] + 1  # 0-based to 1-based

    if not heading_page_map:
        return None

    # Stage 3: Propagate (including lines before first heading)
    sorted_headings = sorted(heading_page_map.keys())

    # Lines before first heading get the first heading's page
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
        # page_map exists but target_page not found — estimate line range
        # Use linear interpolation: find nearest mapped pages
        all_pages = sorted(set(page_map.values()))
        total_lines = len(lines)
        if all_pages:
            max_page = max(all_pages)
            # Estimate line range for target_page
            est_start = int((target_page - 1) / max(max_page, 1) * total_lines)
            est_end = int(target_page / max(max_page, 1) * total_lines)
            est_start = max(0, est_start - 5)
            est_end = min(total_lines, est_end + 5)
            return '\n'.join(lines[est_start:est_end])

    # Fallback: ±20 lines
    center = max(0, matched_line - 1)
    start = max(0, center - 20)
    end = min(len(lines), center + 21)
    return '\n'.join(lines[start:end])


def main():
    print(f"Excel 파일 읽는 중: {EXCEL_PATH}")
    wb = load_workbook(EXCEL_PATH)
    ws = wb[wb.sheetnames[0]]
    print(f"시트: '{wb.sheetnames[0]}', 행: {ws.max_row}, 열: {ws.max_column}")

    # Add header for E column
    if ws.cell(row=2, column=5).value is None:
        ws.cell(row=2, column=5, value='페이지전체내용')

    # Cache: (md_path) -> (lines, page_map)
    file_cache = {}
    processed = 0
    skipped = 0
    errors = []

    for row_idx in range(3, ws.max_row + 1):  # Data starts at row 3
        filename = ws.cell(row=row_idx, column=2).value  # B: filename
        page_val = ws.cell(row=row_idx, column=4).value   # D: page number

        if not filename or page_val is None:
            skipped += 1
            continue

        try:
            target_page = int(page_val)
        except (ValueError, TypeError):
            skipped += 1
            continue

        filename = nfc(str(filename))

        # Find actual files
        if filename not in file_cache:
            md_path, meta_path = find_md_and_meta(NCS_BASES, filename)
            if md_path and os.path.exists(md_path):
                with open(md_path, encoding='utf-8') as f:
                    content = nfc(f.read())
                lines = content.split('\n')

                metadata = None
                if meta_path and os.path.exists(meta_path):
                    with open(meta_path, encoding='utf-8') as f:
                        metadata = json.load(f)

                page_map = build_page_map(lines, metadata)
                file_cache[filename] = (lines, page_map)
            else:
                file_cache[filename] = None
                if md_path is None:
                    errors.append(f"Row {row_idx}: 파일 못찾음 - {filename}")

        cached = file_cache.get(filename)
        if cached is None:
            skipped += 1
            continue

        lines, page_map = cached
        full_content = extract_page_content(lines, page_map, target_page, 1)

        # Truncate for Excel
        if len(full_content) > EXCEL_MAX_CHARS:
            full_content = full_content[:EXCEL_MAX_CHARS - 3] + '...'

        ws.cell(row=row_idx, column=5, value=full_content)  # E column
        processed += 1

        if processed % 500 == 0:
            print(f"  처리 중... {processed}행 완료")

    # Set column width
    ws.column_dimensions['E'].width = 100

    wb.save(OUTPUT_PATH)
    print(f"\n=== 완료 ===")
    print(f"처리 행: {processed}")
    print(f"건너뛴 행: {skipped}")
    print(f"파일 캐시: {len(file_cache)}개 파일")
    if errors:
        print(f"오류: {len(errors)}건")
        for e in errors[:10]:
            print(f"  {e}")
    print(f"저장: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
