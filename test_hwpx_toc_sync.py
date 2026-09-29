"""hwpx_toc_sync.py 시험 — python3.13 -m unittest test_hwpx_toc_sync

pymupdf(fitz) 가 있는 인터프리터가 필요하다. 개인 자료(data/, ~/Downloads)는 읽지 않는다 —
HWPX 는 최소 패키지를, PDF 는 fitz 로 이 파일 안에서 만든다.
"""
from __future__ import annotations

import io
import re
import shutil
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

import fitz

import hwpx_toc_sync as TS

NS = ('xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
      'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"')
LS = '<hp:linesegarray><hp:lineseg textpos="0" vertpos="0" vertsize="1000" textheight="1000" baseline="850" spacing="600" horzpos="0" horzsize="42520" flags="393216"/></hp:linesegarray>'

# 목차 수준별 서식(문단모양, 글자모양) — 실제 보고서와 같은 모양의 번호
TOC_STYLE = {'제N장': ('15', '8'), 'N.': ('16', '10'), 'N)': ('17', '11')}
HEAD_STYLE = {'제N장': ('20', '13'), 'N.': ('21', '7'), 'N)': ('53', '35')}


def P(text, para='0', char='0', page_break=False, ls=True):
    pb = '1' if page_break else '0'
    return (f'<hp:p id="0" paraPrIDRef="{para}" styleIDRef="0" pageBreak="{pb}" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{char}"><hp:t>{text}</hp:t></hp:run>{LS if ls else ""}</hp:p>')


def TOC(title, page, level):
    para, char = TOC_STYLE[level]
    return (f'<hp:p id="0" paraPrIDRef="{para}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{char}"><hp:t>{title}<hp:tab width="30000" leader="0" type="1"/>{page}</hp:t></hp:run>{LS}</hp:p>')


def H(title, level, page_break=False):
    para, char = HEAD_STYLE[level]
    return P(title, para, char, page_break)


MEMO_EMPTY = ('<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="0">'
              '<hp:ctrl><hp:fieldBegin id="7" type="MEMO" name="" editable="0" dirty="1" zorder="1" fieldid="623209829">'
              '<hp:parameters cnt="2" name=""><hp:integerParam name="Prop">0</hp:integerParam>'
              '<hp:stringParam name="Command">MEMO/65535/1/1/1/검토자/\\;;</hp:stringParam></hp:parameters>'
              '<hp:subList/></hp:fieldBegin></hp:ctrl></hp:run><hp:run charPrIDRef="0"><hp:t>메모가 걸린 글</hp:t></hp:run>'
              '<hp:run charPrIDRef="0"><hp:ctrl><hp:fieldEnd beginIDRef="7" fieldid="623209829"/></hp:ctrl></hp:run></hp:p>')


def make_hwpx(path: Path, paras: list[str]) -> None:
    sec = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><hs:sec {NS}>' + ''.join(paras) + '</hs:sec>'
    hpf = ('<?xml version="1.0" encoding="UTF-8"?><opf:package xmlns:opf="http://www.idpf.org/2007/opf/"><opf:manifest>'
           '<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>'
           '<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/></opf:manifest>'
           '<opf:spine><opf:itemref idref="header"/><opf:itemref idref="section0" linear="yes"/></opf:spine></opf:package>')
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('mimetype', 'application/hwp+zip', compress_type=zipfile.ZIP_STORED)
        z.writestr('version.xml', '<?xml version="1.0"?><hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version"/>')
        z.writestr('Contents/header.xml', '<?xml version="1.0"?><hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"/>')
        z.writestr('Contents/section0.xml', sec)
        z.writestr('Contents/content.hpf', hpf)


