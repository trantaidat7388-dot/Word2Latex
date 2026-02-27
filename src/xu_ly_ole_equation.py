# xu_ly_ole_equation.py - Chuyển OLE Equation.3 (MTEF) → LaTeX
#
# OLE Equation Editor 3.0 dùng format MTEF v3 (MathType Equation Format)
# Pipeline:
#   1. Trích "Equation Native" stream từ OLE Compound File
#   2. Parse MTEF binary → cây cú pháp
#   3. Duyệt cây → sinh LaTeX
#
# Cách dùng:
#   latex = ole_equation_to_latex(ole_binary_bytes)

import struct
import io
import re

try:
    import olefile
except ImportError:
    olefile = None

# HẰNG SỐ MTEF

# Record types (lower 4 bits of tag byte in MTEF v3)
_END = 0
_LINE = 1
_CHAR = 2
_TMPL = 3
_PILE = 4
_MATRIX = 5
_EMBELL = 6
_RULER = 7
_FONT_STYLE_DEF = 8
_SIZE = 9
_FULL = 10
_SUB = 11
_SUB2 = 12
_SYM = 13
_SUBSYM = 14

# Font style indices (typeface_byte - 128)
_FN_TEXT = 1
_FN_FUNCTION = 2
_FN_VARIABLE = 3
_FN_LC_GREEK = 4
_FN_UC_GREEK = 5
_FN_SYMBOL = 6
_FN_VECTOR = 7
_FN_NUMBER = 8
_FN_USER1 = 9
_FN_USER2 = 10
_FN_MTEXTRA = 11
_FN_EXPAND = 22

# Ánh xạ Unicode → LaTeX cho các ký tự đặc biệt trong MTEF
_UNICODE_TO_LATEX = {
    0x222B: r'\int',       # ∫
    0x222C: r'\iint',      # ∬
    0x222D: r'\iiint',     # ∭
    0x222E: r'\oint',      # ∮
    0x2211: r'\sum',       # ∑
    0x220F: r'\prod',      # ∏
    0x2210: r'\coprod',    # ∐
    0x222A: r'\cup',       # ∪
    0x2229: r'\cap',       # ∩
    0x2212: '-',           # − (minus sign)
    0x00B1: r'\pm',        # ±
    0x2213: r'\mp',        # ∓
    0x00D7: r'\times',     # ×
    0x00F7: r'\div',       # ÷
    0x2264: r'\leq',       # ≤
    0x2265: r'\geq',       # ≥
    0x2260: r'\neq',       # ≠
    0x2248: r'\approx',    # ≈
    0x221E: r'\infty',     # ∞
    0x2202: r'\partial',   # ∂
    0x2207: r'\nabla',     # ∇
    0x2200: r'\forall',    # ∀
    0x2203: r'\exists',    # ∃
    0x2208: r'\in',        # ∈
    0x2209: r'\notin',     # ∉
    0x2282: r'\subset',    # ⊂
    0x2283: r'\supset',    # ⊃
    0x2286: r'\subseteq',  # ⊆
    0x2287: r'\supseteq',  # ⊇
    0x00B0: r'^\circ',     # °
    0x03B1: r'\alpha',     # α
    0x03B2: r'\beta',      # β
    0x03B3: r'\gamma',     # γ
    0x03B4: r'\delta',     # δ
    0x03B5: r'\varepsilon',# ε
    0x03B6: r'\zeta',      # ζ
    0x03B7: r'\eta',       # η
    0x03B8: r'\theta',     # θ
    0x03B9: r'\iota',      # ι
    0x03BA: r'\kappa',     # κ
    0x03BB: r'\lambda',    # λ
    0x03BC: r'\mu',        # μ
    0x03BD: r'\nu',        # ν
    0x03BE: r'\xi',        # ξ
    0x03C0: r'\pi',        # π
    0x03C1: r'\rho',       # ρ
    0x03C3: r'\sigma',     # σ
    0x03C4: r'\tau',       # τ
    0x03C5: r'\upsilon',   # υ
    0x03C6: r'\varphi',    # φ
    0x03C7: r'\chi',       # χ
    0x03C8: r'\psi',       # ψ
    0x03C9: r'\omega',     # ω
    0x0393: r'\Gamma',     # Γ
    0x0394: r'\Delta',     # Δ
    0x0398: r'\Theta',     # Θ
    0x039B: r'\Lambda',    # Λ
    0x039E: r'\Xi',        # Ξ
    0x03A0: r'\Pi',        # Π
    0x03A3: r'\Sigma',     # Σ
    0x03A6: r'\Phi',       # Φ
    0x03A8: r'\Psi',       # Ψ
    0x03A9: r'\Omega',     # Ω
    0x2190: r'\leftarrow',
    0x2191: r'\uparrow',
    0x2192: r'\rightarrow',
    0x2193: r'\downarrow',
    0x2194: r'\leftrightarrow',
    0x21D0: r'\Leftarrow',
    0x21D2: r'\Rightarrow',
    0x21D4: r'\Leftrightarrow',
    0x22C5: r'\cdot',      # ⋅
    0x2026: r'\ldots',     # …
    0x22EF: r'\cdots',     # ⋯
}

