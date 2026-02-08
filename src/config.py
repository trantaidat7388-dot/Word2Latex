# config.py - Hằng số, namespace, và cấu hình cho dự án Word2LaTeX

# NAMESPACES

# Namespace cho OMML (Office Math Markup Language)
OMML_NAMESPACE = 'http://schemas.openxmlformats.org/officeDocument/2006/math'

# Namespaces cho OLE Object (Equation Editor cũ)
W_NAMESPACE = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

OLE_NAMESPACE = 'urn:schemas-microsoft-com:office:office'

VML_NAMESPACE = 'urn:schemas-microsoft-com:vml'

R_NAMESPACE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

# Namespace cho Drawing
A_NAMESPACE = 'http://schemas.openxmlformats.org/drawingml/2006/main'
WP_NAMESPACE = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
WP14_NAMESPACE = 'http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing'
REL_NAMESPACE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

# STYLE MAPPING: Word Style → LaTeX Command
MAP_STYLE = {
    'Heading 1': r'\section',
    'Heading 2': r'\subsection',
    'Heading 3': r'\subsubsection',
    'Heading 4': r'\paragraph',
    'Title': r'\title',
    'Subtitle': r'\subtitle',
    'TOC Heading': None,  # Bỏ qua
}

# HEADING PATTERNS: Phát hiện heading tiếng Việt từ nội dung
HEADING_PATTERNS = [
    (r'^(CHƯƠNG|CHAPTER)\s*(\d+|[IVXLC]+)[\.::]?\s*(.+)$', r'\section*'),
    (r'^(\d+)\.(\d+)\.(\d+)\.?\s*(.+)$', r'\subsubsection*'),   # 1.1.1. hoặc 1.1.1tiêu đề
    (r'^(\d+)\.(\d+)\.?\s*([A-ZÀ-Ỹ].+)$', r'\subsection*'),     # 1.1. hoặc 1.1tiêu đề
    (r'^(\d+)\.\s+([A-ZÀ-Ỹ][a-zA-ZÀ-ỹ\s]{10,})$', r'\section*'), # 1. Tiêu đề dài >10 ký tự
]

# OMML → LaTeX: Bảng ký tự Unicode → LaTeX command
OMML_CHAR_MAP = [
    (r'√', r'\\sqrt'),
    (r'∑', r'\\sum'),
    (r'∏', r'\\prod'),
    (r'∫', r'\\int'),
    (r'∞', r'\\infty'),
    (r'≤', r'\\leq'),
    (r'≥', r'\\geq'),
    (r'≠', r'\\neq'),
    (r'±', r'\\pm'),
    (r'∓', r'\\mp'),
    (r'×', r'\\times'),
    (r'÷', r'\\div'),
    (r'·', r'\\cdot'),
    (r'∂', r'\\partial'),
    (r'∇', r'\\nabla'),
    (r'∀', r'\\forall'),
    (r'∃', r'\\exists'),
    (r'∈', r'\\in'),
    (r'∉', r'\\notin'),
    (r'⊂', r'\\subset'),
    (r'⊃', r'\\supset'),
    (r'⊆', r'\\subseteq'),
    (r'⊇', r'\\supseteq'),
    (r'∪', r'\\cup'),
    (r'∩', r'\\cap'),
    (r'∅', r'\\emptyset'),
    (r'≈', r'\\approx'),
    (r'≡', r'\\equiv'),
    (r'≅', r'\\cong'),
    (r'∝', r'\\propto'),
    (r'←', r'\\leftarrow'),
    (r'→', r'\\rightarrow'),
    (r'↔', r'\\leftrightarrow'),
    (r'⇐', r'\\Leftarrow'),
    (r'⇒', r'\\Rightarrow'),
    (r'⇔', r'\\Leftrightarrow'),
    (r'…', r'\\ldots'),
    (r'⋯', r'\\cdots'),
    (r'⋮', r'\\vdots'),
    (r'⋱', r'\\ddots'),
    # Greek letters
    (r'α', r'\\alpha'),
    (r'β', r'\\beta'),
    (r'γ', r'\\gamma'),
    (r'δ', r'\\delta'),
    (r'ε', r'\\epsilon'),
    (r'ζ', r'\\zeta'),
    (r'η', r'\\eta'),
    (r'θ', r'\\theta'),
    (r'ι', r'\\iota'),
    (r'κ', r'\\kappa'),
    (r'λ', r'\\lambda'),
    (r'μ', r'\\mu'),
    (r'ν', r'\\nu'),
    (r'ξ', r'\\xi'),
    (r'π', r'\\pi'),
    (r'ρ', r'\\rho'),
    (r'σ', r'\\sigma'),
    (r'τ', r'\\tau'),
    (r'υ', r'\\upsilon'),
    (r'φ', r'\\phi'),
    (r'χ', r'\\chi'),
    (r'ψ', r'\\psi'),
    (r'ω', r'\\omega'),
    # Upper-case Greek
    (r'Γ', r'\\Gamma'),
    (r'Δ', r'\\Delta'),
    (r'Θ', r'\\Theta'),
    (r'Λ', r'\\Lambda'),
    (r'Ξ', r'\\Xi'),
    (r'Π', r'\\Pi'),
    (r'Σ', r'\\Sigma'),
    (r'Υ', r'\\Upsilon'),
    (r'Φ', r'\\Phi'),
    (r'Ψ', r'\\Psi'),
    (r'Ω', r'\\Omega'),
]