def make_pdf(path: Path, pages: list[list[tuple[str, str | None]]], footer: dict[int, str | tuple[str, str]] | None = None,
             right_x: float = 520, footer_at: tuple[float, float] = (290, 810), rule_x: float | None = None,
             notes: dict[int, list[tuple[float, str]]] | None = None) -> None:
    """pages: 쪽마다 [(왼쪽 글, 오른쪽 글 또는 None)] — 오른쪽 글은 같은 높이 right_x(목차 쪽번호 자리). 줄 높이는 24pt, 첫 줄 80.
    footer: 쪽번호(1부터) → 바닥글(footer_at). (왼쪽 글, 오른쪽 글) 이면 같은 높이 양 끝에 따로 쓴다.
    rule_x: 모든 쪽에 쪽 높이 대부분에 걸친 세로선(Polaris 가 메모 칸을 가르는 선). notes: 쪽 → [(높이, 글)] 을 선 오른쪽에."""
    doc = fitz.open()
    for n, lines in enumerate(pages, start=1):
        pg = doc.new_page(width=595, height=842)
        y = 80
        for left, right in lines:
            pg.insert_text((60, y), left, fontname='korea', fontsize=12)
            if right is not None:
                pg.insert_text((right_x, y), right, fontname='korea', fontsize=12)
            y += 24
        if footer and n in footer:
            if isinstance(footer[n], tuple):
                pg.insert_text((60, footer_at[1]), footer[n][0], fontname='korea', fontsize=10)
                pg.insert_text((500, footer_at[1]), footer[n][1], fontname='korea', fontsize=10)
            else:
                pg.insert_text(footer_at, footer[n], fontname='korea', fontsize=10)
        if rule_x is not None:
            pg.draw_line((rule_x, 60), (rule_x, 780))
            for ny, text in (notes or {}).get(n, []):
                pg.insert_text((rule_x + 5, ny), text, fontname='korea', fontsize=12)
    doc.save(str(path))


# 기본 문서: 표지 1쪽, 목차 2쪽, 본문 3쪽부터. 목차 숫자는 일부러 틀리게 둔다.
def base_paras(toc_pages=(3, 3, 3, 4, 5)):
    a, b, c, d, e = toc_pages
    return [
        P('반도체 교과서 기초연구'),
        TOC('제1장 서론', a, '제N장'), TOC('1. 연구 배경', b, 'N.'), TOC('1) 주요 사건', c, 'N)'),
        P('', ls=False),
        TOC('2. 연구 필요성', d, 'N.'), TOC('제2장 연구 방법', e, '제N장'),
        H('제1장 서론', '제N장', page_break=True), H('1. 연구 배경', 'N.'), H('1) 주요 사건', 'N)'),
        P('본문 한 단락입니다.'),
        H('2. 연구 필요성', 'N.'),
        P('또 다른 단락입니다.'),
        H('제2장 연구 방법', '제N장', page_break=True),
        P('방법 단락입니다.'),
    ]


# 실제 배치: 서론·배경·주요 사건 3쪽, 필요성 5쪽, 연구 방법 6쪽
def base_pdf_pages(extra_body=None):
    toc = [('제1장 서론', '3'), ('1. 연구 배경', '3'), ('1) 주요 사건', '3'), ('2. 연구 필요성', '4'), ('제2장 연구 방법', '5')]
    return [
        [('반도체 교과서 기초연구', None)],
        toc,
        [('제1장 서론', None), ('1. 연구 배경', None), ('1) 주요 사건', None), ('본문 한 단락입니다.', None)],
        extra_body or [('앞 장이 이어지는 쪽입니다.', None)],
        [('2. 연구 필요성', None), ('또 다른 단락입니다.', None)],
        [('제2장 연구 방법', None), ('방법 단락입니다.', None)],
    ]


