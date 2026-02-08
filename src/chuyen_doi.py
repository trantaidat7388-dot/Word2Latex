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

        # Khởi tạo bộ xử lý toán (XSLT / Pandoc / parser thủ công)
        duong_dan_xslt = duong_dan_xslt_omml or DEFAULT_OMML2MML_XSL
        self.bo_toan = BoXuLyToan(duong_dan_xslt=duong_dan_xslt)

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

    def lay_tat_ca_hyperlink(self, doan_van) -> dict:
        # Trích xuất tất cả hyperlink từ đoạn văn, trả về dict {text: url}
        hyperlinks = {}
        try:
            for hyperlink_elem in doan_van._element.findall(f'.//{{{W_NAMESPACE}}}hyperlink'):
                rId = hyperlink_elem.get(qn('r:id'))
                if rId is None:
                    rId = hyperlink_elem.get(f'{{{R_NAMESPACE}}}id')

                if rId and self.tai_lieu:
                    rels = self.tai_lieu.part.rels
                    if rId in rels:
                        url = rels[rId].target_ref
                        text_parts = []
                        for t_elem in hyperlink_elem.findall(f'.//{{{W_NAMESPACE}}}t'):
                            if t_elem.text:
                                text_parts.append(t_elem.text)
                        link_text = ''.join(text_parts).strip()
                        if link_text and url:
                            hyperlinks[link_text] = url
        except Exception:
            pass
        return hyperlinks

    def xu_ly_run(self, run) -> str:
        # Xử lý một run: escape ký tự + áp dụng bold/italic/màu/highlight/hyperlink
        van_ban = run.text
        if not van_ban:
            return ""

        ket_qua = loc_ky_tu(van_ban)

        # Kiểm tra hyperlink trước (ưu tiên cao nhất)
        url = self.lay_hyperlink(run)
        if url:
            ket_qua = rf"\href{{{url}}}{{{ket_qua}}}"
            return ket_qua

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

    def trich_xuat_anh(self, doan_van) -> list:
        # Trích xuất ảnh từ paragraph, lọc trang trí, lưu ảnh nội dung
        danh_sach_anh = []
        if not self.tai_lieu:
            return danh_sach_anh

        tong_so_anh = sum(
            1 for run in doan_van.runs
            for _ in run._element.findall(f'.//{{{A_NAMESPACE}}}blip')
        )
        if tong_so_anh > 3:
            return danh_sach_anh

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

                # Kiểm tra bằng metadata (vị trí, kích thước...)
                if self.la_anh_trang_tri(kich_thuoc, doan_van):
                    try:
                        os.remove(duong_dan_anh)
                        self.dem_anh -= 1
                    except Exception:
                        pass
                    continue

                # Kiểm tra bằng phân tích pixel (entropy, edge, histogram)
                if not BoLocAnh.la_anh_noi_dung(duong_dan_anh):
                    try:
                        os.remove(duong_dan_anh)
                        self.dem_anh -= 1
                    except Exception:
                        pass
                    continue

                danh_sach_anh.append(ten_anh)
        return danh_sach_anh

    def tao_latex_hinh(self, ten_anh: str) -> str:
        # Sinh mã LaTeX figure cho ảnh (includegraphics + caption + label)
        label = f"fig:hinh{self.dem_anh}"
        ten_thu_muc = os.path.basename(self.thu_muc_anh)
        vi_tri = "[H]" if self.mode == 'demo' else "[htbp]"
        latex = rf"\begin{{figure}}{vi_tri}" + "\n"
        latex += r"  \centering" + "\n"
        latex += rf"  \includegraphics[width=0.6\linewidth]{{{ten_thu_muc}/{ten_anh}}}" + "\n"
        latex += r"  \caption{}" + "\n"
        latex += rf"  \label{{{label}}}" + "\n"
        latex += r"\end{figure}" + "\n\n"
        return latex

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

    # BẢNG: phát hiện loại + chuyển đổi

    def la_table_of_contents(self, bang: Table) -> bool:
        # Phát hiện bảng Mục lục (TOC) dựa trên từ khóa + cấu trúc
        try:
            if len(bang.rows) < 5:
                return False

            if self.tong_so_phan_tu > 0:
                vi_tri_phan_tram = (self.vi_tri_hien_tai / self.tong_so_phan_tu) * 100
                if vi_tri_phan_tram > 30:
                    return False

            toan_bo_text = ''
            for hang in bang.rows[:min(5, len(bang.rows))]:
                for cell in hang.cells:
                    toan_bo_text += cell.text.strip().upper() + ' '

            co_tu_khoa_toc = False
            tu_khoa_muc_luc = ['MỤC LỤC', 'TABLE OF CONTENTS']
            for tu in tu_khoa_muc_luc:
                if tu in toan_bo_text:
                    co_tu_khoa_toc = True
                    break

            dem_dau_cham = 0
            dem_so_trang_cuoi = 0
            dem_cau_truc_muc = 0

            for hang in bang.rows[:min(20, len(bang.rows))]:
                if len(hang.cells) == 0:
                    continue

                text_hang = ''.join([c.text for c in hang.cells])

                if '.....' in text_hang or '…' in text_hang:
                    dem_dau_cham += 1

                if len(hang.cells) >= 2:
                    cell_cuoi = hang.cells[-1].text.strip()
                    if cell_cuoi.isdigit() and 1 <= len(cell_cuoi) <= 4:
                        dem_so_trang_cuoi += 1

                    cell_dau = hang.cells[0].text.strip().upper()
                    if re.search(r'(CH[UƯ][ƠƯ]NG|CHAPTER|PH[ẦẦ]N|PART|M[ỤỦ]C)\s*\d', cell_dau):
                        dem_cau_truc_muc += 1
                    if re.search(r'^\d+\.?\d*\.?\s+[A-ZÀ-Ỹ]', cell_dau):
                        dem_cau_truc_muc += 1

            so_hang_kiem_tra = min(20, len(bang.rows))

            # Cần từ khóa MỤC LỤC + ít nhất 1 tiêu chí cấu trúc
            if co_tu_khoa_toc:
                if dem_dau_cham >= 3 or dem_so_trang_cuoi >= 5:
                    return True

            # Không có từ khóa → cần 3 tiêu chí cùng lúc
            if (dem_dau_cham > so_hang_kiem_tra * 0.5
                    and dem_so_trang_cuoi > so_hang_kiem_tra * 0.5
                    and dem_cau_truc_muc >= 3):
                return True
        except Exception:
            pass
        return False

    def la_bang_chua_anh(self, bang: Table) -> bool:
        # Phát hiện bảng chứa chủ yếu ảnh (figure layout)
        try:
            so_cell_co_anh = 0
            so_cell_co_text_dai = 0
            tong_cell = 0
            cells_da_kiem = set()

            for hang in bang.rows:
                for cell in hang.cells:
                    cell_id = id(cell._tc)
                    if cell_id in cells_da_kiem:
                        continue
                    cells_da_kiem.add(cell_id)

                    tong_cell += 1
                    cell_text = cell.text.strip()
                    co_anh = False

                    for para in cell.paragraphs:
                        for run in para.runs:
                            blips = run._element.findall(f'.//{{{A_NAMESPACE}}}blip')
                            if blips:
                                co_anh = True
                                break
                        drawings = para._element.findall(f'.//{{{A_NAMESPACE}}}blip')
                        if drawings:
                            co_anh = True

                    if co_anh:
                        so_cell_co_anh += 1

                    if re.match(r'^[\(\[]*[a-zA-Z0-9][\)\]]*\.?$', cell_text):
                        pass  # label ngắn, bỏ qua
                    elif re.match(r'^(Hình|Figure|Fig|Bảng|Table)\s*\d+', cell_text, re.IGNORECASE):
                        pass  # label caption, bỏ qua
                    elif len(cell_text) > 20:
                        so_cell_co_text_dai += 1

            if tong_cell == 0:
                return False

            if so_cell_co_anh >= 1:
                if so_cell_co_text_dai <= 1:
                    return True
                if so_cell_co_anh / tong_cell >= 0.3:
                    return True
        except Exception:
            pass
        return False

    def la_bang_layout(self, bang: Table) -> bool:
        # Phát hiện bảng layout metadata (đầu bài báo: ISSN, Abstract, Keywords...)
        try:
            if self.tong_so_phan_tu > 0:
                vi_tri_phan_tram = (self.vi_tri_hien_tai / self.tong_so_phan_tu) * 100
                if vi_tri_phan_tram > 25:
                    return False

            toan_bo_text = ''
            for hang in bang.rows[:min(10, len(bang.rows))]:
                for cell in hang.cells:
                    toan_bo_text += cell.text.strip().upper() + ' '

            tu_khoa_layout = [
                'ARTICLE INFORMATION', 'ARTICLE TITLE', 'JOURNAL:',
                'ISSN:', 'ABSTRACT', 'KEYWORDS:', 'TỪ KHÓA:',
                'AUTHOR', 'AFFILIATION', 'CORRESPONDENCE', 'CITATION',
                'RECEIVED:', 'ACCEPTED:', 'PUBLISHED:', 'DOI:',
                'OPEN ACCESS', 'TÓM TẮT', 'VOLUME:', 'ISSUE:',
            ]

            dem_tu_khoa = sum(1 for tu in tu_khoa_layout if tu in toan_bo_text)
            if dem_tu_khoa >= 3:
                return True
        except Exception:
            pass
        return False

    def la_bang_cong_thuc(self, bang: Table) -> bool:
        # Phát hiện bảng công thức toán: 2 cột, cột cuối là số thứ tự (1), (2)...
        try:
            if len(bang.columns) != 2:
                return False

            dem_so_thu_tu = 0
            for hang in bang.rows:
                if len(hang.cells) >= 2:
                    cell_cuoi = hang.cells[-1].text.strip()
                    if re.match(r'^\(\d+\)$', cell_cuoi):
                        dem_so_thu_tu += 1

            if len(bang.rows) > 0 and dem_so_thu_tu / len(bang.rows) >= 0.5:
                return True
        except Exception:
            pass
        return False

    def trich_xuat_noi_dung_bang_layout(self, bang: Table) -> str:
        # Trích xuất nội dung text từ bảng layout (bỏ cấu trúc bảng)
        ket_qua = []
        da_xuat_para = set()
        try:
            for hang in bang.rows:
                for cell in hang.cells:
                    text = cell.text.strip()
                    if text and len(text) > 2:
                        for para in cell.paragraphs:
                            noi_dung = ""
                            for run in para.runs:
                                noi_dung += self.xu_ly_run(run)
                            noi_dung_clean = noi_dung.strip()
                            if noi_dung_clean and noi_dung_clean not in da_xuat_para:
                                da_xuat_para.add(noi_dung_clean)
                                ket_qua.append(noi_dung + "\n\n")
        except Exception:
            pass
        return ''.join(ket_qua)

    def trich_xuat_omml_tu_cell(self, cell) -> str:
        # Trích xuất công thức (OMML hoặc OLE) từ một cell của bảng
        cong_thuc_parts = []
        try:
            for para in cell.paragraphs:
                # 1. Tìm OMML
                omath_list = para._element.findall(f'.//{{{OMML_NAMESPACE}}}oMath')
                for omath in omath_list:
                    latex = self.bo_toan.omml_element_to_latex(omath)
                    if latex.strip():
                        cong_thuc_parts.append(latex)

                # 2. Tìm OLE Object nếu không có OMML
                if not omath_list:
                    objects = para._element.findall(f'.//{{{W_NAMESPACE}}}object')
                    for obj in objects:
                        ole = obj.find(f'.//{{{OLE_NAMESPACE}}}OLEObject')
                        if ole is not None:
                            # 2a. Thử parse MTEF → LaTeX (ưu tiên)
                            ole_rid = ole.get(f'{{{R_NAMESPACE}}}id')
                            if ole_rid:
                                ole_part = self.tai_lieu.part.related_parts.get(ole_rid)
                                if ole_part:
                                    try:
                                        latex_from_mtef = ole_equation_to_latex(ole_part.blob)
                                        if latex_from_mtef.strip():
                                            cong_thuc_parts.append(latex_from_mtef)
                                            continue
                                    except Exception:
                                        pass

                            # 2b. Fallback: trích xuất ảnh từ OLE
                            imagedata = obj.find(f'.//{{{VML_NAMESPACE}}}imagedata')
                            if imagedata is not None:
                                rid = imagedata.get(f'{{{R_NAMESPACE}}}id')
                                if rid:
                                    part = self.tai_lieu.part.related_parts.get(rid)
                                    if part:
                                        self.dem_anh += 1
                                        content_type = getattr(part, 'content_type', '')
                                        ext = 'png'
                                        if 'wmf' in content_type:
                                            ext = 'wmf'
                                        elif 'emf' in content_type:
                                            ext = 'emf'
                                        elif 'jpeg' in content_type:
                                            ext = 'jpg'

                                        ten_anh_goc = f'formula_{self.dem_anh}.{ext}'
                                        if not os.path.exists(self.thu_muc_anh):
                                            os.makedirs(self.thu_muc_anh)

                                        duong_dan_anh = os.path.join(self.thu_muc_anh, ten_anh_goc)
                                        with open(duong_dan_anh, 'wb') as f:
                                            f.write(part.blob)

                                        # Chuyển WMF/EMF → PNG (XeLaTeX không hỗ trợ)
                                        ten_anh = ten_anh_goc
                                        if ext in ('wmf', 'emf'):
                                            try:
                                                from PIL import Image
                                                img = Image.open(duong_dan_anh)
                                                ten_anh = f'formula_{self.dem_anh}.png'
                                                duong_dan_png = os.path.join(self.thu_muc_anh, ten_anh)
                                                new_size = (img.size[0] * 3, img.size[1] * 3)
                                                img_resized = img.resize(new_size, Image.LANCZOS)
                                                img_resized.save(duong_dan_png)
                                                os.remove(duong_dan_anh)
                                            except Exception:
                                                pass

                                        ten_thu_muc = os.path.basename(self.thu_muc_anh)
                                        cong_thuc_parts.append(
                                            rf'\includegraphics[height=1.5em]{{{ten_thu_muc}/{ten_anh}}}'
                                        )

                # 3. Fallback: lấy text nếu không có OMML/OLE
                if not omath_list and not cong_thuc_parts:
                    text = para.text.strip()
                    if text:
                        cong_thuc_parts.append(loc_ky_tu(text))

            # Fallback cuối: cell.text
            if not cong_thuc_parts:
                cell_text = cell.text.strip()
                if cell_text:
                    cong_thuc_parts.append(loc_ky_tu(cell_text))
        except Exception:
            pass
        return ' '.join(cong_thuc_parts)

    def xu_ly_bang_cong_thuc(self, bang: Table) -> str:
        # Chuyển bảng công thức thành equation environment (có \tag)
        latex = ""
        try:
            for hang in bang.rows:
                if len(hang.cells) >= 2:
                    cong_thuc = self.trich_xuat_omml_tu_cell(hang.cells[0])
                    cell_so = hang.cells[1].text.strip()

                    so_match = re.match(r'^\((\d+)\)$', cell_so)
                    if so_match:
                        so = so_match.group(1)
                        latex += r"\begin{equation}" + "\n"
                        if cong_thuc.strip():
                            latex += f"  {cong_thuc}\n"
                        else:
                            latex += f"  \\text{{[Công thức {so}]}}\n"
                        latex += rf"  \tag{{{so}}}" + "\n"
                        latex += r"\end{equation}" + "\n\n"
        except Exception:
            pass
        return latex

    def xu_ly_bang(self, bang: Table) -> str:
        # Xử lý bảng: phát hiện loại rồi sinh LaTeX tương ứng

        # Bước 1: bảng layout → trích xuất text
        if self.la_bang_layout(bang):
            return self.trich_xuat_noi_dung_bang_layout(bang)

        # Bước 2: bảng công thức → equation
        if self.la_bang_cong_thuc(bang):
            return self.xu_ly_bang_cong_thuc(bang)

        # Bước 3: bảng Mục lục → \tableofcontents
        if self.la_table_of_contents(bang):
            if not self.toc_da_sinh:
                self.toc_da_sinh = True
                return r"\tableofcontents" + "\n\\newpage\n\n"
            return ""

        # Bước 4: bảng chứa ảnh → figure
        if self.la_bang_chua_anh(bang):
            danh_sach_anh = self.trich_xuat_anh_tu_bang(bang)
            if danh_sach_anh:
                latex = ""
                for ten_anh in danh_sach_anh:
                    latex += self.tao_latex_hinh(ten_anh)
                return latex

        # Bước 5: bảng dữ liệu thường → tabular
        self.so_bang_noi_dung += 1
        self.dem_bang += 1
        so_cot = len(bang.columns)
        cot = '|' + '|'.join(['p{2cm}'] * so_cot) + '|'
        vi_tri = "[H]" if self.mode == 'demo' else "[htbp]"

        latex = rf"\begin{{table}}{vi_tri}" + "\n"
        latex += r"  \centering" + "\n"
        latex += rf"  \begin{{tabular}}{{{cot}}}" + "\n"
        latex += r"  \hline" + "\n"

        for hang in bang.rows:
            dong = []
            for o in hang.cells:
                dong.append(loc_ky_tu(o.text.strip()))
            latex += "    " + " & ".join(dong) + r" \\" + "\n"
            latex += r"  \hline" + "\n"

        latex += r"  \end{tabular}" + "\n"
        latex += rf"  \caption{{Bảng {self.dem_bang}}}" + "\n"
        latex += rf"  \label{{tab:bang{self.dem_bang}}}" + "\n"
        latex += r"\end{table}" + "\n\n"
        return latex

    # HEADING: phát hiện từ style và nội dung

    def phat_hien_heading(self, text: str) -> tuple:
        # Phát hiện heading từ nội dung (khi Word không gán style)
        text_strip = text.strip()
        for pattern, latex_cmd in HEADING_PATTERNS:
            match = re.match(pattern, text_strip, re.IGNORECASE)
            if match:
                return (latex_cmd, text_strip)
        return (None, None)

    # ĐOẠN VĂN: xử lý toàn bộ paragraph → LaTeX

    def xu_ly_doan_van(self, doan_van) -> str:
        # Xử lý một đoạn văn: heading, danh sách, công thức, ảnh, text
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

        # Xử lý từng run (formatting)
        noi_dung = ""
        for run in doan_van.runs:
            noi_dung += self.xu_ly_run(run)

        # Áp dụng hyperlink vào nội dung
        hyperlinks = self.lay_tat_ca_hyperlink(doan_van)
        for link_text, url in hyperlinks.items():
            if link_text in noi_dung:
                url_escaped = url.replace('%', '\\%').replace('#', '\\#')
                text_escaped = loc_ky_tu(link_text)
                href_cmd = rf"\href{{{url_escaped}}}{{{text_escaped}}}"
                noi_dung = noi_dung.replace(link_text, href_cmd, 1)

        # Trích xuất ảnh
        danh_sach_anh = self.trich_xuat_anh(doan_van)
        numId, ilvl = self.lay_thong_tin_danh_sach(doan_van)

        ket_qua = ""
        for ten_anh in danh_sach_anh:
            ket_qua += self.tao_latex_hinh(ten_anh)

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
            for text_goc, latex_ct in cong_thuc_list:
                if latex_ct.strip():
                    noi_dung = noi_dung.replace(text_goc, f'${latex_ct}$')

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

    def sinh_noi_dung(self) -> str:
        # Duyệt toàn bộ phần tử và sinh nội dung LaTeX
        self.doc_file_word()
        noi_dung = []
        thu_tu_phan_tu = self.lay_thu_tu_phan_tu()
        self.tong_so_phan_tu = len(thu_tu_phan_tu)

        for idx, (loai, phan_tu) in enumerate(thu_tu_phan_tu):
            self.vi_tri_hien_tai = idx
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