# Nary (tổng, tích phân...) symbol map
NARY_SYMBOL_MAP = {
    '∫': '\\int',
    '∬': '\\iint',
    '∭': '\\iiint',
    '∮': '\\oint',
    '∏': '\\prod',
    '∐': '\\coprod',
    '∑': '\\sum',
    '⋀': '\\bigwedge',
    '⋁': '\\bigvee',
    '⋂': '\\bigcap',
    '⋃': '\\bigcup',
}

# Delimiter (ngoặc) map
DELIMITER_MAP = {
    '(': '(',
    ')': ')',
    '[': '[',
    ']': ']',
    '{': r'\{',
    '}': r'\}',
    '|': '|',
    '‖': r'\|',
    '⌊': r'\lfloor',
    '⌋': r'\rfloor',
    '⌈': r'\lceil',
    '⌉': r'\rceil',
    '⟨': r'\langle',
    '⟩': r'\rangle',
}

# Accent map (dấu trên ký tự toán)
ACCENT_MAP = {
    '\u0302': '\\hat',       # Circumflex  ̂
    '\u0303': '\\tilde',     # Tilde  ̃
    '\u0300': '\\grave',     # Grave  ̀
    '\u0301': '\\acute',     # Acute  ́
    '\u0307': '\\dot',       # Dot  ̇
    '\u0308': '\\ddot',      # Double dot  ̈
    '\u0305': '\\bar',       # Overline  ̅
    '\u20d7': '\\vec',       # Vector arrow
    '\u0306': '\\breve',     # Breve  ̆
    '\u030c': '\\check',     # Caron  ̌
}

# Function name map (tên hàm toán học)
FUNC_NAME_MAP = {
    'sin': '\\sin', 'cos': '\\cos', 'tan': '\\tan',
    'sec': '\\sec', 'csc': '\\csc', 'cot': '\\cot',
    'sinh': '\\sinh', 'cosh': '\\cosh', 'tanh': '\\tanh',
    'ln': '\\ln', 'log': '\\log', 'exp': '\\exp',
    'lim': '\\lim', 'max': '\\max', 'min': '\\min',
    'sup': '\\sup', 'inf': '\\inf',
    'det': '\\det', 'dim': '\\dim', 'ker': '\\ker',
    'deg': '\\deg', 'gcd': '\\gcd', 'arg': '\\arg',
    'mod': '\\bmod',
}

# Đường dẫn XSLT mặc định (Microsoft Office)
import os as _os

_office_paths = [
    r'C:\Program Files\Microsoft Office\root\Office16\OMML2MML.XSL',
    r'C:\Program Files (x86)\Microsoft Office\root\Office16\OMML2MML.XSL',
    r'C:\Program Files\Microsoft Office\Office16\OMML2MML.XSL',
    r'C:\Program Files (x86)\Microsoft Office\Office16\OMML2MML.XSL',
    r'C:\Program Files\Microsoft Office\root\Office15\OMML2MML.XSL',
]

DEFAULT_OMML2MML_XSL = None
for _p in _office_paths:
    if _os.path.exists(_p):
        DEFAULT_OMML2MML_XSL = _p
        break
