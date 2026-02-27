# xu_ly_toan.py - Chuyển đổi OMML (Office Math) sang LaTeX
#
# Pipeline ưu tiên:
#   1. XSLT (OMML → MathML → LaTeX)   – chính xác nhất
#   2. Pandoc subprocess                – fallback mạnh
#   3. Parser thủ công (đệ quy)        – fallback cuối
#
# Cách dùng:
#   bo_toan = BoXuLyToan()                       # tự tìm OMML2MML.XSL
#   bo_toan = BoXuLyToan(duong_dan_xslt=r"...")   # chỉ định đường dẫn
#   latex   = bo_toan.omml_element_to_latex(omath_element)

import os
import re
import subprocess
import tempfile
from copy import deepcopy
from lxml import etree

from utils import loc_ky_tu

from config import (
    OMML_NAMESPACE, W_NAMESPACE,
    OMML_CHAR_MAP, NARY_SYMBOL_MAP, DELIMITER_MAP,
    ACCENT_MAP, FUNC_NAME_MAP,
    DEFAULT_OMML2MML_XSL,
)

# Namespace map dùng cho XSLT wrapper
_OMML_NSMAP = {
    'm': OMML_NAMESPACE,
    'w': W_NAMESPACE,
}

class BoXuLyToan:
    # Bộ xử lý toán: chuyển OMML XML element → LaTeX string

    def __init__(self, duong_dan_xslt: str = None):
        self._xslt_transform = None
        self._mathml_to_latex_fn = None
        self._co_pandoc = None  # lazy-check

        # 1. Khởi tạo XSLT transform
        xslt_path = duong_dan_xslt or DEFAULT_OMML2MML_XSL
        self._init_xslt(xslt_path)

        # 2. Khởi tạo MathML → LaTeX converter
        self._init_mathml_converter()

    # KHỞI TẠO

    def _init_xslt(self, xslt_path: str | None):
        if not xslt_path or not os.path.exists(xslt_path):
            return
        try:
            xslt_doc = etree.parse(xslt_path)
            self._xslt_transform = etree.XSLT(xslt_doc)
        except Exception as e:
            print(f'[Cảnh báo] Lỗi im lặng ở xu_ly_toan.py dòng 58: {e}')
            self._xslt_transform = None

    def _init_mathml_converter(self):
        # Tìm thư viện MathML→LaTeX có sẵn trong môi trường
        # latex2mathml (có hàm ngược mathml→latex ở phiên bản mới)
        try:
            from latex2mathml.converter import convert as _l2m  # noqa: F401
            # Thử hàm ngược
            from latex2mathml import mathml2latex as _m2l
            self._mathml_to_latex_fn = _m2l
            return
        except Exception as e:
            print(f'[Cảnh báo] Lỗi im lặng ở xu_ly_toan.py dòng 70: {e}')
            pass
        # Fallback: tự parse đơn giản qua _mathml_simple_to_latex
        self._mathml_to_latex_fn = None

    def _kiem_tra_pandoc(self) -> bool:
        if self._co_pandoc is not None:
            return self._co_pandoc
        try:
            subprocess.run(
                ['pandoc', '--version'],
                capture_output=True, timeout=5,
            )
            self._co_pandoc = True
        except Exception as e:
            print(f'[Cảnh báo] Lỗi im lặng ở xu_ly_toan.py dòng 84: {e}')
            self._co_pandoc = False
        return self._co_pandoc

    # API CHÍNH

    def omml_element_to_latex(self, omath) -> str:
        # Chuyển một <m:oMath> element thành chuỗi LaTeX (XSLT → thủ công → Pandoc)
        latex = self._via_xslt(omath)
        if latex:
            return latex

        latex = self._via_manual_parser(omath)
        if latex:
            return latex

        latex = self._via_pandoc(omath)
        if latex:
            return latex

        return ""

    # HƯỚNG 1: XSLT  (OMML → MathML → LaTeX)

    def _via_xslt(self, omath) -> str:
        if self._xslt_transform is None:
            return ""
        try:
            # XSLT cần root element có namespace declarations
            wrapper = deepcopy(omath)
            result = self._xslt_transform(wrapper)
            mathml_str = str(result).strip()
            if not mathml_str:
                return ""

            # Nếu kết quả là MathML → chuyển sang LaTeX
            if '<math' in mathml_str or '<mml:math' in mathml_str:
                return self._mathml_to_latex(mathml_str)

            # Nếu XSLT trả LaTeX thẳng (custom XSLT)
            return mathml_str
        except Exception as e:
            print(f'[Cảnh báo] Lỗi im lặng ở xu_ly_toan.py dòng 125: {e}')
            return ""

    def _mathml_to_latex(self, mathml_str: str) -> str:
        # Chuyển chuỗi MathML → LaTeX (dùng thư viện hoặc fallback)
        # Dùng thư viện nếu có
        if self._mathml_to_latex_fn is not None:
            try:
                return self._mathml_to_latex_fn(mathml_str)
            except Exception as e:
                print(f'[Cảnh báo] Lỗi im lặng ở xu_ly_toan.py dòng 134: {e}')
                pass

        # Fallback: parse MathML đơn giản bằng lxml
        return self._mathml_simple_to_latex(mathml_str)

    def _mathml_simple_to_latex(self, mathml_str: str) -> str:
        # Parser MathML → LaTeX đơn giản (fallback khi không có thư viện)
        try:
            # Xóa namespace prefixes để parse dễ hơn
            clean = re.sub(r'<(/?)mml:', r'<\1', mathml_str)
            clean = re.sub(r'\s+xmlns:[a-z]+="[^"]*"', '', clean)
            root = etree.fromstring(clean.encode('utf-8'))
            return self._parse_mathml_node(root).strip()
        except Exception as e:
            print(f'[Cảnh báo] Lỗi im lặng ở xu_ly_toan.py dòng 148: {e}')
            return ""

    def _parse_mathml_node(self, node) -> str:
        tag = etree.QName(node.tag).localname if '}' in node.tag else node.tag
        children_latex = [self._parse_mathml_node(c) for c in node]

        if tag == 'math':
            return ' '.join(children_latex)
        elif tag == 'mrow':
            return ''.join(children_latex)
        elif tag == 'mi':
            return node.text or ''
        elif tag == 'mn':
            return node.text or ''
        elif tag == 'mo':
            op = node.text or ''
            # Map known operators
            op_map = {
                '(': '(', ')': ')', '+': '+', '-': '-', '=': '=',
                '×': r'\times', '·': r'\cdot', '±': r'\pm',
                '≤': r'\leq', '≥': r'\geq', '≠': r'\neq',
            }
            return op_map.get(op, op)
        elif tag == 'msup':
            if len(children_latex) >= 2:
                return f'{{{children_latex[0]}}}^{{{children_latex[1]}}}'
        elif tag == 'msub':
            if len(children_latex) >= 2:
                return f'{{{children_latex[0]}}}_{{{children_latex[1]}}}'
        elif tag == 'msubsup':
            if len(children_latex) >= 3:
                return f'{{{children_latex[0]}}}_{{{children_latex[1]}}}^{{{children_latex[2]}}}'
        elif tag == 'mfrac':
            if len(children_latex) >= 2:
                return rf'\frac{{{children_latex[0]}}}{{{children_latex[1]}}}'
        elif tag == 'msqrt':
            return rf'\sqrt{{{" ".join(children_latex)}}}'
        elif tag == 'mroot':
            if len(children_latex) >= 2:
                return rf'\sqrt[{children_latex[1]}]{{{children_latex[0]}}}'
        elif tag == 'mover':
            if len(children_latex) >= 2:
                return rf'\overset{{{children_latex[1]}}}{{{children_latex[0]}}}'
        elif tag == 'munder':
            if len(children_latex) >= 2:
                return rf'\underset{{{children_latex[1]}}}{{{children_latex[0]}}}'
        elif tag == 'mtext':
            t = node.text or ''
            return rf'\text{{{loc_ky_tu(t)}}}'
        elif tag == 'mtable':
            rows = []
            for child in node:
                child_tag = etree.QName(child.tag).localname if '}' in child.tag else child.tag
                if child_tag == 'mtr':
                    cells = []
                    for td in child:
                        cells.append(self._parse_mathml_node(td))
                    rows.append(' & '.join(cells))
            return r'\begin{matrix}' + r' \\ '.join(rows) + r'\end{matrix}'
        elif tag in ('mtd', 'mtr'):
            return ''.join(children_latex)
        elif tag == 'mspace':
            return r'\;'
        elif tag == 'mfenced':
            open_d = node.get('open', '(')
            close_d = node.get('close', ')')
            return rf'\left{open_d}{",".join(children_latex)}\right{close_d}'

        # Fallback
        return ''.join(children_latex)

    # HƯỚNG 2: PANDOC

    def _via_pandoc(self, omath) -> str:
        if not self._kiem_tra_pandoc():
            return ""
        try:
            # Tạo một document XML tối giản chứa oMath
            omath_copy = deepcopy(omath)
            # Wrap trong w:document > w:body > w:p > m:oMathPara
            nsmap = {
                'w': W_NAMESPACE,
                'm': OMML_NAMESPACE,
            }
            doc = etree.Element(f'{{{W_NAMESPACE}}}document', nsmap=nsmap)
            body = etree.SubElement(doc, f'{{{W_NAMESPACE}}}body')
            para = etree.SubElement(body, f'{{{W_NAMESPACE}}}p')
            omath_para = etree.SubElement(para, f'{{{OMML_NAMESPACE}}}oMathPara')
            omath_para.append(omath_copy)

            xml_bytes = etree.tostring(doc, xml_declaration=True, encoding='UTF-8')

            # Lưu tạm thành .xml, gọi pandoc
            with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='wb') as tmp:
                tmp.write(xml_bytes)
                tmp_path = tmp.name

            try:
                result = subprocess.run(
                    ['pandoc', '-f', 'docx', '-t', 'latex', tmp_path],
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        except Exception as e:
            print(f'[Cảnh báo] Lỗi im lặng ở xu_ly_toan.py dòng 258: {e}')
            pass
        return ""

    # HƯỚNG 3: PARSER THỦ CÔNG (đệ quy)

    def _via_manual_parser(self, omath) -> str:
        try:
            parts = []
            self._process_omml_element(omath, parts)
            return ''.join(parts)
        except Exception as e:
            print(f'[Cảnh báo] Lỗi im lặng ở xu_ly_toan.py dòng 269: {e}')
            return ""

    def _process_omml_element(self, elem, parts: list):
        # Đệ quy xử lý các phần tử OMML (f, rad, sSub, sSup, nary, d, func...)
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        ns = OMML_NAMESPACE

        if tag == 'f':
            num = elem.find(f'.//{{{ns}}}num')
            den = elem.find(f'.//{{{ns}}}den')
            if num is not None and den is not None:
                num_text = self._get_omml_text(num)
                den_text = self._get_omml_text(den)
                parts.append(rf'\frac{{{num_text}}}{{{den_text}}}')
                return

        elif tag == 'rad':
            deg = elem.find(f'.//{{{ns}}}deg')
            e = elem.find(f'.//{{{ns}}}e')
            if e is not None:
                e_text = self._get_omml_text(e)
                if deg is not None:
                    deg_text = self._get_omml_text(deg)
                    if deg_text.strip():
                        parts.append(rf'\sqrt[{deg_text}]{{{e_text}}}')
                        return
                parts.append(rf'\sqrt{{{e_text}}}')
                return

        elif tag == 'sSub':
            base = elem.find(f'.//{{{ns}}}e')
            sub = elem.find(f'.//{{{ns}}}sub')
            if base is not None:
                base_text = self._get_omml_text(base)
                sub_text = self._get_omml_text(sub) if sub is not None else ''
                parts.append(rf'{base_text}_{{{sub_text}}}')
                return

        elif tag == 'sSup':
            base = elem.find(f'.//{{{ns}}}e')
            sup = elem.find(f'.//{{{ns}}}sup')
            if base is not None:
                base_text = self._get_omml_text(base)
                sup_text = self._get_omml_text(sup) if sup is not None else ''
                parts.append(rf'{base_text}^{{{sup_text}}}')
                return

        elif tag == 'sSubSup':
            base = elem.find(f'.//{{{ns}}}e')
            sub = elem.find(f'.//{{{ns}}}sub')
            sup = elem.find(f'.//{{{ns}}}sup')
            if base is not None:
                base_text = self._get_omml_text(base)
                sub_text = self._get_omml_text(sub) if sub is not None else ''
                sup_text = self._get_omml_text(sup) if sup is not None else ''
                parts.append(rf'{base_text}_{{{sub_text}}}^{{{sup_text}}}')
                return

        elif tag == 'nary':
            naryPr = elem.find(f'{{{ns}}}naryPr')
            chr_elem = naryPr.find(f'{{{ns}}}chr') if naryPr is not None else None
            sub = elem.find(f'{{{ns}}}sub')
            sup = elem.find(f'{{{ns}}}sup')
            e = elem.find(f'{{{ns}}}e')

            symbol = '\\sum'
            if chr_elem is not None:
                val = chr_elem.get(f'{{{ns}}}val')
                symbol = NARY_SYMBOL_MAP.get(val, '\\sum')

            sub_text = self._get_omml_text(sub) if sub is not None else ''
            sup_text = self._get_omml_text(sup) if sup is not None else ''
            e_text = self._get_omml_text(e) if e is not None else ''

            result = symbol
            if sub_text:
                result += f'_{{{sub_text}}}'
            if sup_text:
                result += f'^{{{sup_text}}}'
            result += f' {e_text}'
            parts.append(result)
            return

        elif tag == 'd':
            dPr = elem.find(f'{{{ns}}}dPr')
            begChr = '('
            endChr = ')'
            if dPr is not None:
                beg_e = dPr.find(f'{{{ns}}}begChr')
                end_e = dPr.find(f'{{{ns}}}endChr')
                if beg_e is not None:
                    begChr = beg_e.get(f'{{{ns}}}val', '(')
                if end_e is not None:
                    endChr = end_e.get(f'{{{ns}}}val', ')')

            beg_latex = DELIMITER_MAP.get(begChr, begChr)
            end_latex = DELIMITER_MAP.get(endChr, endChr)

            # Nội dung bên trong (có thể nhiều e)
            e_list = elem.findall(f'{{{ns}}}e')
            inner_parts = []
            for e in e_list:
                inner_parts.append(self._get_omml_text(e))
            inner = ','.join(inner_parts)

            parts.append(rf'\left{beg_latex}{inner}\right{end_latex}')
            return

        elif tag == 'func':
            fName = elem.find(f'{{{ns}}}fName')
            e = elem.find(f'{{{ns}}}e')
            func_name = self._get_omml_text(fName) if fName is not None else ''
            e_text = self._get_omml_text(e) if e is not None else ''

            latex_func = FUNC_NAME_MAP.get(func_name.strip(), rf'\operatorname{{{func_name}}}')
            parts.append(f'{latex_func}{{{e_text}}}')
            return

        elif tag in ('limLow', 'limUpp'):
            e = elem.find(f'{{{ns}}}e')
            lim = elem.find(f'{{{ns}}}lim')
            e_text = self._get_omml_text(e) if e is not None else ''
            lim_text = self._get_omml_text(lim) if lim is not None else ''
            if tag == 'limLow':
                parts.append(rf'\underset{{{lim_text}}}{{{e_text}}}')
            else:
                parts.append(rf'\overset{{{lim_text}}}{{{e_text}}}')
            return

        elif tag == 'acc':
            accPr = elem.find(f'{{{ns}}}accPr')
            e = elem.find(f'{{{ns}}}e')
            e_text = self._get_omml_text(e) if e is not None else ''

            accent_char = '\u0302'  # default hat
            if accPr is not None:
                chr_el = accPr.find(f'{{{ns}}}chr')
                if chr_el is not None:
                    accent_char = chr_el.get(f'{{{ns}}}val', '\u0302')

            latex_accent = ACCENT_MAP.get(accent_char, '\\hat')
            parts.append(f'{latex_accent}{{{e_text}}}')
            return

        elif tag == 'bar':
            barPr = elem.find(f'{{{ns}}}barPr')
            e = elem.find(f'{{{ns}}}e')
            e_text = self._get_omml_text(e) if e is not None else ''

            pos = 'top'
            if barPr is not None:
                pos_el = barPr.find(f'{{{ns}}}pos')
                if pos_el is not None:
                    pos = pos_el.get(f'{{{ns}}}val', 'top')

            if pos == 'bot':
                parts.append(rf'\underline{{{e_text}}}')
            else:
                parts.append(rf'\overline{{{e_text}}}')
            return

        elif tag == 'eqArr':
            rows = []
            for e in elem.findall(f'{{{ns}}}e'):
                rows.append(self._get_omml_text(e))
            parts.append(r'\begin{aligned}' + r' \\ '.join(rows) + r'\end{aligned}')
            return

        elif tag == 'm' and elem.tag.endswith(f'{{{ns}}}m'):
            rows = []
            for mr in elem.findall(f'{{{ns}}}mr'):
                cells = []
                for e in mr.findall(f'{{{ns}}}e'):
                    cells.append(self._get_omml_text(e))
                rows.append(' & '.join(cells))
            parts.append(r'\begin{matrix}' + r' \\ '.join(rows) + r'\end{matrix}')
            return

        elif tag == 'box':
            e = elem.find(f'{{{ns}}}e')
            if e is not None:
                parts.append(self._get_omml_text(e))
            return

        elif tag == 'borderBox':
            e = elem.find(f'{{{ns}}}e')
            if e is not None:
                e_text = self._get_omml_text(e)
                parts.append(rf'\boxed{{{e_text}}}')
            return

        elif tag == 'r':
            for child in elem:
                child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if child_tag == 't' and child.text:
                    text = child.text
                    text = self._replace_unicode_math(text)
                    parts.append(text)
            return

        elif tag == 't':
            if elem.text:
                text = self._replace_unicode_math(elem.text)
                parts.append(text)
            return

        # Đệ quy xử lý các phần tử con
        for child in elem:
            self._process_omml_element(child, parts)

    def _get_omml_text(self, elem) -> str:
        # Lấy text LaTeX từ một sub-tree OMML
        parts = []
        self._process_omml_element(elem, parts)
        return ''.join(parts)

    # TIỆN ÍCH

    @staticmethod
    def _replace_unicode_math(text: str) -> str:
        # Thay thế các ký tự Unicode toán học thành LaTeX commands
        for pattern, replacement in OMML_CHAR_MAP:
            text = re.sub(pattern, replacement, text)
        return text

    def omml_to_text(self, omath_elem) -> str:
        # Lấy plain-text từ OMML element (không format LaTeX)
        try:
            text_parts = []
            for elem in omath_elem.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == 't' and elem.text:
                    text_parts.append(elem.text)
            return ''.join(text_parts)
        except Exception as e:
            print(f'[Cảnh báo] Lỗi im lặng ở xu_ly_toan.py dòng 504: {e}')
            return ""

    def trich_xuat_omml(self, doan_van) -> list:
        # Phát hiện OMML Math trong paragraph, trả về list (text_gốc, latex)
        cong_thuc = []
        try:
            omath_list = doan_van._element.findall(f'.//{{{OMML_NAMESPACE}}}oMath')
            for omath in omath_list:
                text_goc = self.omml_to_text(omath)
                latex = self.omml_element_to_latex(omath)
                if text_goc.strip() or latex.strip():
                    cong_thuc.append((text_goc, latex if latex.strip() else text_goc))
        except Exception as e:
            print(f'[Cảnh báo] Lỗi im lặng ở xu_ly_toan.py dòng 517: {e}')
            pass
        return cong_thuc