# Ký tự LaTeX cần escape trong math mode
_LATEX_SPECIAL = {'%': r'\%', '&': r'\&', '#': r'\#', '_': r'\_', '$': r'\$'}

# PARSER: MTEF Binary → Parse Tree

class MTEFParser:
    # Parser cho MTEF v3 binary (Equation Editor 3.0)

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.version = data[0]
        self.platform = data[1]
        self.product = data[2]
        self.prod_ver = data[3]
        self.prod_sub = data[4]
        self.pos = 5

    def _read_byte(self):
        if self.pos >= len(self.data):
            return None
        b = self.data[self.pos]
        self.pos += 1
        return b

    def _peek_byte(self):
        if self.pos >= len(self.data):
            return None
        return self.data[self.pos]

    def _read_uint16_le(self):
        if self.pos + 1 >= len(self.data):
            self.pos = len(self.data)
            return 0
        lo = self.data[self.pos]
        hi = self.data[self.pos + 1]
        self.pos += 2
        return (hi << 8) | lo

    def parse(self):
        # Parse toàn bộ MTEF → danh sách record
        records = []
        while self.pos < len(self.data):
            rec = self._parse_record()
            if rec is None:
                break
            records.append(rec)
        return records

    def _parse_record(self):
        if self.pos >= len(self.data):
            return None
        tag = self._read_byte()
        if tag is None:
            return None
        rec_type = tag & 0x0F
        options = (tag >> 4) & 0x0F

        if rec_type == _END:
            return ('END',)
        elif rec_type == _LINE:
            return self._parse_line(options)
        elif rec_type == _CHAR:
            return self._parse_char(options)
        elif rec_type == _TMPL:
            return self._parse_tmpl(options)
        elif rec_type == _PILE:
            return self._parse_pile(options)
        elif rec_type == _MATRIX:
            return self._parse_matrix(options)
        elif rec_type == _EMBELL:
            return self._parse_embell(options)
        elif rec_type in (_FULL, _SUB, _SUB2, _SYM, _SUBSYM):
            # Các record đánh dấu kích thước - không có dữ liệu phụ
            return (['FULL', '', '', 'SIZE', '', 'SUB', 'SUB2', '', '', '', 'FULL', 'SUB', 'SUB2', 'SYM', 'SUBSYM'][rec_type],)
        elif rec_type in (_RULER, _FONT_STYLE_DEF, _SIZE):
            # Bỏ qua các record ít gặp
            return ('SKIP',)
        else:
            return ('UNKNOWN', tag)

    def _parse_line(self, options):
        children = []
        while self.pos < len(self.data):
            rec = self._parse_record()
            if rec is None or rec[0] == 'END':
                break
            children.append(rec)
        return ('LINE', children)

    def _parse_char(self, options):
        typeface = self._read_byte() or 0x81
        char_code = self._read_uint16_le()
        font_style = typeface - 128
        return ('CHAR', font_style, char_code)

    def _parse_tmpl(self, options):
        selector = self._read_byte() or 0
        variation = self._read_byte() or 0
        # Variation 2 bytes nếu bit 7 set (chủ yếu MTEF v5)
        if variation & 0x80:
            var2 = self._read_byte() or 0
            variation = (variation & 0x7F) | (var2 << 7)

        # Đọc các slot (mỗi slot kết thúc bằng END)
        # Đọc tham lam, dừng khi byte tiếp theo không phải LINE/END
        slots = []
        for _ in range(8):  # tối đa 8 slot
            if self.pos >= len(self.data):
                break
            slot = self._parse_slot()
            slots.append(slot)
            # Kiểm tra byte tiếp: nếu không phải END/LINE → dừng
            nxt = self._peek_byte()
            if nxt is None:
                break
            nxt_type = nxt & 0x0F
            if nxt_type not in (_END, _LINE):
                break

        return ('TMPL', selector, variation, slots)

    def _parse_slot(self):
        # Đọc danh sách record cho đến END
        records = []
        while self.pos < len(self.data):
            rec = self._parse_record()
            if rec is None or rec[0] == 'END':
                break
            records.append(rec)
        return records

    def _parse_pile(self, options):
        halign = self._read_byte() or 0
        lines = []
        while self.pos < len(self.data):
            rec = self._parse_record()
            if rec is None or rec[0] == 'END':
                break
            lines.append(rec)
        return ('PILE', halign, lines)

    def _parse_matrix(self, options):
        rows = self._read_byte() or 1
        cols = self._read_byte() or 1
        # Đọc alignment cho mỗi cột
        col_aligns = []
        for _ in range(cols):
            col_aligns.append(self._read_byte() or 0)
        # Đọc rows*cols cell (mỗi cell kết thúc bằng END)
        cells = []
        for _ in range(rows * cols):
            cell = self._parse_slot()
            cells.append(cell)
        return ('MATRIX', rows, cols, cells)

    def _parse_embell(self, options):
        embell_type = self._read_byte() or 0
        return ('EMBELL', embell_type)

