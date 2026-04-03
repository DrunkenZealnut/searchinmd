#!/usr/bin/env python3
"""
_meta.json 기반으로 마크다운 파일에 <!-- page: N --> 마커를 자동 삽입합니다.

사용법:
  python3 insert_page_markers.py                    # 기본 NCS 디렉토리 처리
  python3 insert_page_markers.py --dry-run           # 변경 없이 미리보기
  python3 insert_page_markers.py --backup            # .md.bak 백업 후 삽입
  python3 insert_page_markers.py /path/to/ncs        # 특정 디렉토리 지정
"""

import os
import re
import sys
import json
import glob
import shutil
import argparse
from page_utils import nfc, build_page_map


DEFAULT_NCS_DIRS = [
    "/Users/zealnutkim/Documents/청년노동자인권센터/교과서/교과서/NCS",
    "/Users/zealnutkim/Documents/DEV/SafeFactory/documents/semiconductor/ncs/data",
]


def has_page_markers(content):
    """파일에 이미 <!-- page: N --> 마커가 있는지 확인"""
    return bool(re.search(r'<!--\s*page:\s*\d+\s*-->', content))


def find_paired_meta(md_path):
    """같은 폴더에서 _meta.json 찾기"""
    folder = os.path.dirname(md_path)
    md_base = os.path.basename(md_path).replace('.md', '').replace('.markdown', '')
    # Remove date prefix if present (e.g., 20260121_174526_)
    clean_base = re.sub(r'^\d{8}_\d{6}_', '', md_base)

    for f in os.listdir(folder):
        f_nfc = nfc(f)
        if f_nfc.endswith('_meta.json'):
            # Match either with or without date prefix
            if clean_base in f_nfc or md_base in f_nfc:
                return os.path.join(folder, f)
    return None


def insert_markers(lines, page_map):
    """페이지 전환점에 <!-- page: N --> 마커를 삽입합니다."""
    output = []
    prev_page = None

    for i, line in enumerate(lines):
        ln = i + 1  # 1-based
        current_page = page_map.get(ln)

        if current_page and current_page != prev_page:
            output.append(f'<!-- page: {current_page} -->\n')
            prev_page = current_page

        output.append(line if line.endswith('\n') else line + '\n')

    return output


def process_file(md_path, dry_run=False, backup=False):
    """단일 .md 파일을 처리합니다."""
    with open(md_path, encoding='utf-8') as f:
        content = f.read()

    if has_page_markers(content):
        return 'skip_has_markers'

    meta_path = find_paired_meta(md_path)
    if not meta_path:
        return 'skip_no_meta'

    with open(meta_path, encoding='utf-8') as f:
        metadata = json.load(f)

    lines = content.split('\n')
    page_map = build_page_map(lines, metadata)

    if not page_map:
        return 'skip_no_mapping'

    # Count unique pages mapped
    unique_pages = len(set(page_map.values()))

    if dry_run:
        return f'would_insert_{unique_pages}_pages'

    # Insert markers
    new_lines = insert_markers(lines, page_map)
    new_content = ''.join(new_lines)

    # Verify markers were actually inserted
    if not has_page_markers(new_content):
        return 'skip_insert_failed'

    # Backup if requested
    if backup:
        shutil.copy2(md_path, md_path + '.bak')

    # Write back
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return f'inserted_{unique_pages}_pages'


def main():
    parser = argparse.ArgumentParser(description='마크다운 파일에 페이지 마커 자동 삽입')
    parser.add_argument('dirs', nargs='*', default=DEFAULT_NCS_DIRS, help='NCS 디렉토리 경로')
    parser.add_argument('--dry-run', action='store_true', help='변경 없이 처리할 파일 목록만 출력')
    parser.add_argument('--backup', action='store_true', help='원본을 .md.bak으로 백업')
    parser.add_argument('--force', action='store_true', help='이미 마커 있는 파일도 재처리')
    args = parser.parse_args()

    stats = {'processed': 0, 'inserted': 0, 'skip_markers': 0,
             'skip_no_meta': 0, 'skip_no_mapping': 0, 'errors': 0}

    if args.dry_run:
        print("=== DRY RUN 모드 (변경 없음) ===\n")

    for ncs_dir in args.dirs:
        if not os.path.isdir(ncs_dir):
            print(f"경고: 디렉토리 없음 - {ncs_dir}")
            continue

        md_files = glob.glob(os.path.join(ncs_dir, '**/*.md'), recursive=True)

        for md_path in sorted(md_files):
            if 'report' in md_path.lower():
                continue

            stats['processed'] += 1
            rel = os.path.relpath(md_path, ncs_dir)

            try:
                result = process_file(md_path, dry_run=args.dry_run, backup=args.backup)

                if result == 'skip_has_markers':
                    stats['skip_markers'] += 1
                elif result == 'skip_no_meta':
                    stats['skip_no_meta'] += 1
                    if args.dry_run:
                        print(f"  SKIP (meta 없음): {rel}")
                elif result == 'skip_no_mapping':
                    stats['skip_no_mapping'] += 1
                    if args.dry_run:
                        print(f"  SKIP (매핑 실패): {rel}")
                elif result.startswith('would_insert'):
                    pages = result.split('_')[2]
                    print(f"  INSERT 예정 ({pages}페이지): {rel}")
                    stats['inserted'] += 1
                elif result.startswith('inserted'):
                    pages = result.split('_')[1]
                    print(f"  DONE ({pages}페이지): {rel}")
                    stats['inserted'] += 1
                else:
                    stats['errors'] += 1

            except Exception as e:
                stats['errors'] += 1
                print(f"  ERROR: {rel} - {e}")

    print(f"\n=== {'DRY RUN ' if args.dry_run else ''}결과 ===")
    print(f"  전체 파일: {stats['processed']}")
    print(f"  마커 삽입{'예정' if args.dry_run else '완료'}: {stats['inserted']}")
    print(f"  이미 마커 있음: {stats['skip_markers']}")
    print(f"  meta.json 없음: {stats['skip_no_meta']}")
    print(f"  매핑 실패: {stats['skip_no_mapping']}")
    if stats['errors']:
        print(f"  오류: {stats['errors']}")


if __name__ == '__main__':
    main()
