# chuyen_doi.py - Bộ điều khiển chính: đọc Word, sinh LaTeX
#
# Lớp ChuyenDoiWordSangLatex đóng vai trò controller:
#   - Đọc file .docx (python-docx)
#   - Duyệt paragraph / table theo thứ tự xuất hiện
#   - Gọi module xu_ly_toan (OMML → LaTeX)
#   - Gọi module xu_ly_anh  (lọc ảnh trang trí / nội dung)
#   - Gọi module utils       (escape ký tự, biên dịch)
#   - Ghép nội dung vào template → file .tex đầu ra

import os
import re
import zipfile
import shutil
import tempfile

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table

from config import (
    OMML_NAMESPACE, W_NAMESPACE, OLE_NAMESPACE, VML_NAMESPACE,
    R_NAMESPACE, A_NAMESPACE, REL_NAMESPACE,
    WP_NAMESPACE, WP14_NAMESPACE,
    MAP_STYLE, HEADING_PATTERNS, DEFAULT_OMML2MML_XSL,
)
from xu_ly_anh import BoLocAnh
from xu_ly_bang import BoXuLyBang
from xu_ly_toan import BoXuLyToan
from xu_ly_ole_equation import ole_equation_to_latex
from utils import loc_ky_tu, bien_dich_latex, don_dep_file_rac


