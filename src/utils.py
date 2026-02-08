# utils.py - Tiện ích: escape ký tự, biên dịch LaTeX, dọn file rác

import os
import re
import subprocess

def loc_ky_tu(text: str) -> str:
    # Escape các ký tự đặc biệt LaTeX (\, %, $, _, &, #, {, }, ~, ^)
    if not text:
        return ""
    ky_tu_dac_biet = [
        ('\\', r'\textbackslash{}'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('_', r'\_'),
        ('&', r'\&'),
        ('#', r'\#'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\textasciicircum{}'),
    ]
    ket_qua = text
    for ky_tu, thay_the in ky_tu_dac_biet:
        ket_qua = ket_qua.replace(ky_tu, thay_the)
    return ket_qua

def don_dep_file_rac(duong_dan_dau_ra: str):
    # Xóa các file phụ sinh ra từ quá trình biên dịch LaTeX
    base_name = os.path.splitext(duong_dan_dau_ra)[0]
    cac_duoi_rac = [
        '.aux', '.log', '.out', '.toc',
        '.fdb_latexmk', '.fls', '.synctex.gz',
    ]
    for duoi in cac_duoi_rac:
        file_rac = base_name + duoi
        if os.path.exists(file_rac):
            try:
                os.remove(file_rac)
                print(f"Đã xóa: {file_rac}")
            except Exception:
                pass

def bien_dich_latex(duong_dan_dau_ra: str) -> bool:
    # Biên dịch file .tex bằng XeLaTeX, trả về True nếu thành công
    ten_file = os.path.basename(duong_dan_dau_ra)
    thu_muc = os.path.dirname(duong_dan_dau_ra)

    print(f"\nBắt đầu biên dịch XeLaTeX: {ten_file}")
    try:
        ket_qua = subprocess.run(
            ['xelatex', '-interaction=nonstopmode', ten_file],
            cwd=thu_muc if thu_muc else '.',
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=120,
        )

        if ket_qua.returncode == 0:
            print(f" Biên dịch thành công: {ten_file.replace('.tex', '.pdf')}")
            return True
        else:
            print(f" Biên dịch thất bại (exit code: {ket_qua.returncode})")
            if ket_qua.stderr:
                print(f"Lỗi: {ket_qua.stderr[:500]}")
            return False
    except FileNotFoundError:
        print(" Không tìm thấy xelatex. Vui lòng cài đặt TeX Live hoặc MiKTeX.")
        return False
    except subprocess.TimeoutExpired:
        print(" Biên dịch quá thời gian (>120s)")
        return False
    except Exception as e:
        print(f" Lỗi: {e}")
        return False