# CONVERTER: Parse Tree → LaTeX String

# Ánh xạ cặp ngoặc fence cho các TMPL fence (selector 0-9)
_FENCE_PAIRS = {
    0: (r'\langle ', r'\rangle '),  # angle
    1: ('(', ')'),                   # paren
    2: (r'\{', r'\}'),              # brace
    3: ('[', ']'),                   # bracket
    4: ('|', '|'),                   # bar
    5: (r'\|', r'\|'),              # double bar
    6: (r'\lfloor ', r'\rfloor '),  # floor
    7: (r'\lceil ', r'\rceil '),    # ceiling
}

# Ánh xạ embellishment → LaTeX
_EMBELL_MAP = {
    2: r'\dot',
    3: r'\ddot',
    4: r'\dddot',
    5: r'\hat',
    6: r'\bar',
    7: r'\vec',
    8: r'\tilde',
    9: r'\check',
    17: r'\overrightarrow',
}

def _char_to_latex(font_style, char_code):
    # Chuyển 1 ký tự MTEF → LaTeX string
    # Kiểm tra bảng Unicode → LaTeX
    if char_code in _UNICODE_TO_LATEX:
        return _UNICODE_TO_LATEX[char_code]

    ch = chr(char_code) if 0x20 <= char_code < 0x10000 else ''
    if not ch:
        return ''

    # Escape ký tự đặc biệt LaTeX
    if ch in _LATEX_SPECIAL:
        return _LATEX_SPECIAL[ch]

    # Xử lý theo font style
    if font_style == _FN_FUNCTION:
        # Ngoặc và dấu phẩy giữ nguyên
        if ch in '()[]{}|,;:.!?':
            return ch
        # Tên hàm (sin, cos, ...) → \mathrm{}
        return r'\mathrm{' + ch + '}'
    elif font_style == _FN_TEXT:
        return r'\text{' + ch + '}'
    elif font_style == _FN_VECTOR:
        return r'\boldsymbol{' + ch + '}'
    elif font_style == _FN_NUMBER:
        return ch
    elif font_style == _FN_SYMBOL:
        return ch
    elif font_style == _FN_VARIABLE:
        return ch  # italic mặc định trong math mode
    elif font_style == _FN_EXPAND:
        return ch
    else:
        return ch

