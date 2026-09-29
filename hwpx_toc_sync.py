#!/usr/bin/env python3
"""HWPX 목차 ↔ 쪽번호 연동 도구.

목차(“제목[탭]쪽번호” 문단들)를 찾아 본문 제목과 대조하고, 문서를 실제로 배치한 PDF
(Polaris Office·한글에서 내보낸 PDF, 또는 Polaris Tools 의 HWPX→PDF)에서 각 제목이 놓인
쪽을 찾아 목차의 쪽번호를 고친다. 쪽은 PDF 에 인쇄된 쪽번호가 있으면 그 번호를, 없으면
물리 쪽(표지 = 1)을 쓴다.

    # 검사만(파일을 쓰지 않음). 어긋나면 종료 코드 1
    python3.13 hwpx_toc_sync.py 문서.hwpx --pdf 문서.pdf --check

    # 쪽번호 갱신 → 문서_목차연동.hwpx
    python3.13 hwpx_toc_sync.py 문서.hwpx --pdf 문서.pdf

    # 바뀐 제목 반영 + 목차에 빠진 본문 제목 추가까지
    python3.13 hwpx_toc_sync.py 문서.hwpx --pdf 문서.pdf --sync-titles --add-missing

원칙
- 입력 파일은 절대 덮어쓰지 않는다. 출력이 이미 있으면 --force 없이는 멈춘다.
- 목차 문단 밖의 문단은 한 글자도 바꾸지 않는다(쓰기 전에 바이트 단위로 대조).
- 제목이 PDF 에서 한 곳이라도 안 찾히면 그 항목의 쪽은 그대로 두고 알린다(추측하지 않음).
- 줄 배치 캐시(hp:linesegarray)로 쪽을 추정하지 않는다 — 여러 쪽에 걸친 표를 덜 세어 틀린다.
- 본문이 빈 메모(<hp:subList/>)는 Polaris 의 HWP 변환을 멈추게 하므로 경고하고,
  --fix-empty-memos 로 빈 문단 하나를 넣어 고칠 수 있다.

필요: pymupdf(fitz) — PDF 에서 줄 단위 글자와 위치를 읽는다.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

HP = '{http://www.hancom.co.kr/hwpml/2011/paragraph}'
OUT_SUFFIX = '_목차연동'

_STRIP = re.compile(r'[\s 　·ㆍ・.,:：’\'‘"“”]+')
TOC_RE = re.compile(r'^(?P<title>.*\S)[  ]*\t+\s*(?P<page>\d{1,4})\s*$')
# 번호 매김 수준(목차 서식 틀을 고를 때 쓰는 열쇠)
LEVELS = [
    ('제N장', re.compile(r'^제\s*\d+\s*장(?!\.)')),
    ('제N장.', re.compile(r'^제\s*\d+\s*장\.')),
    ('N.', re.compile(r'^\d+\.(?!\d)')),
    ('N)', re.compile(r'^\d+\)')),
    ('(N)', re.compile(r'^\(\d+\)')),
    ('가.', re.compile(r'^[가-하]\.')),
    ('①', re.compile(r'^[①-⑳]')),
]
PAGE_LABEL = re.compile(r'[-–—\s]*(\d{1,4})[-–—\s]*(?:/\s*\d{1,4})?')   # 5 · - 5 - · 5/74
# PDF 의 목차 줄: 제목 + 공백이나 점선(·… ─ _ 따위) + 쪽번호. 점선이 쪽번호에 붙어 있어도 된다.
TOC_LINE = re.compile(r'^(?P<title>.*?\S)[\s.·ㆍ・…‥⋯∙_\-–—─]+(?P<page>\d{1,4})$')
TOKEN_RE = re.compile(r'^(제\s*\d+\s*장\.?|\d+\.(?!\d)|\d+\)|\(\d+\)|[가-하]\.|[①-⑳])')


def nfc(s: str) -> str:
    return unicodedata.normalize('NFC', s or '')


def norm(s: str) -> str:
    return _STRIP.sub('', nfc(s)).lower()


def level_of(title: str) -> str | None:
    t = nfc(title).strip()
    for key, pat in LEVELS:
        if pat.match(t):
            return key
    return None


def token_of(title: str) -> str | None:
    m = TOKEN_RE.match(nfc(title).strip())
    return re.sub(r'\s+', '', m.group(1)) if m else None


# ----------------------------------------------------------------------------- HWPX 읽기
def section_names(z: zipfile.ZipFile) -> list[str]:
    """content.hpf 의 spine 순서, 없으면 Contents/section*.xml 이름 순."""
    names = set(z.namelist())
    try:
        hpf = z.read('Contents/content.hpf').decode('utf-8')
        items = dict(re.findall(r'<opf:item id="([^"]+)" href="([^"]+)"', hpf))
        spine = [items[i] for i in re.findall(r'<opf:itemref idref="([^"]+)"', hpf) if i in items]
        secs = [s for s in spine if re.match(r'Contents/section\d+\.xml$', s) and s in names]
        if secs:
            return secs
    except KeyError:
        pass
    return sorted((n for n in names if re.match(r'Contents/section\d+\.xml$', n)),
                  key=lambda n: int(re.search(r'(\d+)', n).group(1)))


def top_spans(xml: str) -> list[tuple[int, int]]:
    """최상위 hp:p 의 (시작, 끝) 문자 위치 — 문자열 편집용(재직렬화하지 않는다)."""
    depth, spans, start = 0, [], None
    for m in re.finditer(r'<(/?)hp:p\b[^>]*?(/?)>', xml):
        close, selfc = m.groups()
        if close:
            depth -= 1
            if depth == 0:
                spans.append((start, m.end()))
        elif not selfc:
            if depth == 0:
                start = m.start()
            depth += 1
    return spans


def run_text(p: ET.Element) -> str:
    """문단의 직접 run 글자만(표·각주 같은 중첩 개체 안은 뺀다). 탭은 '\\t'."""
    out = []
    for run in p.findall(HP + 'run'):
        for t in run.findall(HP + 't'):
            if t.text:
                out.append(t.text)
            for sub in t:
                if sub.tag == HP + 'tab':
                    out.append('\t')
                elif sub.tag == HP + 'lineBreak':
                    out.append('\n')
                if sub.tail:
                    out.append(sub.tail)
    return ''.join(out)


def style_sig(p: ET.Element) -> tuple[str | None, str | None]:
    run = p.find(HP + 'run')
    return p.get('paraPrIDRef'), (run.get('charPrIDRef') if run is not None else None)


@dataclass
class Para:
    section: str
    index: int            # 구역 안 최상위 문단 번호
    xml: str
    text: str
    sig: tuple


@dataclass
class TocEntry:
    para: Para
    title: str
    page: int
    level: str | None
    heading: Para | None = None      # 대응하는 본문 제목 문단
    body_title: str | None = None     # 본문 제목 글자(문구가 다를 때)
    actual: int | None = None         # PDF 에서 찾은 쪽


@dataclass
class Doc:
    path: Path
    sections: dict[str, str]
    paras: list[Para]
    spans: dict[str, list[tuple[int, int]]]
    toc: list[TocEntry] = field(default_factory=list)
    body_start: int = 0               # paras 안에서 본문이 시작하는 위치


def load_hwpx(path: Path) -> Doc:
    with zipfile.ZipFile(path) as z:
        sections = {name: z.read(name).decode('utf-8') for name in section_names(z)}
    paras, spans = [], {}
    for name, xml in sections.items():
        root = ET.fromstring(xml.encode('utf-8'))
        elems = [p for p in root if p.tag == HP + 'p']
        sp = top_spans(xml)
        if len(sp) != len(elems):
            raise ValueError(f'{name}: 최상위 문단 수가 맞지 않습니다({len(sp)} != {len(elems)})')
        spans[name] = sp
        for i, (p, (a, b)) in enumerate(zip(elems, sp)):
            paras.append(Para(name, i, xml[a:b], run_text(p), style_sig(p)))
    return Doc(path, sections, paras, spans)


# ----------------------------------------------------------------------------- 목차·본문 제목
def find_toc(doc: Doc) -> None:
    """“제목[탭]숫자” 문단이 가장 많이 이어진 구간을 목차로 본다(빈 문단은 끼어도 된다)."""
    best, cur = [], []
    for k, p in enumerate(doc.paras):
        m = TOC_RE.match(p.text) if '\t' in p.text else None
        if m:
            cur.append((k, m))
        elif p.text.strip():
            if len(cur) > len(best):
                best = cur
            cur = []
    if len(cur) > len(best):
        best = cur
    if len(best) < 3:
        raise ValueError('목차를 찾지 못했습니다(“제목[탭]쪽번호” 문단이 3개 이상 이어진 곳이 없음)')
    doc.toc = [TocEntry(doc.paras[k], m.group('title').strip(), int(m.group('page')), level_of(m.group('title')))
               for k, m in best]
    doc.body_start = best[-1][0] + 1


def match_headings(doc: Doc) -> None:
    """목차 순서대로 본문 최상위 문단에서 같은 글자의 제목을 찾는다. 못 찾은 항목은
    앞뒤로 찾은 제목 사이에서 같은 번호·같은 제목 서식의 문단을 ‘문구가 바뀐 제목’으로 본다."""
    body = doc.paras[doc.body_start:]
    pos = {id(p): i for i, p in enumerate(body)}
    cur = 0
    for e in doc.toc:
        nt = norm(e.title)
        for i in range(cur, len(body)):
            if norm(body[i].text) == nt:
                e.heading, cur = body[i], i + 1
                break
    sigs = {e.heading.sig for e in doc.toc if e.heading is not None}
    for k, e in enumerate(doc.toc):
        if e.heading is not None:
            continue
        lo = next((pos[id(x.heading)] + 1 for x in reversed(doc.toc[:k]) if x.heading is not None), 0)
        hi = next((pos[id(x.heading)] for x in doc.toc[k + 1:] if x.heading is not None), len(body))
        tok = token_of(e.title)
        cands = [p for p in body[lo:hi] if p.text.strip() and p.sig in sigs and tok and token_of(p.text) == tok]
        if len(cands) == 1:
            e.heading, e.body_title = cands[0], cands[0].text.strip()


def missing_headings(doc: Doc) -> list[tuple[Para, TocEntry | None]]:
    """제목 서식(대응된 제목들의 문단·글자 모양)을 쓰고 번호가 붙었는데 목차에 없는 본문 문단.
    두 번째 값은 목차에서 그 앞에 올 항목(본문 순서상 바로 앞 제목)."""
    body = doc.paras[doc.body_start:]
    matched = {id(e.heading) for e in doc.toc if e.heading is not None}
    sigs = {e.heading.sig for e in doc.toc if e.heading is not None}
    pos = {id(p): i for i, p in enumerate(body)}
    out = []
    for i, p in enumerate(body):
        if id(p) in matched or not p.text.strip() or p.sig not in sigs or not token_of(p.text):
            continue
        prev = None
        for e in doc.toc:
            if e.heading is not None and pos[id(e.heading)] < i:
                prev = e
        out.append((p, prev))
    return out


# ----------------------------------------------------------------------------- PDF
@dataclass
class PdfPages:
    lines: list[list[str]]            # 쪽별 줄(위→아래), 원문 — 메모 칸의 글은 뺀 것
    normed: list[list[str]]
    printed_offset: int | None        # 인쇄 쪽번호 = 물리 쪽 + offset (없으면 None)
    margin: tuple[str, float] | None = None   # 메모 칸: ('right' | 'left', 경계 x)


def margin_cut(doc) -> tuple[str, float] | None:
    """메모를 함께 인쇄한 PDF 의 메모 칸 경계. Polaris 는 메모 칸을 쪽 높이 대부분에 걸친 세로선으로
    가르고 본문을 줄여 앉힌다(2026-09-29 기초연구 PDF: x = 417, 74쪽 모두). 절반 넘는 쪽에서 같은 자리(±2pt)에
    쪽 높이의 절반 넘게 이어지는 세로선이 있고 선 바깥쪽이 안쪽의 60 % 보다 좁을 때만 메모 칸으로 본다 —
    가운데 단 구분선(두 단 편집)은 양쪽 폭이 비슷해서 걸리지 않는다."""
    counts: dict[int, int] = {}
    for page in doc:
        h = page.rect.height
        xs = {round(d['rect'].x0) for d in page.get_drawings()
              if d['rect'].width <= 1.5 and d['rect'].height >= 0.5 * h}
        for x in xs:
            counts[x] = counts.get(x, 0) + 1
    if not counts:
        return None
    score = {x: sum(counts.get(x + d, 0) for d in range(-2, 3)) for x in counts}
    x, c = max(score.items(), key=lambda kv: (kv[1], -kv[0]))
    if c < max(2, (len(doc) + 1) // 2):
        return None
    w = doc[0].rect.width
    if x > w / 2 and w - x < 0.6 * x:
        return ('right', float(x))
    if x < w / 2 and x < 0.6 * (w - x):
        return ('left', float(x))
    return None


def _rows(items: list[tuple[float, float, float, str]]) -> list[list]:
    """(위, 왼쪽, 아래, 글) 조각을 같은 높이(±2pt)끼리 한 줄로 묶는다(목차의 제목과 쪽번호가 떨어져 있어도)."""
    rows = []
    for y, x, y2, txt in sorted(items):
        if rows and abs(rows[-1][0] - y) <= 2:
            rows[-1][1].append((x, txt))
        else:
            rows.append([y, [(x, txt)], y2])
    return rows


def read_pdf(path: Path) -> PdfPages:
    import fitz  # pymupdf
    doc = fitz.open(str(path))
    margin = margin_cut(doc)
    pages, votes = [], {}             # votes: offset → {물리 쪽: 그 숫자의 높이}
    for i, page in enumerate(doc):
        items, body = [], []
        for b in page.get_text('dict')['blocks']:
            for ln in b.get('lines', []):
                txt = ''.join(s['text'] for s in ln['spans'])
                if not txt.strip():
                    continue
                x0, y0, x1, y1 = ln['bbox']
                items.append((y0, x0, y1, txt))
                if not (margin and ((margin[0] == 'right' and x0 >= margin[1] - 1) or
                                    (margin[0] == 'left' and x1 <= margin[1] + 1))):
                    body.append((y0, x0, y1, txt))
        pages.append([' '.join(t for _, t in sorted(parts)).strip() for _, parts, _ in _rows(body)])
        # 쪽번호 후보: 줄 전체, 또는 같은 높이의 한 조각(“기관명 … 5”)이 숫자만인 것. 자리는 따지지 않는다 —
        # 메모 칸 때문에 본문이 줄어든 PDF 는 쪽번호가 쪽 높이의 79 % 에 온다.
        for y, parts, _ in _rows(items):
            cands = [' '.join(t for _, t in sorted(parts)).strip()] + [t.strip() for _, t in parts]
            m = next((m for m in map(PAGE_LABEL.fullmatch, cands) if m), None)
            if m:
                at = votes.setdefault(int(m.group(1)) - (i + 1), {})
                at[i] = max(at.get(i, y), y)
    # 절반 넘는 쪽에서 같은 높이(±6pt)에 ‘물리 쪽 + 같은 차이’ 숫자가 있어야 인쇄 쪽번호로 본다.
    # 목차 쪽번호·표 안 숫자는 쪽마다 차이가 달라 표가 모이지 않는다.
    printed = None
    if votes:
        off, at = max(votes.items(), key=lambda kv: (len(kv[1]), -abs(kv[0])))
        ys = sorted(at.values())
        mid = ys[len(ys) // 2]
        if sum(1 for y in ys if abs(y - mid) <= 6) >= max(2, len(pages) // 2):
            printed = off
    return PdfPages(pages, [[norm(x) for x in ln] for ln in pages], printed, margin)


def toc_pages(pdf: PdfPages, doc: Doc) -> list[int]:
    """PDF 의 목차 쪽: 목차 항목이 ‘제목 … 쪽번호’ 꼴로 3줄 이상 있는 쪽들 가운데 맨 앞의 연속 구간.
    본문 뒤쪽에 목차처럼 생긴 표가 있어도 제목 찾기 시작점을 그 뒤로 밀지 않는다."""
    titles = {norm(e.title) for e in doc.toc}
    found = []
    for i, lines in enumerate(pdf.lines):
        hits = 0
        for ln in lines:
            m = TOC_LINE.match(nfc(ln).strip())
            if m and norm(m.group('title')) in titles:
                hits += 1
        if hits >= 3:
            found.append(i)
    run = found[:1]
    for i in found[1:]:
        if i != run[-1] + 1:
            break
        run.append(i)
    return run


def line_match(normed: list[str], k: int, target: str) -> bool:
    ln = normed[k]
    if ln == target or (ln.startswith(target) and len(ln) - len(target) <= 3):
        return True
    if len(ln) >= 4 and target.startswith(ln):          # 긴 제목이 두세 줄로 넘어간 경우
        joined = ln + ''.join(normed[k + 1:k + 3])
        return joined.startswith(target) and len(target) > len(ln)
    return False


def locate(pdf: PdfPages, targets: list[str], start: int) -> list[int | None]:
    """목차 순서대로 각 제목의 물리 쪽(0부터)을 찾는다. 같은 쪽에 여러 제목이 있을 수 있다."""
    res, cur = [], start
    for t in targets:
        found = None
        for pg in range(cur, len(pdf.normed)):
            if any(line_match(pdf.normed[pg], k, t) for k in range(len(pdf.normed[pg]))):
                found = pg
                break
        res.append(found)
        if found is not None:
            cur = found
    return res


# ----------------------------------------------------------------------------- 쓰기
LINESEG = re.compile(r'<hp:linesegarray>.*?</hp:linesegarray>', re.S)
EMPTY_MEMO = re.compile(r'(<hp:fieldBegin [^>]*type="MEMO"[^>]*>(?:(?!</hp:fieldBegin>).)*?)<hp:subList/>(</hp:fieldBegin>)', re.S)


def set_page(par_xml: str, page: int) -> tuple[str, bool]:
    """마지막 탭 뒤의 첫 숫자를 바꾼다. 반환: (새 XML, 자릿수가 바뀌었는지)."""
    t = par_xml.rfind('<hp:tab')
    m = re.compile(r'>(\s*)(\d{1,4})(\s*)<').search(par_xml, t)
    if t < 0 or not m:
        raise ValueError('목차 문단에서 쪽번호 자리를 찾지 못했습니다')
    old = m.group(2)
    new = par_xml[:m.start(2)] + str(page) + par_xml[m.end(2):]
    return new, len(old) != len(str(page))


def _display_units(title: str) -> float:
    """제목의 대략적인 표시 폭(전각 = 1, 반각 = 0.55)."""
    return sum(1.0 if unicodedata.east_asian_width(ch) in 'WF' else 0.55 for ch in nfc(title))


def tab_width_model(entries: list['TocEntry']) -> dict[str, tuple[float, float]]:
    """문단모양별로 탭 폭 = a + b × 표시 폭 을 맞춘다(탭 폭은 오른쪽 정렬 탭까지 남은 거리라 제목이 길수록 준다)."""
    groups: dict[str, list[tuple[float, int]]] = {}
    for e in entries:
        m = re.search(r'<hp:tab width="(\d+)"', e.para.xml)
        if m:
            groups.setdefault(e.para.sig[0], []).append((_display_units(e.title), int(m.group(1))))
    model = {}
    for key, pts in groups.items():
        if len(pts) < 2:
            continue
        n = len(pts); mx = sum(x for x, _ in pts) / n; my = sum(y for _, y in pts) / n
        sxx = sum((x - mx) ** 2 for x, _ in pts)
        if sxx == 0:
            continue
        b = sum((x - mx) * (y - my) for x, y in pts) / sxx
        model[key] = (my - b * mx, b)
    return model


def set_tab_width(par_xml: str, title: str, para_key: str, model: dict) -> str:
    if para_key not in model:
        return par_xml
    a, b = model[para_key]
    w = max(1000, int(round(a + b * _display_units(title))))
    return re.sub(r'(<hp:tab width=")\d+(")', lambda m: f'{m.group(1)}{w}{m.group(2)}', par_xml, count=1)


def set_title(par_xml: str, title: str) -> str:
    m = re.search(r'(<hp:t>)([^<]*)(<hp:tab\b)', par_xml)
    if not m:
        raise ValueError('목차 제목이 한 글 조각 안에 있지 않아 바꿀 수 없습니다')
    esc = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return par_xml[:m.start(2)] + esc + par_xml[m.end(2):]


def fix_empty_memos(xml: str) -> tuple[str, int]:
    """빈 메모 subList 에 같은 문서의 정상 메모와 같은 속성 + 빈 문단 하나를 넣는다."""
    ok = re.search(r'<hp:fieldBegin [^>]*type="MEMO".*?(<hp:subList [^>]*>)<hp:p ([^>]*)><hp:run charPrIDRef="(\d+)"', xml, re.S)
    if ok:
        sub_open, p_attrs, charpr = ok.group(1), ok.group(2), ok.group(3)
    else:
        sub_open = ('<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" '
                    'linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">')
        p_attrs, charpr = 'id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"', '0'
    full = f'{sub_open}<hp:p {p_attrs}><hp:run charPrIDRef="{charpr}"/></hp:p></hp:subList>'
    return EMPTY_MEMO.subn(lambda m: m.group(1) + full + m.group(2), xml)


def write_hwpx(src: Path, dst: Path, sections: dict[str, str]) -> None:
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, 'w') as zout:
        for info in zin.infolist():
            data = sections[info.filename].encode('utf-8') if info.filename in sections else zin.read(info.filename)
            ctype = zipfile.ZIP_STORED if info.filename == 'mimetype' else zipfile.ZIP_DEFLATED
            zout.writestr(info.filename, data, compress_type=ctype)


def verify_untouched(doc: Doc, out: Path, n_inserted: int, fix_memos: bool) -> None:
    """저장한 파일을 다시 읽어, 목차 구간 밖의 최상위 문단이 원본과 바이트 단위로 같은지 본다."""
    after = load_hwpx(out)
    toc_keys = {(e.para.section, e.para.index) for e in doc.toc}
    first = doc.toc[0].para
    last = doc.toc[-1].para
    def outside(paras, toc_len):
        out_list, in_block = [], False
        seen = 0
        for p in paras:
            if (p.section, p.index) == (first.section, first.index):
                in_block = True
            if in_block and seen < toc_len:
                if p.text.strip():
                    seen += 1
                continue
            in_block = False
            out_list.append(p.xml)
        return out_list
    before = outside(doc.paras, len(doc.toc))
    if fix_memos:
        before = [fix_empty_memos(x)[0] for x in before]
    got = outside(after.paras, len(doc.toc) + n_inserted)
    if before != got:
        diff = next(i for i, (x, y) in enumerate(zip(before, got)) if x != y) if len(before) == len(got) else None
        raise AssertionError(f'목차 밖 문단이 바뀌었습니다(첫 차이 위치 {diff}, 문단 수 {len(before)} → {len(got)})')


# ----------------------------------------------------------------------------- 실행
def run(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='HWPX 목차 쪽번호를 PDF 의 실제 쪽과 맞춘다.')
    ap.add_argument('hwpx', type=Path)
    ap.add_argument('--pdf', type=Path, required=True, help='같은 문서를 Polaris/한글에서 내보낸 PDF')
    ap.add_argument('-o', '--output', type=Path, help=f'출력 파일(기본: <입력>{OUT_SUFFIX}.hwpx)')
    ap.add_argument('--check', action='store_true', help='검사만 하고 파일을 쓰지 않는다(어긋나면 종료 코드 1)')
    ap.add_argument('--sync-titles', action='store_true', help='본문에서 문구가 바뀐 제목을 목차에 반영')
    ap.add_argument('--add-missing', action='store_true', help='목차에 없는 본문 제목을 목차에 추가')
    ap.add_argument('--physical', action='store_true', help='PDF 의 인쇄 쪽번호 대신 물리 쪽(표지 = 1)을 쓴다')
    ap.add_argument('--fix-empty-memos', action='store_true', help='본문이 빈 메모(HWP 변환을 멈추게 함)를 고친다')
    ap.add_argument('--force', action='store_true', help='출력 파일이 이미 있으면 덮어쓴다')
    a = ap.parse_args(argv)

    doc = load_hwpx(a.hwpx)
    find_toc(doc)
    match_headings(doc)
    missing = missing_headings(doc)
    pdf = read_pdf(a.pdf)
    offset = 0 if (a.physical or pdf.printed_offset is None) else pdf.printed_offset
    tp = toc_pages(pdf, doc)
    start = (max(tp) + 1) if tp else 0
    targets = [norm(e.body_title or (e.heading.text if e.heading else e.title)) for e in doc.toc]
    for e, pg in zip(doc.toc, locate(pdf, targets, start)):
        e.actual = None if pg is None else pg + 1 + offset
    miss_pages = []
    if missing:
        cur_pages = {id(e): e.actual for e in doc.toc}
        for p, prev in missing:
            base = cur_pages.get(id(prev)) if prev else None
            s = max(start, (base - 1 - offset)) if base else start
            pg = locate(pdf, [norm(p.text)], s)[0]
            miss_pages.append(None if pg is None else pg + 1 + offset)

    # --- 보고
    if a.physical or pdf.printed_offset is None:
        basis = '물리 쪽(표지 = 1)'
    else:
        basis = 'PDF 인쇄 쪽번호' + (f'(물리 쪽 {offset:+d})' if offset else '')
    memo = f' · 메모 칸 제외({"x ≥" if pdf.margin[0] == "right" else "x ≤"} {pdf.margin[1]:g})' if pdf.margin else ''
    print(f'목차 {len(doc.toc)}개 · PDF {len(pdf.lines)}쪽 · 목차 쪽 {[i + 1 for i in tp] or "못 찾음"} · 쪽 기준: {basis}{memo}')
    if not tp:
        print('  [경고] PDF 에서 목차 쪽을 찾지 못해 1쪽부터 제목을 찾았습니다 — 목차 줄을 본문 제목으로 읽었을 수 있으니 결과를 확인하세요.')
    diffs = [e for e in doc.toc if e.actual is not None and e.actual != e.page]
    notfound = [e for e in doc.toc if e.actual is None]
    retitle = [e for e in doc.toc if e.body_title]
    unmatched = [e for e in doc.toc if e.heading is None]
    for e in diffs:
        print(f'  쪽 {e.page:>3} → {e.actual:>3}  {e.title}')
    for e in notfound:
        print(f'  [PDF 에서 못 찾음] {e.title} (목차 {e.page}쪽, 그대로 둠)')
    for e in unmatched:
        print(f'  [본문 제목 없음] {e.title}')
    for e in retitle:
        print(f'  [문구 다름] 목차 “{e.title}” ↔ 본문 “{e.body_title}”')
    for (p, prev), pg in zip(missing, miss_pages):
        print(f'  [목차에 없음] {p.text.strip()} ({pg}쪽) — 앞 항목: {prev.title if prev else "(맨 앞)"}')
    shown = any(re.search(r'<hp:pageNum [^>]*pos="(?!NONE")', x) for x in doc.sections.values())
    if not shown:
        print('  [경고] 문서에 보이는 쪽번호(쪽 번호 매기기)가 없습니다 — 인쇄본에서 목차 숫자로 쪽을 찾을 수 없습니다.')
    empty = sum(len(EMPTY_MEMO.findall(x)) for x in doc.sections.values())
    if empty:
        print(f'  [경고] 본문이 빈 메모 {empty}개 — Polaris 의 HWP 변환이 멈춥니다. --fix-empty-memos 로 고칠 수 있습니다.')
    print(f'일치 {len(doc.toc) - len(diffs) - len(notfound)} · 쪽 다름 {len(diffs)} · PDF 미발견 {len(notfound)} · '
          f'문구 다름 {len(retitle)} · 본문 없음 {len(unmatched)} · 목차에 없음 {len(missing)}')

    if a.check:
        return 1 if (diffs or notfound or retitle or unmatched or missing or empty) else 0

    # --- 쓰기
    out = a.output or a.hwpx.with_name(a.hwpx.stem + OUT_SUFFIX + '.hwpx')
    if out.resolve() == a.hwpx.resolve():
        print('입력 파일은 덮어쓰지 않습니다. -o 로 다른 이름을 주세요.', file=sys.stderr)
        return 2
    if out.exists() and not a.force:
        print(f'{out} 가 이미 있습니다. 덮어쓰려면 --force', file=sys.stderr)
        return 2
    new_xml: dict[int, str] = {}      # id(Para) → 새 XML
    widths = tab_width_model(doc.toc)
    for e in doc.toc:
        x = e.para.xml
        relayout = False
        if e.actual is not None and e.actual != e.page:
            x, changed = set_page(x, e.actual)
            relayout |= changed
        if a.sync_titles and e.body_title:
            x = set_tab_width(set_title(x, e.body_title), e.body_title, e.para.sig[0], widths)
            relayout = True
        if relayout:
            x = LINESEG.sub('', x)    # 줄 수·폭이 바뀌면 옛 줄 배치 캐시를 버린다(프로그램이 다시 배치)
        if x != e.para.xml:
            new_xml[id(e.para)] = x
    inserts: dict[int, list[str]] = {}
    added = 0
    if a.add_missing:
        templates = {}
        for e in doc.toc:
            templates.setdefault(e.level, e)
        for (p, prev), pg in zip(missing, miss_pages):
            lvl = level_of(p.text)
            tpl = templates.get(lvl)
            anchor = prev.para if prev else doc.toc[0].para
            if tpl is None or pg is None:
                print(f'  [추가 못 함] {p.text.strip()} — {"같은 수준의 목차 서식 없음" if tpl is None else "PDF 에서 쪽을 못 찾음"}')
                continue
            x = LINESEG.sub('', set_title(tpl.para.xml, p.text.strip()))
            x = set_tab_width(x, p.text.strip(), tpl.para.sig[0], widths)
            x, _ = set_page(x, pg)
            key = id(anchor) if prev else -1
            inserts.setdefault(key, []).append(x)
            added += 1
    sections = dict(doc.sections)
    fixed_memos = 0
    for name, xml in doc.sections.items():
        parts, last = [], 0
        sec_paras = [p for p in doc.paras if p.section == name]
        for p, (a0, b0) in zip(sec_paras, doc.spans[name]):
            parts.append(xml[last:a0])
            if -1 in inserts and p is doc.toc[0].para:
                parts.append(''.join(inserts[-1]))      # 목차 맨 앞에 올 항목
            parts.append(new_xml.get(id(p), p.xml))
            parts.append(''.join(inserts.get(id(p), [])))
            last = b0
        parts.append(xml[last:])
        out_xml = ''.join(parts)
        if a.fix_empty_memos:
            out_xml, n = fix_empty_memos(out_xml)
            fixed_memos += n
        ET.fromstring(out_xml.encode('utf-8'))
        sections[name] = out_xml
    write_hwpx(a.hwpx, out, sections)
    verify_untouched(doc, out, n_inserted=added, fix_memos=a.fix_empty_memos)
    print(f'저장: {out}  (쪽번호 {sum(1 for e in doc.toc if e.actual is not None and e.actual != e.page)}개'
          f'{", 제목 %d개" % len(retitle) if a.sync_titles and retitle else ""}'
          f'{", 항목 추가 %d개" % added if added else ""}'
          f'{", 빈 메모 %d개 수정" % fixed_memos if fixed_memos else ""})')
    print('확인: 저장한 파일을 다시 PDF 로 내보내 --check 를 돌리면 일치 여부를 볼 수 있습니다.')
    return 0


if __name__ == '__main__':
    sys.exit(run())
