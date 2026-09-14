#!/usr/bin/env python3
"""
마크다운 파일의 <!-- page: N --> 마커 값을 일괄로 옮깁니다 (N → N+by).

사용법:
  python3 shift_page_markers.py FILE.md                # +1
  python3 shift_page_markers.py FILE.md --by 1 --dry-run
  python3 shift_page_markers.py FILE.md --backup       # FILE.md.bak 을 남기고 적용

왜 있나: 2026-09-13 에 추가된 NCS 2권(LM1903060408, LM1903060424)은 다른 변환기가
마커를 _meta.json 의 page_id 그대로(0-based) 심었다. 기존 84권은 page_id+1 규약
(docs/howto-page-markers.md). 마커를 걷어내고 목차에서 재유도하면(insert_page_markers.py
--force) 쪽당 하나였던 촘촘한 마커가 목차 단위로 성겨지므로, 값만 옮긴다.

마커 줄만 바꾸고 나머지는 바이트 그대로 둔다(CRLF 포함, 임시 파일에 쓴 뒤 교체). 거부 조건(파일 무변경):
  마커 없음 / 결과 마커 < 1 / 마커 값이 감소(비단조) / 본문 줄 안에 낀 마커가 하나라도 있음
  (insert_page_markers.py 와 같은 규칙 — 그 줄은 고칠 수 없으니 옮기면 그 값만 어긋난 채 남는다) /
  --backup 인데 .bak 이 이미 있음. 같은 파일에 두 번 돌리면 두 번 옮겨지므로 --dry-run 으로 먼저 확인할 것.
_meta.json 은 건드리지 않는다.
"""

import argparse
import os
import shutil
import sys
from page_utils import PAGE_MARKER_RE


def shift_lines(lines, by):
    """마커만 있는 줄의 N 을 N+by 로 바꾼 줄 목록과 마커 값 목록을 돌려준다.

    본문 줄 안에 낀 마커(insert_page_markers.strip_page_markers 와 같은 판정)가 하나라도
    있으면 (None, []) — 그 줄은 고칠 수 없고, 나머지만 옮기면 그 값만 어긋난 채 남는다.
    """
    out, values = [], []
    for ln in lines:
        m = PAGE_MARKER_RE.fullmatch(ln.strip())
        if not m and PAGE_MARKER_RE.search(ln):
            return None, []                                   # 본문 줄에 낀 마커 — 호출부가 거부한다
        if m:
            n = int(m.group(1))
            values.append(n)
            head, tail = ln[:ln.index(m.group(0))], ln[ln.index(m.group(0)) + len(m.group(0)):]
            out.append('%s<!-- page: %d -->%s' % (head, n + by, tail))
        else:
            out.append(ln)
    return out, values


def shift_file(md_path, by=1, dry_run=False, backup=False):
    """한 파일을 처리하고 결과 dict 를 돌려준다. status 가 shifted 일 때만 파일이 바뀐다."""
    with open(md_path, encoding='utf-8', newline='') as f:      # newline='' — CRLF 를 LF 로 바꾸지 않는다
        content = f.read()
    lines = content.split('\n')
    new_lines, values = shift_lines(lines, by)
    info = {'file': md_path, 'by': by, 'markers': len(values),
            'first': values[0] if values else None, 'last': values[-1] if values else None}
    if new_lines is None:
        return dict(info, status='refuse_inline_marker')
    if not values:
        return dict(info, status='skip_no_markers')
    if any(b < a for a, b in zip(values, values[1:])):
        return dict(info, status='refuse_non_monotone')
    if min(values) + by < 1:
        return dict(info, status='refuse_below_one')
    if dry_run:
        return dict(info, status='dry_run')
    if backup:
        if os.path.exists(md_path + '.bak'):
            return dict(info, status='refuse_backup_exists')   # 유일한 복구본을 덮어쓰지 않는다
        shutil.copy2(md_path, md_path + '.bak')
    tmp = md_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(new_lines))
    os.replace(tmp, md_path)                                    # 중단돼도 원본이 반쪽으로 남지 않는다
    return dict(info, status='shifted')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('files', nargs='+', help='마크다운 파일')
    parser.add_argument('--by', type=int, default=1, help='더할 값 (기본 1)')
    parser.add_argument('--dry-run', action='store_true', help='변경 없이 보고만')
    parser.add_argument('--backup', action='store_true', help='원본을 .bak 으로 백업')
    args = parser.parse_args()
    bad = 0
    for path in args.files:
        r = shift_file(path, by=args.by, dry_run=args.dry_run, backup=args.backup)
        if r['status'] in ('shifted', 'dry_run'):
            print('%s: %s markers=%d first=%s→%s last=%s→%s' % (
                r['status'], path, r['markers'], r['first'], r['first'] + args.by, r['last'], r['last'] + args.by))
        else:
            bad += 1
            print('%s: %s markers=%d first=%s last=%s' % (r['status'], path, r['markers'], r['first'], r['last']))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