def _split_by_size_markers(records):
    # Chia danh sách record theo marker FULL/SUB/SYM
    # Trả về dict: {'full': [...], 'sub': [...], 'sym': [...], ...}
    parts = {}
    current_key = 'full'
    for rec in records:
        if rec[0] in ('FULL', 'SUB', 'SUB2', 'SYM', 'SUBSYM'):
            current_key = rec[0].lower()
            if current_key not in parts:
                parts[current_key] = []
            continue
        if current_key not in parts:
            parts[current_key] = []
        parts[current_key].append(rec)
    return parts

def _records_to_latex(records):
    # Chuyển danh sách record → LaTeX string
    parts = []
    for rec in records:
        parts.append(_node_to_latex(rec))
    return ''.join(parts)

def _node_to_latex(node):
    # Chuyển 1 node trong parse tree → LaTeX string
    if not node:
        return ''

    tag = node[0]

    if tag == 'CHAR':
        _, font_style, char_code = node
        return _char_to_latex(font_style, char_code)

    elif tag == 'LINE':
        _, children = node
        return _records_to_latex(children)

    elif tag == 'TMPL':
        _, selector, variation, slots = node
        return _tmpl_to_latex(selector, variation, slots)

    elif tag == 'PILE':
        _, halign, lines = node
        return _pile_to_latex(lines)

    elif tag == 'MATRIX':
        _, rows, cols, cells = node
        return _matrix_to_latex(rows, cols, cells)

    elif tag == 'EMBELL':
        _, embell_type = node
        cmd = _EMBELL_MAP.get(embell_type, r'\hat')
        return cmd

    elif tag in ('FULL', 'SUB', 'SUB2', 'SYM', 'SUBSYM'):
        return ''  # size marker, bỏ qua khi render đơn lẻ

    elif tag == 'END':
        return ''

    else:
        return ''

def _collect_fence_chars(slots):
    # Thu thập ký tự fence (ngoặc) từ cuối slots
    # Trả về (content_records, left_char, right_char)
    # Trong v3, fence chars có thể là CHAR ở cuối slot cuối
    # hoặc CHAR nằm ngoài slots hoàn toàn
    left = ''
    right = ''

    # Tìm slot đầu tiên có nội dung (bỏ slot rỗng)
    content_records = []
    for slot in slots:
        if slot:
            content_records = slot
            break

    # Tìm fence chars: các CHAR ở cuối với fnEXPAND hoặc fnSYMBOL
    # mà trông giống ngoặc
    fence_brackets = set('()[]{}|⟨⟩⌊⌋⌈⌉')
    found_fences = []
    remaining = list(content_records)

    # Quét từ cuối: lấy các CHAR có ký tự fence
    while remaining and remaining[-1][0] == 'CHAR':
        _, fs, cc = remaining[-1]
        ch = chr(cc) if 0x20 <= cc < 0x10000 else ''
        if ch in fence_brackets or fs == _FN_EXPAND:
            found_fences.insert(0, remaining.pop())
        else:
            break

    if len(found_fences) >= 2:
        left = chr(found_fences[0][2])
        right = chr(found_fences[1][2])
    elif len(found_fences) == 1:
        left = chr(found_fences[0][2])
        right = left

    return remaining, left, right