def quiet(fn, *args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = fn(*args)
    return rc, out.getvalue(), err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.hwpx = self.tmp / '문서.hwpx'
        self.pdf = self.tmp / '문서.pdf'

    def toc_pages_of(self, path):
        d = TS.load_hwpx(path)
        TS.find_toc(d)
        return [(e.title, e.page) for e in d.toc]


class DetectTests(Base):
    def test_finds_toc_block_across_blank_paragraph_and_matches_headings(self):
        make_hwpx(self.hwpx, base_paras())
        d = TS.load_hwpx(self.hwpx)
        TS.find_toc(d)
        TS.match_headings(d)
        self.assertEqual([e.title for e in d.toc], ['제1장 서론', '1. 연구 배경', '1) 주요 사건', '2. 연구 필요성', '제2장 연구 방법'])
        self.assertEqual([e.level for e in d.toc], ['제N장', 'N.', 'N)', 'N.', '제N장'])
        self.assertTrue(all(e.heading is not None for e in d.toc))
        self.assertEqual(d.paras[d.body_start].text, '제1장 서론')

    def test_no_toc_is_an_error(self):
        make_hwpx(self.hwpx, [P('표지'), P('본문')])
        d = TS.load_hwpx(self.hwpx)
        with self.assertRaises(ValueError):
            TS.find_toc(d)

    def test_level_and_token(self):
        self.assertEqual(TS.level_of('제3장. 반도체'), '제N장.')
        self.assertEqual(TS.level_of('제3장 연구 결과'), '제N장')
        self.assertEqual(TS.level_of('(2) 제조 분야'), '(N)')
        self.assertEqual(TS.level_of('가. 교육목표'), '가.')
        self.assertIsNone(TS.level_of('본문'))
        self.assertEqual(TS.token_of('제 3 장. 반도체'), '제3장.')
        self.assertEqual(TS.token_of('12. 결론'), '12.')


class PdfTests(Base):
    def test_reads_lines_merges_same_row_and_detects_printed_numbers(self):
        make_pdf(self.pdf, base_pdf_pages(), footer={n: str(n) for n in range(2, 7)})
        pdf = TS.read_pdf(self.pdf)
        self.assertEqual(len(pdf.lines), 6)
        self.assertIn('제1장 서론 3', pdf.lines[1])                 # 목차 제목과 오른쪽 쪽번호가 한 줄로
        self.assertEqual(pdf.printed_offset, 0)

    def test_printed_offset_when_numbering_starts_later(self):
        make_pdf(self.pdf, base_pdf_pages(), footer={n: f'- {n - 2} -' for n in range(3, 7)})   # 본문 첫 쪽이 1
        self.assertEqual(TS.read_pdf(self.pdf).printed_offset, -2)

    def test_no_printed_numbers(self):
        make_pdf(self.pdf, base_pdf_pages())
        self.assertIsNone(TS.read_pdf(self.pdf).printed_offset)

    def test_printed_number_beside_footer_text(self):
        make_pdf(self.pdf, base_pdf_pages(), footer={n: ('반도체 기초연구보고서', str(n - 2)) for n in range(3, 7)})
        self.assertEqual(TS.read_pdf(self.pdf).printed_offset, -2)

    def test_margin_cut_finds_memo_column_but_not_a_centre_rule(self):
        make_pdf(self.pdf, base_pdf_pages(), rule_x=417)
        self.assertEqual(TS.margin_cut(fitz.open(str(self.pdf))), ('right', 417.0))
        make_pdf(self.pdf, base_pdf_pages(), rule_x=297)                                # 두 단 편집의 가운데 선
        self.assertIsNone(TS.margin_cut(fitz.open(str(self.pdf))))
        make_pdf(self.pdf, base_pdf_pages())
        self.assertIsNone(TS.margin_cut(fitz.open(str(self.pdf))))

    def test_line_match_handles_wrapped_heading_and_ignores_running_text(self):
        n = [TS.norm(x) for x in ['(5) 반도체 관련 주요 훈련 내용(Topics Covered', 'in the OSHA Training)', '다음 줄']]
        self.assertTrue(TS.line_match(n, 0, TS.norm('(5) 반도체 관련 주요 훈련 내용(Topics Covered in the OSHA Training)')))
        m = [TS.norm('이 절은 1) 주요 사건 을 다룬다')]
        self.assertFalse(TS.line_match(m, 0, TS.norm('1) 주요 사건')))


class RunTests(Base):
    def test_check_reports_mismatches_and_writes_nothing(self):
        make_hwpx(self.hwpx, base_paras())
        make_pdf(self.pdf, base_pdf_pages())
        rc, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--check'])
        self.assertEqual(rc, 1)
        self.assertIn('쪽   4 →   5  2. 연구 필요성', out)
        self.assertIn('쪽   5 →   6  제2장 연구 방법', out)
        self.assertFalse((self.tmp / '문서_목차연동.hwpx').exists())

    def test_check_passes_when_in_sync(self):
        make_hwpx(self.hwpx, base_paras((3, 3, 3, 5, 6)))
        make_pdf(self.pdf, base_pdf_pages())
        rc, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--check'])
        self.assertEqual(rc, 0, out)

    def test_sync_updates_pages_and_leaves_everything_else(self):
        make_hwpx(self.hwpx, base_paras())
        make_pdf(self.pdf, base_pdf_pages())
        rc, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf)])
        self.assertEqual(rc, 0, out)
        dst = self.tmp / '문서_목차연동.hwpx'
        self.assertEqual(self.toc_pages_of(dst), [('제1장 서론', 3), ('1. 연구 배경', 3), ('1) 주요 사건', 3), ('2. 연구 필요성', 5), ('제2장 연구 방법', 6)])
        a, b = TS.load_hwpx(self.hwpx), TS.load_hwpx(dst)
        changed = [i for i, (x, y) in enumerate(zip(a.paras, b.paras)) if x.xml != y.xml]
        self.assertEqual(changed, [5, 6])                                            # 목차 두 문단만
        self.assertIn('<hp:linesegarray>', b.paras[5].xml)                            # 자릿수 같으면 캐시 유지
        with zipfile.ZipFile(self.hwpx) as z1, zipfile.ZipFile(dst) as z2:
            self.assertEqual(z1.namelist(), z2.namelist())
            self.assertEqual(z2.getinfo('mimetype').compress_type, zipfile.ZIP_STORED)
            self.assertEqual(z1.read('Contents/header.xml'), z2.read('Contents/header.xml'))

    def test_digit_count_change_drops_line_layout_cache(self):
        paras = base_paras()
        paras[5] = TOC('2. 연구 필요성', 44, 'N.')                                    # 두 자리 → 한 자리
        make_hwpx(self.hwpx, paras)
        make_pdf(self.pdf, base_pdf_pages())
        quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf)])
        b = TS.load_hwpx(self.tmp / '문서_목차연동.hwpx')
        self.assertTrue(b.paras[5].text.endswith('\t5'))
        self.assertNotIn('<hp:linesegarray>', b.paras[5].xml)

    def test_printed_page_numbers_are_used_and_physical_flag_overrides(self):
        make_hwpx(self.hwpx, base_paras())
        make_pdf(self.pdf, base_pdf_pages(), footer={n: str(n - 2) for n in range(3, 7)})
        quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf)])
        self.assertEqual([p for _, p in self.toc_pages_of(self.tmp / '문서_목차연동.hwpx')], [1, 1, 1, 3, 4])
        quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--physical', '-o', str(self.tmp / 'p.hwpx')])
        self.assertEqual([p for _, p in self.toc_pages_of(self.tmp / 'p.hwpx')], [3, 3, 3, 5, 6])

    def test_toc_page_with_leaders_and_toc_like_body_table(self):
        make_hwpx(self.hwpx, base_paras())
        pages = base_pdf_pages(extra_body=[('제1장 서론', '9'), ('1. 연구 배경', '9'), ('1) 주요 사건', '9')])  # 본문 속 목차 같은 표
        pages[1] = [('제1장 서론·········3', None), ('1. 연구 배경 ……… 3', None), ('1) 주요 사건 ───── 3', None),
                    ('2. 연구 필요성 _____ 4', None), ('제2장 연구 방법 ‥‥‥ 5', None)]          # 점선이 붙은 목차 줄
        make_pdf(self.pdf, pages)
        d = TS.load_hwpx(self.hwpx)
        TS.find_toc(d)
        self.assertEqual(TS.toc_pages(TS.read_pdf(self.pdf), d), [1])
        rc, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--check'])
        self.assertEqual(rc, 1)
        self.assertIn('쪽   4 →   5  2. 연구 필요성', out)
        self.assertIn('일치 3 · 쪽 다름 2 · PDF 미발견 0', out)

    def test_memo_column_text_does_not_break_headings(self):
        # 메모를 함께 인쇄한 Polaris PDF: 본문이 줄어 쪽번호가 쪽 높이의 79 % 에 오고, 긴 제목 첫 줄과 같은 높이·
        # 제목 두 줄 사이에 메모 글이 끼어 있다(2026-09-29 기초연구 PDF 49쪽).
        title = '1) 주요 사건과 공장 안전 교육 과정'
        paras = base_paras((3, 3, 3, 5, 6))
        paras[3], paras[9] = TOC(title, 3, 'N)'), H(title, 'N)')
        make_hwpx(self.hwpx, paras)
        pages = base_pdf_pages()
        pages[1][2] = (title, '3')
        pages[2] = [('제1장 서론', None), ('1. 연구 배경', None), ('1) 주요 사건과 공장', None), ('안전 교육 과정', None),
                    ('본문 한 단락입니다.', None)]
        make_pdf(self.pdf, pages, footer={n: str(n) for n in range(2, 7)}, right_x=380, footer_at=(206, 669),
                 rule_x=417, notes={3: [(129.5, '앞 절과 제목이 같습니다'), (140, '확인 바랍니다')]})
        pdf = TS.read_pdf(self.pdf)
        self.assertEqual(pdf.printed_offset, 0)
        rc, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--check'])
        self.assertEqual(rc, 0, out)
        self.assertIn('쪽 기준: PDF 인쇄 쪽번호 · 메모 칸 제외(x ≥ 417)', out)
        self.assertIn('일치 5 · 쪽 다름 0 · PDF 미발견 0', out)
        with mock.patch.object(TS, 'margin_cut', return_value=None):                  # 메모 칸을 모르면 제목을 놓친다
            rc, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--check'])
        self.assertEqual(rc, 1)
        self.assertIn(f'[PDF 에서 못 찾음] {title}', out)

    def test_warns_when_pdf_has_no_toc_page(self):
        make_hwpx(self.hwpx, base_paras())
        pages = base_pdf_pages()
        pages[1] = [('차례는 따로 인쇄했습니다.', None)]
        make_pdf(self.pdf, pages)
        _, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--check'])
        self.assertIn('목차 쪽을 찾지 못해', out)
        self.assertIn('쪽   5 →   6  제2장 연구 방법', out)

    def test_heading_missing_in_pdf_is_reported_and_kept(self):
        make_hwpx(self.hwpx, base_paras())
        pages = base_pdf_pages()
        pages[4] = [('또 다른 단락입니다.', None)]                                     # 2. 연구 필요성 이 PDF 에 없음
        make_pdf(self.pdf, pages)
        rc, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf)])
        self.assertEqual(rc, 0)
        self.assertIn('[PDF 에서 못 찾음] 2. 연구 필요성', out)
        self.assertEqual(dict(self.toc_pages_of(self.tmp / '문서_목차연동.hwpx'))['2. 연구 필요성'], 4)

    def test_sync_titles_uses_the_changed_body_heading(self):
        paras = base_paras()
        paras[11] = H('2. 연구의 필요성과 범위', 'N.')                                  # 본문 제목 문구가 바뀜
        make_hwpx(self.hwpx, paras)
        pages = base_pdf_pages()
        pages[4] = [('2. 연구의 필요성과 범위', None)]
        make_pdf(self.pdf, pages)
        rc, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--check'])
        self.assertIn('[문구 다름] 목차 “2. 연구 필요성” ↔ 본문 “2. 연구의 필요성과 범위”', out)
        quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--sync-titles'])
        self.assertIn(('2. 연구의 필요성과 범위', 5), self.toc_pages_of(self.tmp / '문서_목차연동.hwpx'))

    def test_add_missing_inserts_with_same_level_template(self):
        paras = base_paras()
        paras.insert(12, H('2) 추가된 절', 'N)'))                                     # 목차에 없는 본문 제목
        make_hwpx(self.hwpx, paras)
        pages = base_pdf_pages()
        pages[4] = [('2. 연구 필요성', None), ('또 다른 단락입니다.', None), ('2) 추가된 절', None)]
        make_pdf(self.pdf, pages)
        rc, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--add-missing'])
        self.assertEqual(rc, 0, out)
        self.assertIn('[목차에 없음] 2) 추가된 절 (5쪽) — 앞 항목: 2. 연구 필요성', out)
        dst = self.tmp / '문서_목차연동.hwpx'
        self.assertEqual(self.toc_pages_of(dst)[4:], [('2) 추가된 절', 5), ('제2장 연구 방법', 6)])
        b = TS.load_hwpx(dst)
        new = next(p for p in b.paras if p.text.startswith('2) 추가된 절'))
        self.assertEqual(new.sig, TOC_STYLE['N)'])
        self.assertNotIn('<hp:linesegarray>', new.xml)

    def test_tab_width_is_estimated_from_same_level_entries(self):
        make_hwpx(self.hwpx, [P('표지'), TOC('1) 짧은 제목', 3, 'N)').replace('width="30000"', 'width="36000"'),
                              TOC('2) 훨씬 더 길게 늘어난 제목입니다', 3, 'N)').replace('width="30000"', 'width="24000"'),
                              TOC('3) 가운데 길이 제목', 3, 'N)').replace('width="30000"', 'width="31000"')])
        d = TS.load_hwpx(self.hwpx)
        TS.find_toc(d)
        model = TS.tab_width_model(d.toc)
        short = TS.set_tab_width(d.toc[0].para.xml, '4) 짧다', '17', model)
        long_ = TS.set_tab_width(d.toc[0].para.xml, '4) 아주 아주 아주 긴 제목이 들어가서 폭이 줄어듭니다', '17', model)
        w = lambda x: int(re.search(r'<hp:tab width="(\d+)"', x).group(1))
        self.assertGreater(w(short), w(long_))
        self.assertGreater(w(short), 36000 - 1)                                        # 가장 짧은 항목보다 짧으면 폭이 더 크다

    def test_refuses_to_overwrite_input_or_existing_output(self):
        make_hwpx(self.hwpx, base_paras())
        make_pdf(self.pdf, base_pdf_pages())
        rc, _, err = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '-o', str(self.hwpx)])
        self.assertEqual(rc, 2)
        self.assertIn('덮어쓰지 않습니다', err)
        dst = self.tmp / '문서_목차연동.hwpx'
        dst.write_bytes(b'x')
        rc, _, err = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf)])
        self.assertEqual(rc, 2)
        self.assertEqual(dst.read_bytes(), b'x')
        rc, _, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--force'])
        self.assertEqual(rc, 0)

    def test_warns_when_document_has_no_visible_page_numbers(self):
        make_hwpx(self.hwpx, base_paras((3, 3, 3, 5, 6)))
        make_pdf(self.pdf, base_pdf_pages())
        _, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--check'])
        self.assertIn('보이는 쪽번호', out)
        paras = base_paras((3, 3, 3, 5, 6))
        paras[1] = paras[1].replace('<hp:run charPrIDRef="8">', '<hp:run charPrIDRef="8"><hp:ctrl><hp:pageNum pos="BOTTOM_CENTER" formatType="DIGIT" sideChar=""/></hp:ctrl>', 1)
        make_hwpx(self.hwpx, paras)
        _, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--check'])
        self.assertNotIn('보이는 쪽번호', out)

    def test_empty_memo_is_warned_and_fixed_on_request(self):
        paras = base_paras((3, 3, 3, 5, 6))
        paras.insert(10, MEMO_EMPTY)
        make_hwpx(self.hwpx, paras)
        make_pdf(self.pdf, base_pdf_pages())
        rc, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--check'])
        self.assertEqual(rc, 1)                                                      # 목차는 맞지만 HWP 변환을 멈출 결함
        self.assertIn('본문이 빈 메모 1개', out)
        rc, out, _ = quiet(TS.run, [str(self.hwpx), '--pdf', str(self.pdf), '--fix-empty-memos'])
        self.assertEqual(rc, 0, out)
        with zipfile.ZipFile(self.tmp / '문서_목차연동.hwpx') as z:
            sec = z.read('Contents/section0.xml').decode()
        self.assertNotIn('<hp:subList/>', sec)
        self.assertIn('<hp:run charPrIDRef="0"/></hp:p></hp:subList></hp:fieldBegin>', sec)


if __name__ == '__main__':
    unittest.main()
