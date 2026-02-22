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
        # Đọc file Word (.docx) bằng python-docx
        if not os.path.exists(self.duong_dan_word):
            raise FileNotFoundError(f"Không tìm thấy file: {self.duong_dan_word}")
        try:
            self.tai_lieu = Document(self.duong_dan_word)
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
                        run_obj = run_map.get(id(r_elem))
                        if run_obj is not None:
                            noi_dung_link += self.xu_ly_run_thuong(run_obj)
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
                return loc_ky_tu(text)
        except Exception:
            pass
        return None

    def bat_caption_hinh(self) -> str:
        # Bắt caption thật của hình từ paragraph ngay phía dưới
        try:
            idx_sau = self.vi_tri_hien_tai + 1
            if idx_sau < 0 or idx_sau >= len(self.danh_sach_phan_tu):
                return None
            loai, phan_tu = self.danh_sach_phan_tu[idx_sau]
            if loai != 'paragraph':
                return None
            text = phan_tu.text.strip()
            if not text:
                return None
            if re.match(r'^(HÌNH|HINH|ẢNH|ANH|FIGURE|FIG)\b', text.strip(), re.IGNORECASE):
                self.cac_doan_da_dung.add(idx_sau)
                return loc_ky_tu(text)
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

        # Phát hiện TOC text
        if 'TABLE OF CONTENTS' in text_raw or 'MỤC LỤC' in text_raw:
            if not self.toc_da_sinh and len(text_raw) < 50:
                self.toc_da_sinh = True
                return r"\tableofcontents" + "\n\\newpage\n\n"
            return ""

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
                heading_cmd, _ = self.phat_hien_heading(text_goc)
                if heading_cmd:
                    lenh_latex = heading_cmd

            # Dùng starred heading (*) khi nội dung đã có số đầu dòng
            if lenh_latex and lenh_latex in (r'\section', r'\subsection',
                                             r'\subsubsection', r'\paragraph'):
                if (re.match(r'^[\d\.]+\s*[A-Za-zÀ-ỹ]', text_goc)
                        or re.match(r'^(CHƯƠNG|CHAPTER)\s*\d', text_goc, re.IGNORECASE)):
                    lenh_latex = lenh_latex + '*'
                elif lenh_latex == r'\section':
                    self.dem_heading1 += 1
                    if self.dem_heading1 == 1:
                        lenh_latex = r'\section*'

            if lenh_latex:
                if lenh_latex is None:
                    return ket_qua
                ket_qua += f"{lenh_latex}{{{noi_dung}}}\n\n"
            else:
                ket_qua += f"{noi_dung}\n\n"

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
        latex += rf"  \caption{{{caption_final}}}" + "\n"
        latex += rf"  \label{{{label}}}" + "\n"
        latex += r"\end{figure}" + "\n\n"
        return latex

    def tao_latex_nhom_hinh(self, danh_sach_anh: list, danh_sach_caption: list = None, caption: str = None) -> str:
        # Gom nhieu anh thanh 1 figure voi subfigure nam ngang
        if not danh_sach_anh:
            return ""
        ten_thu_muc = os.path.basename(self.thu_muc_anh)
        vi_tri = "[H]" if self.mode == 'demo' else "[htbp]"
        so_anh = len(danh_sach_anh)
        # Tinh do rong moi subfigure (tru khoang cach hfill)
        do_rong = f"{0.9 / so_anh:.2f}" if so_anh > 1 else "0.48"

        latex = rf"\begin{{figure}}{vi_tri}" + "\n"
        latex += r"  \centering" + "\n"

        for i, ten_anh in enumerate(danh_sach_anh):
            # Lay phan mo ta (bo nhan (a),(b) vi subcaption tu sinh)
            mo_ta = ""
            if danh_sach_caption and i < len(danh_sach_caption):
                # Loai bo phan "(a)" dau chuoi, chi giu mo ta
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

        caption_final = caption or ""
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
        # Duyệt toàn bộ phần tử và sinh nội dung LaTeX
        self.doc_file_word()
        noi_dung = []
        thu_tu_phan_tu = self.lay_thu_tu_phan_tu()
        self.tong_so_phan_tu = len(thu_tu_phan_tu)
        # Luu danh sach de cac ham khac co the nhin truoc/sau
        self.danh_sach_phan_tu = thu_tu_phan_tu

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

    def chuyen_doi(self):
        # Thực hiện chuyển đổi: đọc Word → sinh nội dung → ghép template → ghi file
        template = self.doc_template()
        if r"\usepackage{multirow}" not in template:
            goi_multirow = "\\usepackage{multirow}\n\\usepackage{multicol}\n"
            if r"\begin{document}" in template:
                template = template.replace(r"\begin{document}", goi_multirow + r"\begin{document}")
            else:
                template = template + "\n" + goi_multirow
        noi_dung = self.sinh_noi_dung()
        latex_cuoi = template.replace('%%CONTENT%%', noi_dung)
        with open(self.duong_dan_dau_ra, 'w', encoding='utf-8') as f:
            f.write(latex_cuoi)

def main():
    # Hàm chính: thiết lập đường dẫn và chạy chuyển đổi
    duong_dan_word = r"input_data/word_template(mau4).docx"
    duong_dan_template = r"input_data/latex_template_onecolumn.tex"
    duong_dan_dau_ra = r"output/word_template(mau4).tex"
    thu_muc_anh = r"output/images"
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