def _tmpl_to_latex(selector, variation, slots):
    # Chuyển TMPL record → LaTeX tùy theo selector
    # Gom tất cả records từ các slot vào 1 danh sách phẳng
    all_records = []
    for slot in slots:
        all_records.extend(slot)

    # Ngoặc đơn, ngoặc vuông, ngoặc nhọn, thanh abs, v.v.
    if 0 <= selector <= 9:
        remaining, left, right = _collect_fence_chars(slots)

        # Nếu không tìm được fence chars, dùng mặc định từ bảng
        if not left and selector in _FENCE_PAIRS:
            left, right = _FENCE_PAIRS[selector]

        # Đếm số LINE con - nếu > 1 LINE, xem như pile/matrix
        line_records = [r for r in remaining if r[0] == 'LINE']
        non_line = [r for r in remaining if r[0] not in ('LINE', 'FULL', 'SUB', 'SUB2', 'SYM', 'SUBSYM')]

        if len(line_records) > 1 and not non_line:
            # Nhiều LINE bên trong ngoặc → xác định cấu trúc matrix
            n = len(line_records)
            # Tìm kích thước ma trận vuông nếu có thể
            import math
            sqrt_n = int(math.isqrt(n))

            # Ánh xạ selector → loại matrix environmen
            matrix_env = {3: 'bmatrix', 1: 'pmatrix', 4: 'vmatrix',
                          5: 'Vmatrix', 2: 'Bmatrix'}.get(selector, 'matrix')

            if sqrt_n * sqrt_n == n and sqrt_n > 1:
                # Ma trận vuông: sắp xếp theo hàng
                rows_latex = []
                for r_idx in range(sqrt_n):
                    row_cells = []
                    for c_idx in range(sqrt_n):
                        cell_idx = r_idx * sqrt_n + c_idx
                        row_cells.append(_node_to_latex(line_records[cell_idx]))
                    rows_latex.append(' & '.join(row_cells))
                content = r' \\ '.join(rows_latex)
            else:
                # Không phải ma trận vuông → xếp dọc (pile)
                rows = [_node_to_latex(lr) for lr in line_records]
                content = r' \\ '.join(rows)

            return r'\begin{' + matrix_env + '} ' + content + r' \end{' + matrix_env + '}'

        content = _records_to_latex(remaining)
        if content:
            # Nếu nội dung đã là matrix environment → bỏ fence ngoài
            content_stripped = content.strip()
            if content_stripped.startswith(r'\begin{') and 'matrix}' in content_stripped:
                return content
            return r'\left' + left + ' ' + content + r' \right' + right
        return r'\left' + left + r' \right' + right

    elif selector == 10 or selector == 13:
        return _root_to_latex(all_records, variation)

    elif selector == 11:
        return _frac_to_latex(slots)

    # Trong v3, selector 12 thường là underbar, selector 13 thường là root
    elif selector == 12:
        content = _records_to_latex(all_records)
        return r'\underline{' + content + '}'

    elif selector in (15, 16, 17, 18, 19, 20, 21, 22, 24):
        return _bigop_to_latex(all_records, selector)

    elif selector == 23:
        return _limit_to_latex(all_records)

    # Xử lý ở bigop

    elif selector in (27, 28, 29):
        return _script_to_latex(all_records, selector)

    elif selector == 31:
        content = _records_to_latex(all_records)
        return r'\vec{' + content + '}'
    elif selector == 32:
        content = _records_to_latex(all_records)
        return r'\tilde{' + content + '}'
    elif selector == 33:
        content = _records_to_latex(all_records)
        return r'\hat{' + content + '}'
    elif selector == 34:
        content = _records_to_latex(all_records)
        return r'\overset{\frown}{' + content + '}'

    elif selector == 25 or selector == 36:
        content = _records_to_latex(all_records)
        return r'\overline{' + content + '}'

    elif selector == 37 or selector == 26:
        content = _records_to_latex(all_records)
        return r'\cancel{' + content + '}'

    else:
        return _records_to_latex(all_records)

def _root_to_latex(records, variation):
    # Chuyển ROOT template → \sqrt{} hoặc \sqrt[n]{}
    # Trong v3: radicand LINE, sau đó SUB marker + index LINE
    parts = _split_by_size_markers(records)

    # Phần full (hoặc không có marker) = radicand
    radicand_recs = parts.get('full', [])
    # Phần sub = index (nếu nth root)
    index_recs = parts.get('sub', [])

    radicand = _records_to_latex(radicand_recs)
    index = _records_to_latex(index_recs)

    # Bỏ ngoặc thừa nếu radicand đã được bao bởi ()
    radicand_clean = radicand.strip()
    if radicand_clean.startswith('(') and radicand_clean.endswith(')'):
        # Kiểm tra ngoặc cân bằng
        depth = 0
        balanced = True
        for i, c in enumerate(radicand_clean):
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            if depth == 0 and i < len(radicand_clean) - 1:
                balanced = False
                break
        if balanced:
            radicand_clean = radicand_clean[1:-1]

    if index:
        return r'\sqrt[' + index + ']{' + radicand_clean + '}'
    else:
        return r'\sqrt{' + radicand_clean + '}'

