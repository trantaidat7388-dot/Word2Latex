# xu_ly_anh.py - Xử lý phân tích và lọc ảnh (trang trí vs nội dung)

import math
import re
from PIL import Image, ImageStat, ImageFilter

class BoLocAnh:
    # Bộ lọc ảnh: phân biệt ảnh nội dung (photo, chart) và ảnh trang trí (logo, icon)

    # PHÂN TÍCH ẢNH ĐƠN LẺ

    @staticmethod
    def tinh_entropy_anh(duong_dan_hoac_anh) -> float:
        # Tính entropy (Shannon) đo độ hỗn loạn màu: trang trí <3.5, nội dung >5.0
        try:
            if isinstance(duong_dan_hoac_anh, str):
                im = Image.open(duong_dan_hoac_anh)
            else:
                im = duong_dan_hoac_anh
            histogram = im.histogram()
            histogram_length = sum(histogram)
            if histogram_length == 0:
                return 0
            samples_probability = [float(h) / histogram_length for h in histogram]
            entropy = -sum([p * math.log(p, 2) for p in samples_probability if p != 0])
            return entropy
        except Exception as e:
            print(f"[Cảnh báo] Lỗi tinh_entropy_anh: {e}")
            return 0

    @staticmethod
    def tinh_so_mau_anh(duong_dan_hoac_anh) -> int:
        # Đếm số màu duy nhất: logo ít màu (<50), photo nhiều màu (>1000)
        try:
            if isinstance(duong_dan_hoac_anh, str):
                im = Image.open(duong_dan_hoac_anh)
            else:
                im = duong_dan_hoac_anh
            colors = im.getcolors(maxcolors=100000)
            if colors is None:
                return 100000
            return len(colors)
        except Exception as e:
            print(f"[Cảnh báo] Lỗi tinh_so_mau_anh: {e}")
            return 0

    @staticmethod
    def tinh_do_phuc_tap_anh(duong_dan_hoac_anh) -> dict:
        # Phát hiện cạnh (Edge Detection) và đo độ biến thiên (variance)
        try:
            if isinstance(duong_dan_hoac_anh, str):
                im = Image.open(duong_dan_hoac_anh).convert('L')
            else:
                im = duong_dan_hoac_anh.convert('L')
            edges = im.filter(ImageFilter.FIND_EDGES)
            edge_stat = ImageStat.Stat(edges)
            edge_mean = edge_stat.mean[0]
            edge_stddev = edge_stat.stddev[0]

            stat = ImageStat.Stat(im)
            variance = stat.var[0]

            return {
                'edge_mean': edge_mean,
                'edge_stddev': edge_stddev,
                'variance': variance,
            }
        except Exception as e:
            print(f"[Cảnh báo] Lỗi tinh_do_phuc_tap_anh: {e}")
            return {'edge_mean': 0, 'edge_stddev': 0, 'variance': 0}

    @staticmethod
    def phan_tich_histogram(duong_dan_hoac_anh) -> dict:
        # Phân tích histogram: logo ít peaks + dominant cao, photo ngược lại
        try:
            if isinstance(duong_dan_hoac_anh, str):
                im = Image.open(duong_dan_hoac_anh).convert('L')
            else:
                im = duong_dan_hoac_anh.convert('L')
            histogram = im.histogram()
            total = sum(histogram)
            if total == 0:
                return {'num_peaks': 0, 'dominant_ratio': 1.0}

            peaks = 0
            threshold = total * 0.02
            for i in range(1, 255):
                if histogram[i] > threshold:
                    if histogram[i] > histogram[i - 1] and histogram[i] > histogram[i + 1]:
                        peaks += 1

            sorted_hist = sorted(histogram, reverse=True)
            dominant_ratio = sum(sorted_hist[:5]) / total

            return {'num_peaks': peaks, 'dominant_ratio': dominant_ratio}
        except Exception as e:
            print(f"[Cảnh báo] Lỗi phan_tich_histogram: {e}")
            return {'num_peaks': 0, 'dominant_ratio': 1.0}

    # SCORING SYSTEM

    @classmethod
    def la_anh_noi_dung(cls, duong_dan_hoac_anh) -> bool:
        # Tổng hợp điểm từ các tiêu chí: >= 4 = nội dung, < 4 = trang trí (max 12)
        try:
            if isinstance(duong_dan_hoac_anh, str):
                im = Image.open(duong_dan_hoac_anh)
            else:
                im = duong_dan_hoac_anh
                
            entropy = cls.tinh_entropy_anh(im)
            so_mau = cls.tinh_so_mau_anh(im)
            do_phuc_tap = cls.tinh_do_phuc_tap_anh(im)
            hist_info = cls.phan_tich_histogram(im)

        except Exception as e:
            print(f"[Cảnh báo] Lỗi la_anh_noi_dung quá trình tính toán tính năng: {e}")
            return False

        diem = 0

        if entropy >= 5.0:
            diem += 3
        elif entropy >= 4.0:
            diem += 2
        elif entropy >= 3.0:
            diem += 1

        if so_mau >= 1000:
            diem += 3
        elif so_mau >= 200:
            diem += 2
        elif so_mau >= 50:
            diem += 1

        if do_phuc_tap['edge_mean'] >= 20:
            diem += 2
        elif do_phuc_tap['edge_mean'] >= 10:
            diem += 1

        if do_phuc_tap['variance'] >= 2000:
            diem += 2
        elif do_phuc_tap['variance'] >= 500:
            diem += 1

        if hist_info['num_peaks'] >= 5:
            diem += 1
        if hist_info['dominant_ratio'] < 0.5:
            diem += 1

        return diem >= 4

    # LỌC ẢNH TRANG TRÍ (dựa trên metadata + context)

    @staticmethod
    def la_anh_trang_tri(kich_thuoc_anh, doan_van,
                          da_qua_phan_noi_dung: bool,
                          dem_paragraph_thuc: int,
                          tong_so_phan_tu: int,
                          vi_tri_hien_tai: int,
                          kich_thuoc_anh_da_xem: list) -> bool:
        # Phát hiện ảnh trang trí dựa trên metadata (kích thước, vị trí, ngữ cảnh)
        rong, cao = kich_thuoc_anh

        if rong == 0 or cao == 0:
            return True

        # Whitelist: style "Image" hoặc "FigureCaption" chắc chắn là ảnh nội dung
        style_noi_dung = ['Image', 'FigureCaption', 'image', 'figurecaption']
        if doan_van.style and doan_van.style.name in style_noi_dung:
            return False

        ty_le = rong / cao if cao > 0 else 0

        if rong > 6500000 or cao > 8500000:
            return True

        if rong < 400000 and cao < 400000:
            return True

        if not da_qua_phan_noi_dung:
            return True

        style_trang_tri = ['Title', 'Subtitle', 'Heading 1', 'Abstract', 'Cover Page', 'Title Page']
        if doan_van.style.name in style_trang_tri:
            return True

        text_upper = doan_van.text.strip().upper()
        text_lower = doan_van.text.strip()

        tu_khoa_tieu_de = [
            'ABSTRACT', 'ACKNOWLEDGMENT', 'ACKNOWLEDGEMENT',
            'TÓM TẮT', 'LỜI CẢM ƠN', 'COVER PAGE', 'TITLE PAGE',
        ]
        for tu in tu_khoa_tieu_de:
            if tu in text_upper and len(text_upper) < 200:
                return True

        tu_khoa_trang_tri = [
            'ARTIST PROFILE', 'AUTHOR PROFILE', 'PORTRAIT', 'LOGO',
            'ICON', 'DECORATION', 'HỒ SƠ NGHỆ SĨ', 'TIỂU SỬ', 'CHÂN DUNG',
        ]
        for tu in tu_khoa_trang_tri:
            if tu in text_upper:
                return True

        if dem_paragraph_thuc < 20:
            return True

        if tong_so_phan_tu > 0:
            vi_tri_phan_tram = (vi_tri_hien_tai / tong_so_phan_tu) * 100
            if vi_tri_phan_tram < 8 or vi_tri_phan_tram > 95:
                return True

        if ty_le > 15 or ty_le < 0.06:
            return True

        co_nam = bool(re.search(r'\b(19|20)\d{2}\b', text_lower))
        co_dau_cham_nhieu = text_lower.count('.') >= 2
        co_chu_hoa = bool(re.search(r'[A-Z][a-z]+', text_lower))
        co_mo_ta = len(text_lower) > 40

        if co_nam and co_dau_cham_nhieu and co_mo_ta:
            return False

        if 0.8 < ty_le < 1.2:
            if len(text_lower) < 50:
                return True
            if not (co_nam and co_dau_cham_nhieu):
                return True

        kich_thuoc_tuple = (rong, cao)
        dem_trung = sum(
            1 for kt in kich_thuoc_anh_da_xem
            if abs(kt[0] - rong) < 50000 and abs(kt[1] - cao) < 50000
        )
        if dem_trung >= 2:
            return True
        kich_thuoc_anh_da_xem.append(kich_thuoc_tuple)

        text_xung_quanh = doan_van.text.strip()
        if len(text_xung_quanh) == 0:
            so_run_co_anh = sum(
                1 for run in doan_van.runs
                if run._element.findall(
                    './/{http://schemas.openxmlformats.org/drawingml/2006/main}blip'
                )
            )
            so_run_tong = len(doan_van.runs)
            if so_run_tong > 0 and so_run_co_anh == so_run_tong:
                if rong > 5000000 or cao > 5000000:
                    return True

        co_tu_khoa_hinh = False
        tu_khoa_hinh = [
            'FIGURE', 'FIG', 'HÌNH', 'ẢNH', 'IMAGE', 'PHOTO',
            'CHART', 'GRAPH', 'DIAGRAM',
        ]
        for tu in tu_khoa_hinh:
            if tu in text_upper:
                co_tu_khoa_hinh = True
                break

        if co_tu_khoa_hinh:
            text_sach = re.sub(r'[^A-ZÀ-Ỹ0-9\s]', '', text_upper)
            pattern_caption_don = r'^(HÌNH|FIGURE|FIG|ẢNH|IMAGE)\s*\d+\s*$'
            pattern_caption_ngan = r'^(HÌNH|FIGURE|FIG|ẢNH|IMAGE)\s*\d+\s*.{0,30}$'

            if re.match(pattern_caption_don, text_sach.strip()):
                return True

            if re.match(pattern_caption_ngan, text_upper.strip()):
                if not (co_nam and co_dau_cham_nhieu):
                    return True

        if not co_tu_khoa_hinh:
            if len(text_xung_quanh) < 80:
                if not (co_chu_hoa and co_dau_cham_nhieu and co_nam):
                    if rong > 2000000 or cao > 2000000:
                        return True

        return False