def chuyen_docm_sang_docx(duong_dan_docm: str) -> str:
    """Chuyển file .docm (macro-enabled) thành .docx bằng cách loại bỏ VBA macros.

    python-docx không hỗ trợ mở .docm trực tiếp vì content type khác.
    Hàm này mở .docm dưới dạng ZIP, bỏ vbaProject.bin, sửa [Content_Types].xml
    và các .rels, rồi lưu thành file .docx tạm.

    Returns:
        Đường dẫn file .docx tạm (caller cần tự dọn nếu muốn).
    """
    duong_dan_docx = duong_dan_docm.rsplit('.', 1)[0] + '_converted.docx'

    # Các file VBA cần loại bỏ (lowercase để so sánh)
    vba_files = {'vbaproject.bin', 'vbadata.xml'}

    with zipfile.ZipFile(duong_dan_docm, 'r') as zin:
        with zipfile.ZipFile(duong_dan_docx, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                ten_lower = item.filename.lower()
                # Bỏ qua file VBA macros
                ten_goc = os.path.basename(ten_lower)
                if ten_goc in vba_files:
                    continue
                du_lieu = zin.read(item.filename)

                # Sửa [Content_Types].xml: thay content type macro → docx thường
                if item.filename == '[Content_Types].xml':
                    du_lieu_str = du_lieu.decode('utf-8')
                    du_lieu_str = du_lieu_str.replace(
                        'application/vnd.ms-word.document.macroEnabled.main+xml',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
                    )
                    # Loại bỏ entry Override cho vbaProject / vbaData
                    du_lieu_str = re.sub(
                        r'<Override[^>]*(vbaProject|vbaData)[^>]*/>', '', du_lieu_str
                    )
                    du_lieu = du_lieu_str.encode('utf-8')

                # Sửa các file .rels: loại bỏ Relationship tới vbaProject
                elif ten_lower.endswith('.rels'):
                    du_lieu_str = du_lieu.decode('utf-8')
                    du_lieu_str = re.sub(
                        r'<Relationship[^>]*(vbaProject|vbaData)[^>]*/>', '', du_lieu_str
                    )
                    du_lieu = du_lieu_str.encode('utf-8')

                zout.writestr(item, du_lieu)

    return duong_dan_docx

class ChuyenDoiWordSangLatex:
    # Lớp chính chuyển đổi file Word (.docx) sang LaTeX (.tex)

    def __init__(self, duong_dan_word: str, duong_dan_template: str,
                 duong_dan_dau_ra: str, thu_muc_anh: str = 'images',
                 mode: str = 'demo', duong_dan_xslt_omml: str = None):
        # Khởi tạo các đường dẫn và trạng thái ban đầu
        self.duong_dan_word = duong_dan_word
        self.duong_dan_template = duong_dan_template
        self.duong_dan_dau_ra = duong_dan_dau_ra
        self.thu_muc_anh = thu_muc_anh
        self.mode = mode
        self.tai_lieu = None

        # Bộ đếm
        self.dem_anh = 0
        self.dem_bang = 0
        self.dem_heading1 = 0
        self.dem_paragraph_thuc = 0
        self.so_bang_noi_dung = 0

        # Trạng thái danh sách (itemize / enumerate)
        self.trang_thai_danh_sach = None
        self.danh_sach_numId = {}

        # Trạng thái vị trí
        self.da_qua_phan_noi_dung = False
        self.vi_tri_hien_tai = 0
        self.tong_so_phan_tu = 0
        self.toc_da_sinh = False
        self.kich_thuoc_anh_da_xem = []
        self.danh_sach_phan_tu = []
        # Tap hop chi muc cac doan van da dung lam caption con (bo qua khi duyet)
        self.cac_doan_da_dung = set()

        # Trạng thái xử lý title/author block (cho fallback %%CONTENT%%)
        self.da_co_maketitle = False
        self.dang_trong_abstract = False
        self.danh_sach_author = []   # Tạm lưu author + affil

        # --- Semantic Mapping: dữ liệu đã phân loại từ Word ---
        self.parsed_data = {
            'title': '',
            'abstract': '',
            'keywords': '',
            'body': '',
        }
        # Vùng ngữ nghĩa hiện tại khi duyệt: pre_title → title → abstract → keywords → body
        self._vung_hien_tai = 'pre_title'

        # Khởi tạo bộ xử lý toán (XSLT / Pandoc / parser thủ công)
        duong_dan_xslt = duong_dan_xslt_omml or DEFAULT_OMML2MML_XSL
        self.bo_toan = BoXuLyToan(duong_dan_xslt=duong_dan_xslt)

        # Khởi tạo bộ xử lý bảng (delegate để đảm bảo SRP)
        self.bo_bang = BoXuLyBang(self)

    # ĐỌC FILE

    def doc_template(self) -> str:
        # Đọc file template LaTeX và trả về nội dung dạng chuỗi
        with open(self.duong_dan_template, 'r', encoding='utf-8') as f:
            return f.read()

    def doc_file_word(self):
        # Đọc file Word (.docx / .docm) bằng python-docx
        if not os.path.exists(self.duong_dan_word):
            raise FileNotFoundError(f"Không tìm thấy file: {self.duong_dan_word}")

        duong_dan_thuc = self.duong_dan_word
        self._file_docm_tam = None  # Lưu đường dẫn tạm để dọn sau

        # Nếu file .docm (macro-enabled), chuyển sang .docx trước
        if self.duong_dan_word.lower().endswith('.docm'):
            try:
                duong_dan_thuc = chuyen_docm_sang_docx(self.duong_dan_word)
                self._file_docm_tam = duong_dan_thuc
                print(f"[INFO] Đã chuyển .docm → .docx: {duong_dan_thuc}")
            except Exception as e:
                raise RuntimeError(f"Lỗi chuyển đổi .docm sang .docx: {e}")

        try:
            self.tai_lieu = Document(duong_dan_thuc)
            return self.tai_lieu
        except Exception as e:
            raise RuntimeError(f"Lỗi mở file: {e}")

    # XỬ LÝ RUN (formatting: bold, italic, màu, highlight, hyperlink)

    def lay_mau_chu(self, run):
        # Lấy mã màu chữ (RGB) từ run, trả về chuỗi "r,g,b" hoặc None
        try:
            font = run.font
            if font.color and font.color.type == 1:
                rgb = font.color.rgb
                if rgb:
                    r = rgb[0] / 255.0
                    g = rgb[1] / 255.0
                    b = rgb[2] / 255.0
                    return f"{r:.3f},{g:.3f},{b:.3f}"
        except Exception:
            pass
        return None

    def lay_highlight(self, run) -> str:
        # Lấy màu highlight (nền) của run, trả về tên màu hoặc None
        try:
            if run.font.highlight_color is not None:
                map_mau = {
                    7: 'yellow', 4: 'green', 3: 'cyan',
                    5: 'magenta', 2: 'blue', 6: 'red', 16: 'lightgray',
                }
                return map_mau.get(run.font.highlight_color)
            rPr = run._element.rPr
            if rPr is not None:
                shd = rPr.find(qn('w:shd'))
                if shd is not None:
                    fill = shd.get(qn('w:fill'))
                    if fill and fill.upper() not in ('AUTO', 'FFFFFF', '000000', 'NONE'):
                        return 'yellow'
        except Exception:
            pass
        return None

    def lay_hyperlink(self, run) -> str:
        # Trích xuất URL hyperlink từ run (nếu run nằm trong w:hyperlink)
        try:
            parent = run._element.getparent()
            if parent is not None and parent.tag.endswith('}hyperlink'):
                rId = parent.get(qn('r:id'))
                if rId is None:
                    rId = parent.get(f'{{{R_NAMESPACE}}}id')
                if rId and self.tai_lieu:
                    rels = self.tai_lieu.part.rels
                    if rId in rels:
                        return rels[rId].target_ref
        except Exception:
            pass
        return None

    def lay_url_tu_hyperlink_elem(self, hyperlink_elem) -> str:
        # Lấy URL từ thẻ w:hyperlink dựa vào r:id và rels của document
        try:
            rId = hyperlink_elem.get(qn('r:id'))
            if rId is None:
                rId = hyperlink_elem.get(f'{{{R_NAMESPACE}}}id')
            if not rId or not self.tai_lieu:
                return None
            rels = self.tai_lieu.part.rels
            if rId in rels:
                return rels[rId].target_ref
        except Exception:
            pass
        return None

    def lay_tat_ca_hyperlink(self, doan_van) -> dict:
        # Trích xuất tất cả hyperlink từ đoạn văn, trả về dict {text: url}
        hyperlinks = {}
        try:
            for hyperlink_elem in doan_van._element.findall(f'.//{{{W_NAMESPACE}}}hyperlink'):
                url = self.lay_url_tu_hyperlink_elem(hyperlink_elem)
                if not url:
                    continue
                text_parts = []
                for t_elem in hyperlink_elem.findall(f'.//{{{W_NAMESPACE}}}t'):
                    if t_elem.text:
                        text_parts.append(t_elem.text)
                link_text = ''.join(text_parts).strip()
                if link_text:
                    hyperlinks[link_text] = url
        except Exception:
            pass
        return hyperlinks

    def xu_ly_run_thuong(self, run) -> str:
        # Xử lý một run thường (không tự bọc hyperlink), giữ bold/italic/màu/highlight
        van_ban = run.text
        if not van_ban:
            return ""

        ket_qua = loc_ky_tu(van_ban)

        mau = self.lay_mau_chu(run)
        highlight = self.lay_highlight(run)
        dam = run.bold
        nghieng = run.italic

        if dam:
            ket_qua = r"\textbf{" + ket_qua + "}"
        if nghieng:
            ket_qua = r"\textit{" + ket_qua + "}"
        if highlight:
            ket_qua = rf"\colorbox{{{highlight}}}{{{ket_qua}}}"
        if mau:
            ket_qua = rf"\textcolor[rgb]{{{mau}}}{{{ket_qua}}}"

        return ket_qua

    def xu_ly_noi_dung_doan_van(self, doan_van) -> str:
        # Dựng nội dung paragraph theo XML để bắt hyperlink đúng chuẩn Word
        run_map = {id(run._element): run for run in doan_van.runs}
        ket_qua = ""

        try:
            for child in list(doan_van._element):
                tag = child.tag.split('}')[-1] if hasattr(child, 'tag') else ''
                if tag == 'hyperlink':
                    url = self.lay_url_tu_hyperlink_elem(child)
                    if not url:
                        continue
                    url_escaped = url.replace('%', '\\%').replace('#', '\\#')
                    noi_dung_link = ""
                    for r_elem in child.findall(f'.//{{{W_NAMESPACE}}}r'):
                        # Ưu tiên: dùng run_map nếu có, fallback đọc XML trực tiếp
                        run_obj = run_map.get(id(r_elem))
                        if run_obj is not None:
                            van_ban = run_obj.text
                            if van_ban:
                                formatted = loc_ky_tu(van_ban)
                                if run_obj.bold:
                                    formatted = r"\textbf{" + formatted + "}"
                                if run_obj.italic:
                                    formatted = r"\textit{" + formatted + "}"
                                noi_dung_link += formatted
                        else:
                            # Fallback: đọc text trực tiếp từ XML <w:t> elements
                            for t_elem in r_elem.findall(f'.//{{{W_NAMESPACE}}}t'):
                                if t_elem.text:
                                    formatted = loc_ky_tu(t_elem.text)
                                    # Kiểm tra bold/italic qua XML <w:rPr>
                                    rPr = r_elem.find(f'{{{W_NAMESPACE}}}rPr')
                                    if rPr is not None:
                                        if rPr.find(f'{{{W_NAMESPACE}}}b') is not None:
                                            formatted = r"\textbf{" + formatted + "}"
                                        if rPr.find(f'{{{W_NAMESPACE}}}i') is not None:
                                            formatted = r"\textit{" + formatted + "}"
                                    noi_dung_link += formatted
                    # Nếu display text vẫn rỗng, dùng URL đầy đủ (không rút gọn)
                    if not noi_dung_link.strip():
                        noi_dung_link = loc_ky_tu(url)
                    ket_qua += rf"\href{{{url_escaped}}}{{\textcolor{{blue}}{{{noi_dung_link}}}}}"
                elif tag == 'r':
                    run_obj = run_map.get(id(child))
                    if run_obj is not None:
                        ket_qua += self.xu_ly_run_thuong(run_obj)
        except Exception:
            ket_qua = "".join(self.xu_ly_run_thuong(run) for run in doan_van.runs)

        return ket_qua

    def xu_ly_run(self, run) -> str:
        # Xử lý một run: escape ký tự + áp dụng bold/italic/màu/highlight/hyperlink
        van_ban = run.text
        if not van_ban:
            return ""

        ket_qua = loc_ky_tu(van_ban)

        mau = self.lay_mau_chu(run)
        highlight = self.lay_highlight(run)
        dam = run.bold
        nghieng = run.italic

        if dam:
            ket_qua = r"\textbf{" + ket_qua + "}"
        if nghieng:
            ket_qua = r"\textit{" + ket_qua + "}"
        if highlight:
            ket_qua = rf"\colorbox{{{highlight}}}{{{ket_qua}}}"
        if mau:
            ket_qua = rf"\textcolor[rgb]{{{mau}}}{{{ket_qua}}}"

        return ket_qua

    def bat_caption_bang(self) -> str:
        # Bắt caption thật của bảng từ paragraph ngay phía trên
        try:
            idx_truoc = self.vi_tri_hien_tai - 1
            if idx_truoc < 0 or idx_truoc >= len(self.danh_sach_phan_tu):
                return None
            loai, phan_tu = self.danh_sach_phan_tu[idx_truoc]
            if loai != 'paragraph':
                return None
            text = phan_tu.text.strip()
            if not text:
                return None
            if re.match(r'^(BẢNG|BANG|TABLE)\b', text.strip(), re.IGNORECASE):
                self.cac_doan_da_dung.add(idx_truoc)
                caption_text = loc_ky_tu(text)
                # Strip prefix "Table X:" / "Bảng X." để tránh duplicate với LaTeX tự sinh
                caption_text = re.sub(
                    r'^(Bảng|Bảng|Table|TABLE|Bang|BANG)\s*\d+\s*[:\.\-–—]?\s*',
                    '', caption_text, flags=re.IGNORECASE
                ).strip()
                return caption_text
        except Exception:
            pass
        return None

    def bat_caption_hinh(self) -> str:
        # Bắt caption thật của hình từ paragraph phía dưới (tìm tối đa 5 đoạn)
        try:
            for buoc in range(1, 6):
                idx_sau = self.vi_tri_hien_tai + buoc
                if idx_sau < 0 or idx_sau >= len(self.danh_sach_phan_tu):
                    break
                loai, phan_tu = self.danh_sach_phan_tu[idx_sau]
                # Dừng nếu gặp bảng hoặc phần tử không phải paragraph
                if loai == 'table':
                    break
                if loai != 'paragraph':
                    continue
                text = phan_tu.text.strip()
                if not text:
                    continue
                if re.match(r'^(HÌNH|HINH|ẢNH|ANH|FIGURE|FIG)\b', text.strip(), re.IGNORECASE):
                    self.cac_doan_da_dung.add(idx_sau)
                    caption_text = loc_ky_tu(text)
                    # Strip prefix "Hình X." / "Figure X:" / "Fig. 1:" để tránh duplicate với LaTeX tự sinh
                    caption_text = re.sub(
                        r'^(Hình|Figure|Fig\.?)\s*\d+\s*[:\.\-–—]?\s*',
                        '', caption_text, flags=re.IGNORECASE
                    ).strip()
                    return caption_text
                # Dừng nếu gặp section heading mới
                if hasattr(phan_tu, 'style') and phan_tu.style and phan_tu.style.name and 'Heading' in phan_tu.style.name:
                    break
        except Exception:
            pass
        return None

    # DANH SÁCH (itemize / enumerate)

    def lay_thong_tin_danh_sach(self, doan_van):
        # Lấy numId và ilvl từ paragraph properties (danh sách đánh số/gạch đầu dòng)
        pPr = doan_van._element.pPr
        if pPr is None:
            return None, 0
        numPr = pPr.numPr
        if numPr is None:
            return None, 0

        numId_elem = numPr.find(qn('w:numId'))
        ilvl_elem = numPr.find(qn('w:ilvl'))

        numId = numId_elem.get(qn('w:val')) if numId_elem is not None else None
        ilvl = int(ilvl_elem.get(qn('w:val'))) if ilvl_elem is not None else 0
        return numId, ilvl

    def xac_dinh_loai_danh_sach(self, numId: str) -> str:
        # Xác định loại danh sách (itemize mặc định) từ numId
        if numId in self.danh_sach_numId:
            return self.danh_sach_numId[numId]
        self.danh_sach_numId[numId] = 'itemize'
        return 'itemize'

    def mo_danh_sach(self, loai):
        # Sinh lệnh \begin{loai} mở đầu danh sách
        return rf"\begin{{{loai}}}" + "\n"

    def dong_danh_sach(self, loai):
        # Sinh lệnh \end{loai} kết thúc danh sách
        return rf"\end{{{loai}}}" + "\n"

    def dong_danh_sach_hien_tai(self) -> str:
        # Đóng tất cả danh sách đang mở (nhiều cấp)
        if self.trang_thai_danh_sach:
            loai, cap = self.trang_thai_danh_sach
            self.trang_thai_danh_sach = None
            latex = ""
            for _ in range(cap + 1):
                latex += self.dong_danh_sach(loai)
            return latex
        return ""

    def xu_ly_doan_van(self, doan_van, che_do_inline: bool = False) -> str:
        # Xử lý đoạn văn; tự động inline ảnh nhỏ (icon) nếu đoạn có text dài kèm ảnh
        ten_style = doan_van.style.name
        text_raw = doan_van.text.strip().upper()
        text_goc = doan_van.text.strip()

        if len(text_raw) > 0:
            self.dem_paragraph_thuc += 1

        # === XỬ LÝ STYLE ACM ĐẶC BIỆT (trước khi xử lý chung) ===
        style_cmd = MAP_STYLE.get(ten_style, '')

        # Style None → bỏ qua hoàn toàn (CCS, Keywords metadata, ORCID...)
        if style_cmd is None:
            return ""

        # Style \title → tạo \title{...} + \date{} (ẩn ngày tự động)
        if style_cmd == r'\title':
            noi_dung = self.xu_ly_noi_dung_doan_van(doan_van)
            if noi_dung.strip():
                return f"\\title{{{noi_dung.strip()}}}\n\\date{{}}\n"
            return ""

        # Style \subtitle → tạo \subtitle{...} (nếu template hỗ trợ)
        if style_cmd == r'\subtitle':
            noi_dung = self.xu_ly_noi_dung_doan_van(doan_van)
            if noi_dung.strip():
                return f"% Subtitle: {noi_dung.strip()}\n"
            return ""

        # Style \author → thu thập author
        if style_cmd == r'\author':
            if text_goc:
                self.danh_sach_author.append(('author', text_goc))
            return ""

        # Style \affil → thu thập affiliation
        if style_cmd == r'\affil':
            if text_goc:
                self.danh_sach_author.append(('affil', text_goc))
            return ""

        # Style \abstract → bắt đầu/tiếp tục abstract block
        if style_cmd == r'\abstract':
            noi_dung = self.xu_ly_noi_dung_doan_van(doan_van)
            if not self.dang_trong_abstract:
                self.dang_trong_abstract = True
                # Xuất author block + \maketitle TRƯỚC abstract
                ket_qua = self._xuat_author_block()
                if not self.da_co_maketitle:
                    ket_qua += "\\maketitle\n\n"
                    self.da_co_maketitle = True
                ket_qua += "\\begin{abstract}\n"
                ket_qua += noi_dung.strip() + "\n"
                return ket_qua
            else:
                return noi_dung.strip() + "\n"

        # Khi gặp style khác mà đang trong abstract → đóng abstract
        if self.dang_trong_abstract:
            self.dang_trong_abstract = False
            prefix = "\\end{abstract}\n\n"
        else:
            prefix = ""

        # === XỬ LÝ DISPLAY EQUATION (DisplayFormula / DisplayFormulaUnnum) ===
        if style_cmd in ('equation', 'equation*'):
            cong_thuc_list = self.bo_toan.trich_xuat_omml(doan_van)
            if cong_thuc_list:
                latex_parts = [lt for _, lt in cong_thuc_list if lt.strip()]
                if latex_parts:
                    latex_math = ' '.join(latex_parts)
                    if style_cmd == 'equation':
                        return prefix + f"\\begin{{equation}}\n{latex_math}\n\\end{{equation}}\n\n"
                    else:
                        return prefix + f"\\[\n{latex_math}\n\\]\n\n"
            # Fallback: nếu không trích xuất được OMML, xuất text thường
            noi_dung = self.xu_ly_noi_dung_doan_van(doan_van)
            if noi_dung.strip():
                return prefix + noi_dung + "\n\n"
            return prefix

        # === XỬ LÝ BIB_ENTRY (References) ===
        if style_cmd == 'bibitem':
            noi_dung = self.xu_ly_noi_dung_doan_van(doan_van)
            if not noi_dung.strip():
                return ""
            ket_qua_bib = ""
            if not hasattr(self, 'dang_trong_bibliography') or not self.dang_trong_bibliography:
                self.dang_trong_bibliography = True
                self.dem_bib = 0
                ket_qua_bib = prefix + "\\begin{thebibliography}{99}\n\n"
            self.dem_bib += 1
            ket_qua_bib += f"\\bibitem{{ref{self.dem_bib}}} {noi_dung.strip()}\n\n"
            return ket_qua_bib

        # === ĐÓNG BIBLIOGRAPHY nếu rời Bib_entry ===
        if hasattr(self, 'dang_trong_bibliography') and self.dang_trong_bibliography:
            # Bỏ qua paragraph trống (không đóng bibliography vì có thể chỉ là gap)
            if not text_goc.strip():
                return ""
            # Chỉ đóng khi gặp heading hoặc nội dung thực sự (không phải Normal trống)
            if style_cmd != 'bibitem':
                self.dang_trong_bibliography = False
                prefix = "\\end{thebibliography}\n\n" + prefix

        # Khi gặp heading đầu tiên mà chưa có \maketitle → chèn
        if not self.da_co_maketitle and style_cmd in (r'\section', r'\subsection', r'\subsubsection'):
            pre = self._xuat_author_block()
            pre += "\\maketitle\n\n"
            self.da_co_maketitle = True
            prefix = pre + prefix

        # Phát hiện TOC text
        if 'TABLE OF CONTENTS' in text_raw or 'MỤC LỤC' in text_raw:
            if not self.toc_da_sinh and len(text_raw) < 50:
                self.toc_da_sinh = True
                return prefix + r"\tableofcontents" + "\n\\newpage\n\n"
            return prefix

        # Phát hiện phần nội dung chính (sau abstract/introduction)
        if not self.da_qua_phan_noi_dung:
            cac_tu_khoa = ['ABSTRACT', 'INTRODUCTION', 'TÓM TẮT',
                           'GIỚI THIỆU', 'MỞ ĐẦU', 'CHƯƠNG 1']
            for tu in cac_tu_khoa:
                if tu in text_raw:
                    self.da_qua_phan_noi_dung = True
                    break

        # Xử lý nội dung theo XML để bắt đúng hyperlink
        noi_dung = self.xu_ly_noi_dung_doan_van(doan_van)

        # Trích xuất ảnh và danh sách thông tin
        danh_sach_anh, danh_sach_kich_thuoc = self.trich_xuat_anh(doan_van)
        numId, ilvl = self.lay_thong_tin_danh_sach(doan_van)

        # Tự động bật chế độ inline nếu có ảnh nhỏ (icon/decorative)
        if not che_do_inline and danh_sach_anh:
            # Kiểm tra nếu tất cả ảnh đều nhỏ (< 1.5 inch = 1,371,600 EMU) → inline
            tat_ca_anh_nho = all(
                (rong < 1371600 and cao < 1371600) 
                for rong, cao in danh_sach_kich_thuoc
            )
            if tat_ca_anh_nho or len(text_goc) > 20:
                che_do_inline = True

        ket_qua = ""

        if che_do_inline:
            cong_thuc_list = self.bo_toan.trich_xuat_omml(doan_van)
            for text_goc_ct, latex_ct in cong_thuc_list:
                if latex_ct.strip():
                    noi_dung = noi_dung.replace(text_goc_ct, f'${latex_ct}$')

            ket_qua_inline = []
            if danh_sach_anh:
                ten_thu_muc = os.path.basename(self.thu_muc_anh)
                for ten_anh in danh_sach_anh:
                    ket_qua_inline.append(
                        rf"\includegraphics[height=1.2em]{{{ten_thu_muc}/{ten_anh}}}"
                    )

            if noi_dung.strip():
                ket_qua_inline.append(noi_dung)

            return " ".join(ket_qua_inline)

        # Nhieu anh trong 1 doan -> gom thanh subfigure
        if len(danh_sach_anh) > 1:
            caption_con = self.trich_xuat_caption_con()
            if caption_con:
                self.cac_doan_da_dung.add(self.vi_tri_hien_tai + 1)
            caption_chinh = self.bat_caption_hinh()
            ket_qua += self.tao_latex_nhom_hinh(danh_sach_anh, caption_con, caption_chinh)
        else:
            for ten_anh in danh_sach_anh:
                caption_chinh = self.bat_caption_hinh()
                ket_qua += self.tao_latex_hinh(ten_anh, caption_chinh)

        # Xử lý danh sách
        if numId is not None:
            loai = self.xac_dinh_loai_danh_sach(numId)
            if self.trang_thai_danh_sach is None:
                for _ in range(ilvl + 1):
                    ket_qua += self.mo_danh_sach(loai)
                self.trang_thai_danh_sach = (loai, ilvl)
            else:
                loai_cu, cap_cu = self.trang_thai_danh_sach
                if ilvl > cap_cu:
                    for _ in range(cap_cu + 1, ilvl + 1):
                        ket_qua += self.mo_danh_sach(loai)
                elif ilvl < cap_cu:
                    for _ in range(cap_cu - ilvl):
                        ket_qua += self.dong_danh_sach(loai_cu)
                self.trang_thai_danh_sach = (loai, ilvl)
            ket_qua += r"\item " + noi_dung + "\n"
        else:
            ket_qua += self.dong_danh_sach_hien_tai()
            if not noi_dung.strip():
                return ket_qua

            # Xử lý OMML math (thay text gốc bằng inline $...$)
            cong_thuc_list = self.bo_toan.trich_xuat_omml(doan_van)
            for text_goc_ct, latex_ct in cong_thuc_list:
                if latex_ct.strip():
                    noi_dung = noi_dung.replace(text_goc_ct, f'${latex_ct}$')

            # Xác định heading (từ style hoặc từ nội dung)
            lenh_latex = MAP_STYLE.get(ten_style, '')

            if not lenh_latex:
                # Chỉ phát hiện heading từ content khi:
                # 1. Style chưa được map (lenh_latex rỗng)
                # 2. Style gốc là Normal hoặc không rõ (tránh false positive)
                # 3. Paragraph chỉ chứa text ngắn (heading, không phải body text)
                if ten_style in ('Normal', '', None) and len(text_goc.strip()) < 80:
                    heading_cmd, _ = self.phat_hien_heading(text_goc)
                    if heading_cmd:
                        lenh_latex = heading_cmd

            # Dùng starred heading (*) chỉ khi nội dung đã có số đầu dòng
            if lenh_latex and lenh_latex in (r'\section', r'\subsection',
                                             r'\subsubsection', r'\paragraph'):
                if (re.match(r'^[\d\.]+\s*[A-Za-zÀ-ỹ]', text_goc)
                        or re.match(r'^(CHƯƠNG|CHAPTER)\s*\d', text_goc, re.IGNORECASE)):
                    lenh_latex = lenh_latex + '*'

            if lenh_latex:
                if lenh_latex is None:
                    return prefix + ket_qua
                # ComputerCode → dùng \texttt thay vì verbatim{...}
                if lenh_latex == 'verbatim':
                    ket_qua += f"\\texttt{{{noi_dung}}}" + "\n\n"
                else:
                    ket_qua += f"{lenh_latex}{{{noi_dung}}}" + "\n\n"
            else:
                ket_qua += f"{noi_dung}\n\n"

            ket_qua = prefix + ket_qua

        return ket_qua

    def tao_latex_hinh(self, ten_anh: str, caption: str = None) -> str:
        # Sinh mã LaTeX figure cho ảnh (includegraphics + caption + label)
        label = f"fig:hinh{self.dem_anh}"
        ten_thu_muc = os.path.basename(self.thu_muc_anh)
        vi_tri = "[H]" if self.mode == 'demo' else "[htbp]"
        latex = rf"\begin{{figure}}{vi_tri}" + "\n"
        latex += r"  \centering" + "\n"
        latex += rf"  \includegraphics[width=0.6\linewidth]{{{ten_thu_muc}/{ten_anh}}}" + "\n"
        caption_final = caption or ""
        # Strip prefix "Hình X." / "Figure X:" nếu còn sót
        caption_final = re.sub(
            r'^(Hình|Figure|Fig\.?)\s*\d+\s*[:\.\-–—]?\s*',
            '', caption_final, flags=re.IGNORECASE
        ).strip()
        latex += rf"  \caption{{{caption_final}}}" + "\n"
        latex += rf"  \label{{{label}}}" + "\n"
        latex += r"\end{figure}" + "\n\n"
        return latex

    def tao_latex_nhom_hinh(self, danh_sach_anh: list, danh_sach_caption: list = None, caption: str = None) -> str:
        # Gom nhieu anh thanh 1 figure nam ngang
        if not danh_sach_anh:
            return ""
        ten_thu_muc = os.path.basename(self.thu_muc_anh)
        vi_tri = "[H]" if self.mode == 'demo' else "[htbp]"
        so_anh = len(danh_sach_anh)
        do_rong = f"{0.9 / so_anh:.2f}" if so_anh > 1 else "0.48"

        # Kiem tra co caption con khong (Word co label (a),(b) khong)
        co_caption_con = danh_sach_caption and len(danh_sach_caption) > 0

        latex = rf"\begin{{figure}}{vi_tri}" + "\n"
        latex += r"  \centering" + "\n"

        if co_caption_con:
            # Co caption con -> dung subfigure
            for i, ten_anh in enumerate(danh_sach_anh):
                mo_ta = ""
                if i < len(danh_sach_caption):
                    mo_ta = re.sub(r'^\([a-z]\)\s*', '', danh_sach_caption[i]).strip()
                nhan = chr(ord('a') + i)

                latex += rf"  \begin{{subfigure}}[b]{{{do_rong}\textwidth}}" + "\n"
                latex += r"    \centering" + "\n"
                latex += rf"    \includegraphics[width=\linewidth]{{{ten_thu_muc}/{ten_anh}}}" + "\n"
                latex += rf"    \caption{{{mo_ta}}}" + "\n"
                latex += rf"    \label{{fig:hinh{self.dem_anh - so_anh + i + 1}_{nhan}}}" + "\n"
                latex += r"  \end{subfigure}" + "\n"
                if i < so_anh - 1:
                    latex += r"  \hfill" + "\n"
        else:
            # Khong co caption con -> layout don gian (khong subfigure, khong (a)(b)(c)(d))
            for i, ten_anh in enumerate(danh_sach_anh):
                latex += rf"  \includegraphics[width={do_rong}\linewidth]{{{ten_thu_muc}/{ten_anh}}}" + "\n"
                if i < so_anh - 1:
                    latex += r"  \hfill" + "\n"

        caption_final = caption or ""
        caption_final = re.sub(
            r'^(Hình|Figure|Fig\.?)\s*\d+\s*[:\.\-–—]?\s*',
            '', caption_final, flags=re.IGNORECASE
        ).strip()
        latex += rf"  \caption{{{caption_final}}}" + "\n"
        latex += rf"  \label{{fig:nhom{self.dem_anh}}}" + "\n"
        latex += r"\end{figure}" + "\n\n"
        return latex

    def trich_xuat_caption_con(self) -> list:
        # Tim caption con (a), (b)... tu doan van ngay phia duoi
        danh_sach = []
        try:
            vi_tri_ke = self.vi_tri_hien_tai + 1
            if vi_tri_ke < len(self.danh_sach_phan_tu):
                loai_ke, phan_tu_ke = self.danh_sach_phan_tu[vi_tri_ke]
                if loai_ke == 'paragraph':
                    text_ke = phan_tu_ke.text.strip()
                    # Nhan dien pattern (a) mo ta, (b) mo ta...
                    ket_qua = re.findall(r'\(([a-z])\)\s*([^(]*)', text_ke)
                    if ket_qua:
                        for nhan, mo_ta in ket_qua:
                            caption = f"({nhan})"
                            if mo_ta.strip():
                                caption += f" {mo_ta.strip()}"
                            danh_sach.append(loc_ky_tu(caption))
        except Exception:
            pass
        return danh_sach

    # ẢNH: trích xuất, lọc, tạo LaTeX

    def lay_kich_thuoc_anh(self, run_element):
        # Lấy kích thước ảnh (cx, cy) đơn vị EMU từ XML element
        try:
            extent = run_element.find(f'.//{{{WP_NAMESPACE}}}extent')
            if extent is None:
                extent = run_element.find(f'.//{{{WP14_NAMESPACE}}}extent')
            if extent is not None:
                cx = int(extent.get('cx', 0))
                cy = int(extent.get('cy', 0))
                return (cx, cy)
        except Exception:
            pass
        return (0, 0)

    def la_anh_trang_tri(self, kich_thuoc_anh, doan_van) -> bool:
        # Ủy quyền cho BoLocAnh kiểm tra ảnh trang trí (metadata + context)
        return BoLocAnh.la_anh_trang_tri(
            kich_thuoc_anh, doan_van,
            da_qua_phan_noi_dung=self.da_qua_phan_noi_dung,
            dem_paragraph_thuc=self.dem_paragraph_thuc,
            tong_so_phan_tu=self.tong_so_phan_tu,
            vi_tri_hien_tai=self.vi_tri_hien_tai,
            kich_thuoc_anh_da_xem=self.kich_thuoc_anh_da_xem,
        )

    def trich_xuat_anh(self, doan_van) -> tuple:
        # Trích xuất ảnh từ paragraph, lọc ảnh trang trí và lưu vào thư mục ảnh
        # Trả về tuple(danh_sach_anh, danh_sach_kich_thuoc)
        danh_sach_anh = []
        danh_sach_kich_thuoc = []
        if not self.tai_lieu:
            return danh_sach_anh, danh_sach_kich_thuoc

        tong_so_anh = sum(
            1 for run in doan_van.runs
            for _ in run._element.findall(f'.//{{{A_NAMESPACE}}}blip')
        )
        if tong_so_anh > 3:
            return danh_sach_anh, danh_sach_kich_thuoc

        for run in doan_van.runs:
            blips = run._element.findall(f'.//{{{A_NAMESPACE}}}blip')
            if not blips:
                continue

            kich_thuoc = self.lay_kich_thuoc_anh(run._element)
            rong, cao = kich_thuoc

            if rong == 0 or cao == 0:
                continue
            if rong < 300000 and cao < 300000:
                continue
            if rong > 7000000 or cao > 9000000:
                continue

            for blip in blips:
                embed = blip.get(f'{{{REL_NAMESPACE}}}embed')
                if not embed:
                    continue

                part = self.tai_lieu.part.related_parts.get(embed)
                if not part:
                    continue

                self.dem_anh += 1
                content_type = getattr(part, 'content_type', '')
                ext = 'png'
                if 'jpeg' in content_type:
                    ext = 'jpg'

                ten_anh = f'hinh_{self.dem_anh}.{ext}'
                if not os.path.exists(self.thu_muc_anh):
                    os.makedirs(self.thu_muc_anh)

                duong_dan_anh = os.path.join(self.thu_muc_anh, ten_anh)
                with open(duong_dan_anh, 'wb') as f:
                    f.write(part.blob)
                
                # Kiểm tra file ảnh có hợp lệ không
                if not os.path.exists(duong_dan_anh) or os.path.getsize(duong_dan_anh) == 0:
                    continue
                
                # Kiểm tra ảnh có thể mở được bằng PIL
                try:
                    from PIL import Image
                    img = Image.open(duong_dan_anh)
                    width, height = img.size
                    # Nếu ảnh có kích thước 0, bỏ qua
                    if width == 0 or height == 0:
                        os.remove(duong_dan_anh)
                        self.dem_anh -= 1
                        continue
                except Exception:
                    # Nếu không mở được ảnh, xóa file và bỏ qua
                    try:
                        os.remove(duong_dan_anh)
                        self.dem_anh -= 1
                    except:
                        pass
                    continue

                if self.la_anh_trang_tri(kich_thuoc, doan_van):
                    try:
                        os.remove(duong_dan_anh)
                        self.dem_anh -= 1
                    except Exception:
                        pass
                    continue

                if not BoLocAnh.la_anh_noi_dung(duong_dan_anh):
                    try:
                        os.remove(duong_dan_anh)
                        self.dem_anh -= 1
                    except Exception:
                        pass
                    continue

                danh_sach_anh.append(ten_anh)
                danh_sach_kich_thuoc.append(kich_thuoc)
        return danh_sach_anh, danh_sach_kich_thuoc

    def trich_xuat_anh_tu_bang(self, bang: Table) -> list:
        # Trích xuất ảnh từ bảng (figure layout), luôn giữ ảnh
        danh_sach_anh = []
        if not self.tai_lieu:
            return danh_sach_anh

        for hang in bang.rows:
            for cell in hang.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        blips = run._element.findall(f'.//{{{A_NAMESPACE}}}blip')
                        for blip in blips:
                            embed = blip.get(f'{{{REL_NAMESPACE}}}embed')
                            if not embed:
                                continue
                            part = self.tai_lieu.part.related_parts.get(embed)
                            if not part:
                                continue

                            self.dem_anh += 1
                            content_type = getattr(part, 'content_type', '')
                            ext = 'png'
                            if 'jpeg' in content_type:
                                ext = 'jpg'

                            ten_anh = f'hinh_{self.dem_anh}.{ext}'
                            if not os.path.exists(self.thu_muc_anh):
                                os.makedirs(self.thu_muc_anh)

                            duong_dan_anh = os.path.join(self.thu_muc_anh, ten_anh)
                            with open(duong_dan_anh, 'wb') as f:
                                f.write(part.blob)

                            danh_sach_anh.append(ten_anh)
        return danh_sach_anh

    # OLE OBJECT (Equation Editor cũ)

    def trich_xuat_ole_cong_thuc(self, doan_van) -> list:
        # Trích xuất công thức từ OLE Object (Equation Editor)
        # Ưu tiên parse MTEF → LaTeX, fallback → trích ảnh
        danh_sach_cong_thuc = []
        if not self.tai_lieu:
            return danh_sach_cong_thuc

        try:
            objects = doan_van._element.findall(f'.//{{{W_NAMESPACE}}}object')
            for obj in objects:
                ole = obj.find(f'.//{{{OLE_NAMESPACE}}}OLEObject')
                if ole is None:
                    continue

                # Thử parse MTEF → LaTeX
                ole_rid = ole.get(f'{{{R_NAMESPACE}}}id')
                if ole_rid:
                    ole_part = self.tai_lieu.part.related_parts.get(ole_rid)
                    if ole_part:
                        try:
                            latex_result = ole_equation_to_latex(ole_part.blob)
                            if latex_result.strip():
                                # Trả về LaTeX string (đánh dấu bằng prefix $...$)
                                danh_sach_cong_thuc.append(f'$${latex_result}$$')
                                continue
                        except Exception:
                            pass

                # Fallback: trích xuất ảnh
                imagedata = obj.find(f'.//{{{VML_NAMESPACE}}}imagedata')
                if imagedata is None:
                    continue

                rid = imagedata.get(f'{{{R_NAMESPACE}}}id')
                if not rid:
                    continue

                part = self.tai_lieu.part.related_parts.get(rid)
                if not part:
                    continue

                self.dem_anh += 1
                content_type = getattr(part, 'content_type', '')
                ext = 'png'
                if 'wmf' in content_type or 'x-wmf' in content_type:
                    ext = 'wmf'
                elif 'emf' in content_type or 'x-emf' in content_type:
                    ext = 'emf'
                elif 'jpeg' in content_type:
                    ext = 'jpg'

                ten_anh = f'formula_{self.dem_anh}.{ext}'
                if not os.path.exists(self.thu_muc_anh):
                    os.makedirs(self.thu_muc_anh)

                duong_dan_anh = os.path.join(self.thu_muc_anh, ten_anh)
                with open(duong_dan_anh, 'wb') as f:
                    f.write(part.blob)

                danh_sach_cong_thuc.append(ten_anh)
        except Exception:
            pass

        return danh_sach_cong_thuc

    def xu_ly_bang(self, bang: Table) -> str:
        # Ủy quyền xử lý bảng cho BoXuLyBang để đảm bảo SRP
        return self.bo_bang.xu_ly_bang(bang)

    def _xuat_author_block(self) -> str:
        """Xuất block author/affil đã thu thập thành LaTeX."""
        if not self.danh_sach_author:
            return ""
        ket_qua = ""
        for loai, text in self.danh_sach_author:
            if loai == 'author':
                ket_qua += f"\\author{{{text}}}\n"
            elif loai == 'affil':
                ket_qua += f"\\affil{{{text}}}\n"
        self.danh_sach_author = []  # Reset sau khi xuất
        return ket_qua

    # HEADING: phát hiện từ style và nội dung

    def phat_hien_heading(self, text: str) -> tuple:
        # Phát hiện heading từ nội dung (khi Word không gán style)
        text_strip = text.strip()
        for pattern, latex_cmd in HEADING_PATTERNS:
            match = re.match(pattern, text_strip, re.IGNORECASE)
            if match:
                return (latex_cmd, text_strip)
        return (None, None)

    # FLOW CHÍNH: duyệt document → sinh nội dung → ghép template

    def lay_thu_tu_phan_tu(self):
        # Lấy danh sách phần tử (paragraph / table) theo thứ tự trong body
        body = self.tai_lieu.element.body
        thu_tu = []
        for phan_tu in body:
            tag = phan_tu.tag.split('}')[-1]
            if tag == 'p':
                from docx.text.paragraph import Paragraph
                thu_tu.append(('paragraph', Paragraph(phan_tu, self.tai_lieu)))
            elif tag == 'tbl':
                thu_tu.append(('table', Table(phan_tu, self.tai_lieu)))
        return thu_tu

    def _tim_caption_con_trong_bang(self, bang: Table) -> list:
        # Tim text caption con (a), (b)... trong cac cell cua bang
        danh_sach = []
        try:
            for hang in bang.rows:
                for cell in hang.cells:
                    text = cell.text.strip()
                    # Cell chi chua label ngan dang (a), (b)...
                    match = re.match(r'^\(([a-z])\)(.*)$', text)
                    if match:
                        nhan = match.group(1)
                        mo_ta = match.group(2).strip()
                        caption = f"({nhan})"
                        if mo_ta:
                            caption += f" {mo_ta}"
                        danh_sach.append(caption)
        except Exception:
            pass
        return danh_sach

    def sinh_noi_dung(self) -> str:
        # Duyệt toàn bộ phần tử và sinh nội dung LaTeX (dùng cho fallback %%CONTENT%%)
        self.doc_file_word()
        noi_dung = []
        thu_tu_phan_tu = self.lay_thu_tu_phan_tu()
        self.tong_so_phan_tu = len(thu_tu_phan_tu)
        # Luu danh sach de cac ham khac co the nhin truoc/sau
        self.danh_sach_phan_tu = thu_tu_phan_tu

        # Pre-scan: đánh dấu các paragraph là caption bảng (nằm ngay trước table)
        for idx, (loai, phan_tu) in enumerate(thu_tu_phan_tu):
            if loai == 'table' and idx > 0:
                loai_truoc, pt_truoc = thu_tu_phan_tu[idx - 1]
                if loai_truoc == 'paragraph':
                    text_truoc = pt_truoc.text.strip()
                    if text_truoc and re.match(r'^(BẢNG|BANG|TABLE)\b', text_truoc, re.IGNORECASE):
                        self.cac_doan_da_dung.add(idx - 1)

        for idx, (loai, phan_tu) in enumerate(thu_tu_phan_tu):
            self.vi_tri_hien_tai = idx
            # Bo qua doan van da dung lam caption con cho subfigure
            if idx in self.cac_doan_da_dung:
                continue
            if loai == 'paragraph':
                ket_qua = self.xu_ly_doan_van(phan_tu)
                if ket_qua:
                    noi_dung.append(ket_qua)
            elif loai == 'table':
                noi_dung.append(self.dong_danh_sach_hien_tai())
                ket_qua = self.xu_ly_bang(phan_tu)
                if ket_qua:
                    noi_dung.append(ket_qua)

        noi_dung.append(self.dong_danh_sach_hien_tai())
        return ''.join(noi_dung)

    # =====================================================================
    # SEMANTIC MAPPING: Phân loại nội dung Word → Tiêm vào template LaTeX
    # =====================================================================

    def _la_doan_title(self, doan_van, idx: int) -> bool:
        """Heuristic: đoạn văn nằm trong 10 phần tử đầu, chữ to/đậm/canh giữa → Title."""
        if idx >= 10:
            return False
        text = doan_van.text.strip()
        if not text or len(text) < 3:
            return False

        # Style tên "Title" hoặc "Title_document" do Word gán
        ten_style = doan_van.style.name
        if ten_style and ten_style.lower() in ('title', 'title_document'):
            return True
        # Kiểm tra qua MAP_STYLE: nếu style map sang \title → đây là title
        style_cmd = MAP_STYLE.get(ten_style, '')
        if style_cmd == r'\title':
            return True

        # Canh giữa
        canh_giua = False
        try:
            alignment = doan_van.paragraph_format.alignment
            if alignment is not None and alignment == 1:  # WD_ALIGN_PARAGRAPH.CENTER
                canh_giua = True
        except Exception:
            pass

        # Toàn bộ run đều bold
        tat_ca_dam = False
        runs = doan_van.runs
        if runs:
            tat_ca_dam = all(r.bold for r in runs if r.text.strip())

        # Font size lớn (>= 14pt)
        font_lon = False
        try:
            for r in runs:
                if r.font.size and r.font.size.pt >= 14:
                    font_lon = True
                    break
        except Exception:
            pass

        # Kết hợp: canh giữa + đậm, hoặc font lớn + đậm
        if (canh_giua and tat_ca_dam) or (font_lon and tat_ca_dam):
            return True

        return False

    def _la_nhan_vung(self, text: str, cac_nhan: list) -> bool:
        """Kiểm tra text có phải nhãn bắt đầu vùng hay không (Abstract, Keywords...)."""
        text_upper = text.strip().upper()
        # Loại bỏ số thứ tự đầu dòng nếu có: "1. ABSTRACT" → "ABSTRACT"
        text_upper = re.sub(r'^[\d\.]+\s*', '', text_upper).strip()
        for nhan in cac_nhan:
            if text_upper == nhan.upper() or text_upper.startswith(nhan.upper() + ':'):
                return True
        return False

    def _la_nhan_abstract(self, text: str) -> bool:
        """Kiểm tra text là nhãn 'Abstract' / 'Tóm tắt'."""
        return self._la_nhan_vung(text, ['ABSTRACT', 'TÓM TẮT', 'TOM TAT'])

    def _la_nhan_keywords(self, text: str) -> bool:
        """Kiểm tra text là nhãn 'Keywords' / 'Từ khóa'."""
        return self._la_nhan_vung(text, ['KEYWORDS', 'INDEX TERMS', 'TỪ KHÓA', 'TU KHOA', 'KEY WORDS'])

    def _la_nhan_body(self, text: str) -> bool:
        """Kiểm tra text là nhãn bắt đầu phần body (Introduction, Giới thiệu...)."""
        cac_nhan = [
            'INTRODUCTION', 'GIỚI THIỆU', 'GIOI THIEU', 'MỞ ĐẦU', 'MO DAU',
            'CHƯƠNG 1', 'CHUONG 1', 'CHAPTER 1', 'I. INTRODUCTION',
            'BACKGROUND', 'RELATED WORK', 'LITERATURE REVIEW',
            'METHODOLOGY', 'METHODS', 'PHƯƠNG PHÁP',
        ]
        text_upper = text.strip().upper()
        text_upper = re.sub(r'^[\d\.]+\s*', '', text_upper).strip()
        for nhan in cac_nhan:
            if text_upper == nhan or text_upper.startswith(nhan):
                return True
        # Heading pattern: "I. ..." hoặc "1. ..."
        if re.match(r'^[IV]+\.\s+', text.strip()):
            return True
        return False

    def phan_tich_ngu_nghia(self):
        """BƯỚC 1: Duyệt Word, phân loại nội dung vào parsed_data.

        State machine: pre_title → title → abstract → keywords → body
        Mỗi phần tử được xử lý thành LaTeX rồi gán vào vùng tương ứng.
        """
        self.doc_file_word()
        thu_tu_phan_tu = self.lay_thu_tu_phan_tu()
        self.tong_so_phan_tu = len(thu_tu_phan_tu)
        self.danh_sach_phan_tu = thu_tu_phan_tu

        # Reset
        self._vung_hien_tai = 'pre_title'
        bo_dem_abstract = 0  # Đếm đoạn văn trong vùng abstract
        bo_dem_keywords = 0

        # Template đã có \maketitle → không cho xu_ly_doan_van chèn thêm
        self.da_co_maketitle = True

        # Các buffer tạm
        buf_body = []
        buf_abstract = []
        buf_keywords = []
        buf_authors = []
        title_parts = []

        # Pre-scan: đánh dấu các paragraph là caption bảng (nằm ngay trước table)
        # để tránh xuất chúng lần nữa trong body
        for idx, (loai, phan_tu) in enumerate(thu_tu_phan_tu):
            if loai == 'table' and idx > 0:
                loai_truoc, pt_truoc = thu_tu_phan_tu[idx - 1]
                if loai_truoc == 'paragraph':
                    text_truoc = pt_truoc.text.strip()
                    if text_truoc and re.match(r'^(BẢNG|BANG|TABLE)\b', text_truoc, re.IGNORECASE):
                        self.cac_doan_da_dung.add(idx - 1)

        for idx, (loai, phan_tu) in enumerate(thu_tu_phan_tu):
            self.vi_tri_hien_tai = idx
            if idx in self.cac_doan_da_dung:
                continue

            # ---- Xác định chuyển vùng (state transition) ----
            if loai == 'paragraph':
                text_raw = phan_tu.text.strip()
                ten_style_p = phan_tu.style.name if phan_tu.style else ''
                style_cmd_p = MAP_STYLE.get(ten_style_p, '')

                # === Phát hiện vùng dựa trên STYLE ACM trước (ưu tiên cao) ===
                # Title style → luôn capture vào title_parts
                if style_cmd_p == r'\title':
                    self._vung_hien_tai = 'title'
                    if text_raw:
                        title_parts.append(loc_ky_tu(text_raw))
                    continue

                # Author / Affiliation → thu thập vào buf_authors
                if style_cmd_p in (r'\author', r'\affil'):
                    if text_raw:
                        buf_authors.append(text_raw)
                    if self._vung_hien_tai == 'title':
                        pass  # Vẫn ở vùng title, chờ abstract
                    continue

                # Abstract style → capture nội dung vào buf_abstract
                if style_cmd_p == r'\abstract':
                    if self._vung_hien_tai != 'abstract':
                        self._vung_hien_tai = 'abstract'
                    noi_dung_abs = self.xu_ly_noi_dung_doan_van(phan_tu)
                    if noi_dung_abs.strip():
                        buf_abstract.append(noi_dung_abs.strip() + '\n')
                    continue

                # Keywords style (MAP_STYLE = None nhưng tên style là 'Keywords')
                if ten_style_p in ('Keywords', 'KeyWordHead'):
                    if ten_style_p == 'Keywords' and text_raw:
                        self._vung_hien_tai = 'keywords'
                        buf_keywords.append(loc_ky_tu(text_raw))
                    continue

                # Các style bị bỏ qua hoàn toàn (metadata)
                if style_cmd_p is None:
                    continue

                # === Fallback: dùng heuristics cho các style khác ===

                # Từ pre_title → phát hiện Title
                if self._vung_hien_tai == 'pre_title':
                    if self._la_doan_title(phan_tu, idx):
                        self._vung_hien_tai = 'title'
                        title_parts.append(loc_ky_tu(text_raw))
                        continue
                    elif self._la_nhan_abstract(text_raw):
                        self._vung_hien_tai = 'abstract'
                        if len(text_raw) < 30:
                            continue
                        noi_dung_sau_nhan = re.sub(
                            r'^(abstract|tóm tắt|tom tat)[:\s]*', '', text_raw, flags=re.IGNORECASE
                        ).strip()
                        if noi_dung_sau_nhan:
                            buf_abstract.append(loc_ky_tu(noi_dung_sau_nhan))
                        continue
                    elif self._la_nhan_body(text_raw):
                        self._vung_hien_tai = 'body'
                    elif not text_raw:
                        continue

                # Từ title → gom thêm hoặc chuyển sang abstract/body
                elif self._vung_hien_tai == 'title':
                    if self._la_doan_title(phan_tu, idx):
                        title_parts.append(loc_ky_tu(text_raw))
                        continue
                    elif self._la_nhan_abstract(text_raw):
                        self._vung_hien_tai = 'abstract'
                        if len(text_raw) < 30:
                            continue
                        noi_dung_sau_nhan = re.sub(
                            r'^(abstract|tóm tắt|tom tat)[:\s]*', '', text_raw, flags=re.IGNORECASE
                        ).strip()
                        if noi_dung_sau_nhan:
                            buf_abstract.append(loc_ky_tu(noi_dung_sau_nhan))
                        continue
                    elif self._la_nhan_body(text_raw):
                        self._vung_hien_tai = 'body'
                    elif text_raw:
                        self._vung_hien_tai = 'body'

                # Từ abstract → chuyển sang keywords hoặc body
                elif self._vung_hien_tai == 'abstract':
                    if self._la_nhan_keywords(text_raw):
                        self._vung_hien_tai = 'keywords'
                        if len(text_raw) < 30:
                            continue
                        noi_dung_sau_nhan = re.sub(
                            r'^(keywords|index terms|từ khóa|tu khoa|key words)[:\s]*',
                            '', text_raw, flags=re.IGNORECASE
                        ).strip()
                        if noi_dung_sau_nhan:
                            buf_keywords.append(loc_ky_tu(noi_dung_sau_nhan))
                        continue
                    elif self._la_nhan_body(text_raw):
                        self._vung_hien_tai = 'body'
                    elif text_raw:
                        bo_dem_abstract += 1
                        if bo_dem_abstract > 10:
                            self._vung_hien_tai = 'body'

                # Từ keywords → chuyển sang body
                elif self._vung_hien_tai == 'keywords':
                    if self._la_nhan_body(text_raw):
                        self._vung_hien_tai = 'body'
                    elif text_raw:
                        bo_dem_keywords += 1
                        if bo_dem_keywords > 3:
                            self._vung_hien_tai = 'body'

            # ---- Xử lý phần tử và gán vào vùng ----
            if loai == 'paragraph':
                ket_qua = self.xu_ly_doan_van(phan_tu)
                if not ket_qua:
                    continue

                if self._vung_hien_tai == 'abstract':
                    buf_abstract.append(ket_qua)
                elif self._vung_hien_tai == 'keywords':
                    buf_keywords.append(ket_qua)
                else:  # body, pre_title (phần chưa nhận dạng → body)
                    buf_body.append(ket_qua)

            elif loai == 'table':
                buf_body.append(self.dong_danh_sach_hien_tai())
                ket_qua = self.xu_ly_bang(phan_tu)
                if ket_qua:
                    buf_body.append(ket_qua)

        # Đóng danh sách nếu còn mở
        buf_body.append(self.dong_danh_sach_hien_tai())

        # Gán kết quả
        self.parsed_data['title'] = ' '.join(title_parts).strip()
        self.parsed_data['authors'] = buf_authors
        self.parsed_data['abstract'] = ''.join(buf_abstract).strip()
        self.parsed_data['keywords'] = ''.join(buf_keywords).strip()
        self.parsed_data['body'] = ''.join(buf_body)

    # ----- Regex helpers cho inject_into_template -----

    def _tim_cap_ngoac(self, s: str, vi_tri_bat_dau: int) -> int:
        """Tìm vị trí đóng ngoặc nhọn } khớp với { tại vi_tri_bat_dau.
        Xử lý nested braces: \title{A {B} C} → trả về vị trí } cuối.
        """
        if vi_tri_bat_dau >= len(s) or s[vi_tri_bat_dau] != '{':
            return -1
        dem = 0
        for i in range(vi_tri_bat_dau, len(s)):
            if s[i] == '{' and (i == 0 or s[i-1] != '\\'):
                dem += 1
            elif s[i] == '}' and (i == 0 or s[i-1] != '\\'):
                dem -= 1
                if dem == 0:
                    return i
        return -1

    def _thay_the_title(self, template: str) -> str:
        """Thay thế \title{dummy} bằng nội dung title thật từ Word."""
        title = self.parsed_data.get('title', '').strip()
        if not title:
            return template

        # Tìm \title{ bằng regex, sau đó dùng brace matching
        match = re.search(r'\\title\s*\{', template)
        if not match:
            return template

        vi_tri_mo = match.end() - 1  # Vị trí ký tự '{'
        vi_tri_dong = self._tim_cap_ngoac(template, vi_tri_mo)
        if vi_tri_dong == -1:
            return template

        # Giữ nguyên phần sau title (ví dụ \thanks{...})
        noi_dung_cu = template[vi_tri_mo + 1:vi_tri_dong]

        # Nếu có \thanks{} bên trong, giữ lại
        thanks_match = re.search(r'\\thanks\s*\{', noi_dung_cu)
        phan_thanks = ''
        if thanks_match:
            thanks_start = thanks_match.start()
            # Tìm } đóng của \thanks
            vi_tri_thanks_mo = thanks_match.end() - 1
            # Tìm trong noi_dung_cu
            vi_tri_thanks_dong = self._tim_cap_ngoac(noi_dung_cu, vi_tri_thanks_mo)
            if vi_tri_thanks_dong != -1:
                phan_thanks = '\n' + noi_dung_cu[thanks_start:vi_tri_thanks_dong + 1]

        noi_dung_moi = title + phan_thanks
        template = template[:vi_tri_mo + 1] + noi_dung_moi + template[vi_tri_dong:]
        return template

    def _thay_the_abstract(self, template: str) -> str:
        """Thay thế nội dung bên trong \begin{abstract}...\end{abstract}."""
        abstract = self.parsed_data.get('abstract', '').strip()
        if not abstract:
            return template

        pattern = r'(\\begin\{abstract\})(.*?)(\\end\{abstract\})'
        match = re.search(pattern, template, re.DOTALL)
        if match:
            template = (
                template[:match.start(2)]
                + '\n' + abstract + '\n'
                + template[match.end(2):]
            )
        return template

    def _thay_the_keywords(self, template: str) -> str:
        """Thay thế nội dung keywords trong IEEEkeywords hoặc dòng Keywords."""
        keywords = self.parsed_data.get('keywords', '').strip()
        if not keywords:
            return template

        # Thử \begin{IEEEkeywords}...\end{IEEEkeywords}
        pattern_ieee = r'(\\begin\{IEEEkeywords\})(.*?)(\\end\{IEEEkeywords\})'
        match = re.search(pattern_ieee, template, re.DOTALL)
        if match:
            template = (
                template[:match.start(2)]
                + '\n' + keywords + '\n'
                + template[match.end(2):]
            )
            return template

        # Thử \textbf{Keywords:} hoặc \textbf{Index Terms:}
        pattern_kw = r'\\textbf\{(Keywords|Index Terms)\s*:?\}[^\n]*'
        match = re.search(pattern_kw, template, re.IGNORECASE)
        if match:
            replacement = rf'\\textbf{{{match.group(1)}:}} {keywords}'
            template = template[:match.start()] + replacement + template[match.end():]
            return template

        return template

    def _thay_the_author(self, template: str) -> str:
        """Thay thế \\author{...} trong template bằng author từ Word."""
        authors = self.parsed_data.get('authors', [])
        if not authors:
            return template

        # Tìm \\author{ và replace toàn bộ block (xử lý nested braces)
        match = re.search(r'\\author\s*\{', template)
        if not match:
            return template

        vi_tri_mo = match.end() - 1  # vị trí {
        vi_tri_dong = self._tim_cap_ngoac(template, vi_tri_mo)
        if vi_tri_dong == -1:
            return template

        # Xây dựng nội dung author mới
        # Ghép tất cả author/affiliation thành dạng \\author{...}
        noi_dung_author_parts = []
        for i, info in enumerate(authors):
            info_escaped = loc_ky_tu(info)
            noi_dung_author_parts.append(info_escaped)

        # Ghép lại: dùng \\\\ để xuống dòng giữa các phần (name, dept, org...)
        noi_dung_author = ' \\\\\n'.join(noi_dung_author_parts)

        # Thay thế toàn bộ \\author{...} cũ bằng \\author{...} mới
        template = (
            template[:match.start()]
            + f'\\author{{{noi_dung_author}}}'
            + template[vi_tri_dong + 1:]
        )
        return template

    def _strip_latex_commands(self, text: str) -> str:
        """Loại bỏ các lệnh LaTeX formatting để lấy plain text cho matching."""
        # Loại bỏ \textbf{...}, \textit{...}, \textcolor[...]{...}{...}
        result = text
        result = re.sub(r'\\textcolor\[[^\]]*\]\{[^}]*\}\{([^}]*)\}', r'\1', result)
        result = re.sub(r'\\textcolor\{[^}]*\}\{([^}]*)\}', r'\1', result)
        result = re.sub(r'\\text(?:bf|it|rm|tt|sf|sc)\{([^}]*)\}', r'\1', result)
        # Loại bỏ \href{...}{...}
        result = re.sub(r'\\href\{[^}]*\}\{([^}]*)\}', r'\1', result)
        # Loại bỏ các lệnh LaTeX đơn giản còn lại
        result = re.sub(r'\\[a-zA-Z]+\*?\{([^}]*)\}', r'\1', result)
        result = re.sub(r'\\[a-zA-Z]+\*?', '', result)
        # Loại bỏ {} còn thừa
        result = result.replace('{', '').replace('}', '')
        return result.strip()

    def _loc_metadata_word_thua(self, body: str) -> str:
        r"""Lọc bỏ các đoạn metadata Word dư thừa ở đầu body.
        Khi Word document có bảng layout chứa metadata (ARTICLE TITLE, Authors,
        Abstract...), semantic parser phân loại tất cả thành body → trùng lặp
        với template header. Hàm này strip các đoạn đó.

        Chiến lược: tìm dòng \section*{...} đầu tiên — tất cả metadata nằm trước đó.
        Nếu không tìm thấy \section*, dùng pattern matching để cắt metadata."""
        cac_dong = body.split('\n')

        # Chiến lược 1: tìm \section* đầu tiên — cắt tất cả trước đó
        for i, dong in enumerate(cac_dong):
            if re.match(r'\s*\\section\*?\{', dong.strip()):
                if i > 0:
                    return '\n'.join(cac_dong[i:])
                return body

        # Chiến lược 2 (fallback): dùng pattern matching trên plain text
        cac_pattern_metadata = [
            r'ARTICLE\s+TITLE',
            r'ARTICLE\s+INFORMATION',
            r'Full\s+Name\s+of\s+Author',
            r'Affiliation\s+for\s+Author',
            r'authors\s+have\s+contributed\s+equally',
            r'ABSTRACT',
            r'TOM\s+TAT|T[ÓO]M\s+T[AẮ]T',
            r'Journal.*?ISSN',
            r'ISSN:\s*\d',
            r'Volume:\s*',
            r'Issue:\s*',
            r'Firstname',
            r'Correspondence:',
            r'Citation:',
            r'DOI:',
            r'OPEN\s+ACCESS',
            r'Creative\s+Commons',
            r'CC\s+BY',
            r'Received:.*Accepted:',
            r'Published:.*\d{4}',
            r'BE\s+CONCISE.*SPECIFIC.*RELEVANT',
            r'CAPITALIZED.*BOLD.*TIMES',
            r'NOT\s+EXCEED\s+20\s+WORDS',
            r'provided the original work',
            r'permission of the author',
            r'^\*\s*Note:',
            r'abc@xyz',
            r'keyword\s+\d',
            r'tu\s+khoa\s+\d|t[ừu]\s+kh[oó]a\s+\d',
        ]
        combined_re = re.compile('|'.join(cac_pattern_metadata), re.IGNORECASE)
        dong_bat_dau_noi_dung = 0

        for i, dong in enumerate(cac_dong):
            dong_strip = dong.strip()
            if not dong_strip:
                continue
            # Strip LaTeX commands để lấy plain text trước khi matching
            plain_text = self._strip_latex_commands(dong_strip)
            if not plain_text:
                dong_bat_dau_noi_dung = i + 1
                continue
            if combined_re.search(plain_text):
                dong_bat_dau_noi_dung = i + 1
                continue
            # Gặp dòng nội dung thật → dừng
            break

        if dong_bat_dau_noi_dung > 0:
            return '\n'.join(cac_dong[dong_bat_dau_noi_dung:])
        return body

    def _thay_the_body(self, template: str) -> str:
        """Thay thế TOÀN BỘ dummy content trong template bằng body thật từ Word.

        Chiến lược:
        1. Tìm điểm BẮT ĐẦU: ngay sau \end{IEEEkeywords}, \end{abstract},
           hoặc \maketitle (lấy vị trí xa nhất)
        2. Tìm điểm KẾT THÚC: ngay trước \end{document} (luôn luôn)
        3. Xóa TẤT CẢ dummy content giữa 2 điểm (body + References + bibliography
           + red warning...), chèn body Word thay thế
        """
        body = self.parsed_data.get('body', '')
        if not body.strip():
            return template

        # Lọc bỏ metadata Word dư thừa ở đầu body
        body = self._loc_metadata_word_thua(body)

        # Tìm điểm bắt đầu (ưu tiên cao → thấp)
        diem_bat_dau = -1
        cac_moc_bat_dau = [
            r'\\end\{IEEEkeywords\}',
            r'\\end\{abstract\}',
            r'\\maketitle',
        ]
        for moc in cac_moc_bat_dau:
            match = re.search(moc, template)
            if match:
                # Lấy vị trí xa nhất (sau cùng trong template)
                if match.end() > diem_bat_dau:
                    diem_bat_dau = match.end()

        if diem_bat_dau == -1:
            # Không tìm thấy mốc → fallback
            return template

        # Điểm kết thúc: LUÔN là \end{document} — xóa TẤT CẢ dummy content
        match_end = re.search(r'\\end\{document\}', template)
        if not match_end:
            return template
        diem_ket_thuc = match_end.start()

        # Xây dựng template mới: giữ preamble + chèn body + \end{document}
        template = (
            template[:diem_bat_dau]
            + '\n\n' + body + '\n\n'
            + template[diem_ket_thuc:]
        )
        return template

    def _template_co_cau_truc(self, template: str) -> bool:
        """Kiểm tra template có cấu trúc ngữ nghĩa (title/abstract/maketitle)
        hay chỉ là template đơn giản với %%CONTENT%%.
        """
        # Nếu template có \maketitle hoặc \title{ → cấu trúc IEEE/ACM
        co_maketitle = '\\maketitle' in template
        co_title_cmd = bool(re.search(r'\\title\s*\{', template))
        co_abstract = '\\begin{abstract}' in template
        # Template được coi là có cấu trúc nếu có ít nhất 1 trong 3 dấu hiệu
        return co_maketitle or co_title_cmd or co_abstract

    def inject_into_template(self, template: str) -> str:
        """BƯỚC 2: Tiêm parsed_data vào template LaTeX có cấu trúc.

        Thứ tự xử lý: title → abstract → keywords → body
        Mỗi bước dùng regex helper riêng biệt, dễ debug.
        """
        ket_qua = template

        # 1. Title
        ket_qua = self._thay_the_title(ket_qua)

        # 2. Author (thay thế example authors trong template)
        ket_qua = self._thay_the_author(ket_qua)

        # 3. Abstract
        ket_qua = self._thay_the_abstract(ket_qua)

        # 4. Keywords
        ket_qua = self._thay_the_keywords(ket_qua)

        # 4. Body (quan trọng nhất)
        ket_qua = self._thay_the_body(ket_qua)

        # 5. Fallback: nếu body injection thất bại, thử %%CONTENT%%
        if '%%CONTENT%%' in ket_qua:
            all_content = self.parsed_data.get('body', '')
            ket_qua = ket_qua.replace('%%CONTENT%%', all_content)

        return ket_qua

    def chuyen_doi(self):
        """Thực hiện chuyển đổi: đọc Word → phân loại → tiêm vào template → ghi file."""
        template = self.doc_template()

        # Đảm bảo template có các package cần thiết
        cac_goi_can_them = []
        if r"\usepackage{multirow}" not in template:
            cac_goi_can_them.append(r"\usepackage{multirow}")
            cac_goi_can_them.append(r"\usepackage{multicol}")
        if r"\usepackage{float}" not in template:
            cac_goi_can_them.append(r"\usepackage{float}")
        if r"\usepackage{subcaption}" not in template and r"\usepackage{subfig}" not in template:
            cac_goi_can_them.append(r"\usepackage{subcaption}")
        if '{hyperref}' not in template:
            cac_goi_can_them.append(r"\usepackage{hyperref}")
            # Ẩn viền xanh quanh hyperlink trong PDF
            cac_goi_can_them.append(r"\hypersetup{colorlinks=true,linkcolor=black,urlcolor=blue,citecolor=black}")
        elif 'colorlinks' not in template and r"\hypersetup" not in template:
            # Template đã có hyperref nhưng chưa cấu hình colorlinks
            cac_goi_can_them.append(r"\hypersetup{colorlinks=true,linkcolor=black,urlcolor=blue,citecolor=black}")

        if cac_goi_can_them:
            goi_str = "\n".join(cac_goi_can_them) + "\n"
            if r"\begin{document}" in template:
                template = template.replace(r"\begin{document}", goi_str + r"\begin{document}")
            else:
                template = template + "\n" + goi_str

        # Phân biệt: template có cấu trúc (IEEE/ACM) hay đơn giản (%%CONTENT%%)
        co_cau_truc = self._template_co_cau_truc(template)

        if co_cau_truc:
            # --- Semantic Mapping Pipeline ---
            self.phan_tich_ngu_nghia()            # BƯỚC 1: Bóc tách
            latex_cuoi = self.inject_into_template(template)  # BƯỚC 2: Tiêm
        else:
            # --- Fallback: dùng %%CONTENT%% như cũ ---
            noi_dung = self.sinh_noi_dung()
            latex_cuoi = template.replace('%%CONTENT%%', noi_dung)

        with open(self.duong_dan_dau_ra, 'w', encoding='utf-8') as f:
            f.write(latex_cuoi)

def main():
    # Hàm chính: thiết lập đường dẫn và chạy chuyển đổi
    duong_dan_word = 'input_data/acm_submission_template.docx'
    duong_dan_template = 'input_data/latex_template_onecolumn.tex'
    duong_dan_dau_ra = 'output/ket_qua_acm_ieee.tex'
    thu_muc_anh = 'output/images'
    mode = 'demo'

    chuyen_doi = ChuyenDoiWordSangLatex(
        duong_dan_word,
        duong_dan_template,
        duong_dan_dau_ra,
        thu_muc_anh,
        mode,
    )
    chuyen_doi.chuyen_doi()
    print("Chuyển đổi hoàn tất rùi! \n")

    bien_dich_latex(duong_dan_dau_ra)
    don_dep_file_rac(duong_dan_dau_ra)

if __name__ == "__main__":
    main()