def _frac_to_latex(slots):
    # Chuyển FRACTION → \frac{num}{den}
    # Slot 0 = tử, Slot 1 = mẫu (hoặc ngược lại tùy v3)
    if len(slots) >= 2:
        num_recs = slots[0] if slots[0] else []
        den_recs = slots[1] if slots[1] else []
    elif len(slots) == 1:
        # Thử tách theo size marker
        parts = _split_by_size_markers(slots[0])
        num_recs = parts.get('full', [])
        den_recs = parts.get('sub', [])
    else:
        return r'\frac{}{}'

    num = _records_to_latex(num_recs)
    den = _records_to_latex(den_recs)
    return r'\frac{' + num + '}{' + den + '}'

def _bigop_to_latex(records, selector):
    # Chuyển BIG OPERATOR (integral, sum, ...) → LaTeX
    # Trong v3: integrand ở FULL, limits ở SUB, operator ở SYM
    parts = _split_by_size_markers(records)

    # Phần integrand (FULL size)
    integrand_recs = parts.get('full', [])
    # Phần limits (SUB size) - thường là 2 LINE: lower, upper
    limit_recs = parts.get('sub', [])
    # Phần operator (SYM size) - chứa CHAR ∫/∑ v.v.
    sym_recs = parts.get('sym', [])

    # Xác định operator LaTeX từ SYM records
    operator = ''
    for rec in sym_recs:
        if rec[0] == 'CHAR':
            operator = _char_to_latex(rec[1], rec[2])
            break

    # Nếu không tìm thấy operator từ SYM, suy ra từ selector
    if not operator:
        op_map = {
            15: r'\int', 24: r'\int',
            16: r'\sum', 22: r'\sum',
            17: r'\prod',
            18: r'\coprod',
            19: r'\bigcup',
            20: r'\bigcap',
            21: r'\int',
        }
        operator = op_map.get(selector, r'\int')

    # Trích lower và upper limits
    lower = ''
    upper = ''
    limit_lines = [r for r in limit_recs if r[0] == 'LINE']
    if len(limit_lines) >= 1:
        lower = _node_to_latex(limit_lines[0])
    if len(limit_lines) >= 2:
        upper = _node_to_latex(limit_lines[1])

    # Xây dựng LaTeX
    result = operator
    if lower:
        result += '_{' + lower + '}'
    if upper:
        result += '^{' + upper + '}'

    integrand = _records_to_latex(integrand_recs)
    if integrand:
        result += ' ' + integrand

    return result

def _limit_to_latex(records):
    # \lim hoặc tương tự
    parts = _split_by_size_markers(records)
    main_recs = parts.get('full', [])
    sub_recs = parts.get('sub', [])

    main = _records_to_latex(main_recs)
    sub = _records_to_latex(sub_recs)

    if sub:
        return main + '_{' + sub + '}'
    return main

def _script_to_latex(records, selector):
    # SUB (27): subscript, SUP (28): superscript, SUBSUP (29): cả hai
    # Trong v3, format: base_content SUB lower SUP upper hoặc tương tự
    parts = _split_by_size_markers(records)
    base_recs = parts.get('full', [])
    sub_recs = parts.get('sub', [])
    sup_recs = parts.get('sym', parts.get('sub2', []))

    base = _records_to_latex(base_recs) if base_recs else ''
    sub_text = _records_to_latex(sub_recs) if sub_recs else ''

    if selector == 27:  # SUB
        return base + '_{' + sub_text + '}'
    elif selector == 28:  # SUP
        return base + '^{' + sub_text + '}'
    else:  # SUBSUP
        sup_text = _records_to_latex(sup_recs) if sup_recs else ''
        return base + '_{' + sub_text + '}^{' + sup_text + '}'

def _pile_to_latex(lines):
    # PILE → \begin{array}{c} ... \end{array}
    rows = []
    for line in lines:
        rows.append(_node_to_latex(line))
    if len(rows) <= 1:
        return rows[0] if rows else ''
    return r'\begin{array}{c} ' + r' \\ '.join(rows) + r' \end{array}'

def _matrix_to_latex(rows, cols, cells):
    # MATRIX → \begin{matrix} ... \end{matrix}
    # Trường hợp đặc biệt: MATRIX 1x1 chỉ là wrapper
    if rows == 1 and cols == 1 and len(cells) == 1:
        cell_content = cells[0]
        # Nếu cell chứa TMPL fence + CHAR fence chars → gom lại
        tmpl_rec = None
        fence_chars = []
        other_recs = []
        for rec in cell_content:
            if rec[0] == 'TMPL' and not tmpl_rec:
                tmpl_rec = rec
            elif rec[0] == 'CHAR' and rec[1] == _FN_EXPAND:
                fence_chars.append(rec)
            else:
                other_recs.append(rec)

        if tmpl_rec and fence_chars:
            # Gom fence chars vào TMPL fence
            _, sel, var, slots = tmpl_rec
            if 0 <= sel <= 9:
                # Thêm fence chars vào slot cuối
                if slots:
                    slots[-1] = list(slots[-1]) + fence_chars
                else:
                    slots.append(fence_chars)
                return _tmpl_to_latex(sel, var, slots)

        # Nếu không phải trường hợp đặc biệt, render bình thường
        return _records_to_latex(cell_content)

    result_rows = []
    for r in range(rows):
        row_parts = []
        for c in range(cols):
            idx = r * cols + c
            if idx < len(cells):
                cell_latex = _records_to_latex(cells[idx])
                row_parts.append(cell_latex)
        result_rows.append(' & '.join(row_parts))
    return r'\begin{matrix} ' + r' \\ '.join(result_rows) + r' \end{matrix}'

# HÀM CHÍNH: OLE Binary → LaTeX

def extract_mtef_from_ole(ole_binary: bytes) -> bytes | None:
    # Trích xuất MTEF data từ OLE Compound File
    # ole_binary = nội dung file oleObjectN.bin từ DOCX
    if olefile is None:
        return None

    try:
        ole = olefile.OleFileIO(io.BytesIO(ole_binary))
        if ole.exists('Equation Native'):
            eq_data = ole.openstream('Equation Native').read()
            if len(eq_data) < 28:
                ole.close()
                return None
            # Header 28 bytes (cbHdr ở 4 byte đầu)
            cb_hdr = struct.unpack_from('<I', eq_data, 0)[0]
            mtef_data = eq_data[cb_hdr:]
            ole.close()
            return mtef_data
        ole.close()
    except Exception as e:
        print(f'[Cảnh báo] Lỗi im lặng ở xu_ly_ole_equation.py dòng 771: {e}')
        pass
    return None

def parse_mtef(mtef_data: bytes) -> list:
    # Parse MTEF binary → danh sách record (parse tree)
    if not mtef_data or len(mtef_data) < 5:
        return []
    parser = MTEFParser(mtef_data)
    return parser.parse()

def mtef_tree_to_latex(tree: list) -> str:
    # Chuyển parse tree → LaTeX string
    return _records_to_latex(tree)

def ole_equation_to_latex(ole_binary: bytes) -> str:
    # Hàm chính: OLE binary → LaTeX math string
    # Trả về '' nếu không parse được
    mtef_data = extract_mtef_from_ole(ole_binary)
    if not mtef_data:
        return ''

    tree = parse_mtef(mtef_data)
    if not tree:
        return ''

    latex = mtef_tree_to_latex(tree)

    # Dọn dẹp chuỗi kết quả
    # Bỏ khoảng trắng thừa
    latex = re.sub(r'\s+', ' ', latex).strip()
    # Bỏ \mathrm{} bao đơn ký tự phổ biến
    # VD: \mathrm{(} → (
    latex = re.sub(r'\\mathrm\{([()[\]{}|,;:.!?])\}', r'\1', latex)
    # Thêm \, trước dx, dt, dy, ds trong tích phân
    latex = re.sub(r'(?<!\\)d([xytsurv])\b', r'\\, d\1', latex)

    return latex
