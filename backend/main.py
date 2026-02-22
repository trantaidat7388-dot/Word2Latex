import os
import sys
import uuid
import shutil
import zipfile
import time
import asyncio
import re
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chuyen_doi import ChuyenDoiWordSangLatex
from utils import don_dep_file_rac, bien_dich_latex

# Khởi tạo FastAPI app
app = FastAPI(title="Word2LaTeX API", version="1.0.0")

# Cấu hình CORS - cho phép frontend truy cập (hỗ trợ nhiều port)
cors_allow_all = os.getenv('CORS_ALLOW_ALL', '0').strip() == '1'
cors_origins_raw = os.getenv('CORS_ORIGINS', '').strip()
cors_origins = [o.strip() for o in cors_origins_raw.split(',') if o.strip()]
if not cors_origins:
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if cors_allow_all else cors_origins,
    allow_credentials=False if cors_allow_all else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = Path(__file__).parent.parent
template_folder = base_dir / "input_data"
custom_template_folder = base_dir / "backend" / "custom_templates"
temp_folder = base_dir / "temp_jobs"
outputs_folder = base_dir / "outputs"

custom_template_folder.mkdir(parents=True, exist_ok=True)
temp_folder.mkdir(parents=True, exist_ok=True)
outputs_folder.mkdir(parents=True, exist_ok=True)


def in_log_loi(thong_diep: str, loi: Exception = None):
    # In log lỗi ra console để developer dễ debug
    if loi is not None:
        print(f"[LOI] {thong_diep}: {loi}")
    else:
        print(f"[LOI] {thong_diep}")


def doc_noi_dung_tex_an_toan(duong_dan: Path) -> str:
    # Đọc nội dung .tex an toàn với fallback encoding
    if not duong_dan.exists():
        return ''

    for enc in ['utf-8', 'utf-16', 'latin-1']:
        try:
            noi_dung = duong_dan.read_text(encoding=enc, errors='ignore')
            if noi_dung and noi_dung.strip():
                return noi_dung
        except Exception as loi:
            in_log_loi(f"Không thể đọc tex bằng encoding={enc}: {duong_dan}", loi)
    return ''


def xoa_thu_muc_an_toan(duong_dan: Path):
    # Xóa thư mục an toàn và không làm crash server nếu lỗi
    try:
        if duong_dan.exists():
            shutil.rmtree(duong_dan, ignore_errors=True)
    except Exception as loi:
        in_log_loi(f"Không thể xóa thư mục: {duong_dan}", loi)


async def don_dep_sau_15_phut(duong_dan: Path):
    # Dọn dẹp thư mục job sau 15 phút để user có thời gian tải ZIP
    try:
        await asyncio.sleep(900)
    except Exception as loi:
        in_log_loi(f"Lỗi sleep cleanup: {duong_dan}", loi)
    xoa_thu_muc_an_toan(duong_dan)


def chay_don_dep_sau_15_phut(duong_dan: Path):
    # Chạy cleanup async trong threadpool để không block request
    try:
        asyncio.run(don_dep_sau_15_phut(duong_dan))
    except Exception as loi:
        in_log_loi(f"Không thể chạy cleanup: {duong_dan}", loi)


def quet_xoa_thu_muc_mo_coi(thu_muc_goc: Path, so_gio_ton_tai_toi_da: int):
    # Quét và xóa các thư mục/file cũ còn tồn đọng để tránh tràn ổ đĩa
    if not thu_muc_goc.exists():
        return
    now = time.time()
    ttl_seconds = max(1, so_gio_ton_tai_toi_da) * 3600

    try:
        for item in thu_muc_goc.iterdir():
            try:
                mtime = item.stat().st_mtime
                if now - mtime < ttl_seconds:
                    continue
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
            except Exception as loi_item:
                in_log_loi(f"Không thể dọn item mồ côi: {item}", loi_item)
    except Exception as loi:
        in_log_loi(f"Không thể quét dọn thư mục: {thu_muc_goc}", loi)


@app.get("/")
def doc_api():
    # Endpoint gốc - hướng dẫn sử dụng API
    return {
        "message": "Word2LaTeX API đang hoạt động",
        "endpoints": {
            "/api/chuyen-doi": "POST - Upload file .docx và chuyển đổi",
            "/docs": "Xem Swagger documentation"
        }
    }


@app.get("/api/templates")
def lay_danh_sach_template():
    # Lấy danh sách tất cả templates (mặc định + custom)
    templates = []
    
    # Templates mặc định
    for name, label in [("onecolumn", "1 cột (mặc định)")]:
        tpl_path = template_folder / f"latex_template_{name}.tex"
        if tpl_path.exists():
            templates.append({
                "id": name,
                "ten": label,
                "loai": "mac_dinh",
                "kichThuoc": tpl_path.stat().st_size
            })
    
    # Templates custom do người dùng upload
    for tpl_file in custom_template_folder.glob("*.tex"):
        templates.append({
            "id": f"custom_{tpl_file.stem}",
            "ten": tpl_file.stem,
            "loai": "tuy_chinh",
            "kichThuoc": tpl_file.stat().st_size
        })
    
    return {"templates": templates}


@app.post("/api/templates/upload")
async def tai_len_template(file: UploadFile = File(...)):
    # Upload template LaTeX tùy chỉnh
    if not file.filename.endswith('.tex'):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .tex")
    
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:  # 2MB
        raise HTTPException(status_code=400, detail="File template quá lớn (tối đa 2MB)")
    
    # Kiểm tra nội dung có phải LaTeX hợp lệ
    text = contents.decode('utf-8', errors='ignore')
    if '\\documentclass' not in text and '\\begin{document}' not in text:
        raise HTTPException(status_code=400, detail="File không phải template LaTeX hợp lệ (thiếu documentclass hoặc begin{document})")
    
    # Lưu file
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in Path(file.filename).stem)
    save_path = custom_template_folder / f"{safe_name}.tex"
    
    with open(save_path, 'wb') as f:
        f.write(contents)
    
    return {
        "thanhCong": True,
        "template": {
            "id": f"custom_{safe_name}",
            "ten": safe_name,
            "loai": "tuy_chinh",
            "kichThuoc": len(contents)
        },
        "message": f"Đã tải lên template: {safe_name}"
    }


@app.delete("/api/templates/{template_id}")
def xoa_template(template_id: str):
    # Xóa template tùy chỉnh
    if not template_id.startswith("custom_"):
        raise HTTPException(status_code=400, detail="Không thể xóa template mặc định")
    
    name = template_id.replace("custom_", "", 1)
    file_path = custom_template_folder / f"{name}.tex"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Template không tồn tại")
    
    file_path.unlink()
    return {"thanhCong": True, "message": f"Đã xóa template: {name}"}


@app.post("/api/chuyen-doi")
async def chuyen_doi_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    template_type: str = Query("onecolumn", description="onecolumn hoặc custom_xxx")
):
    # Endpoint chuyển đổi file Word → LaTeX
    
    # Kiểm tra file extension
    if not file.filename.endswith('.docx'):
        raise HTTPException(
            status_code=400, 
            detail="Chỉ chấp nhận file .docx"
        )
    
    # Kiểm tra kích thước file (max 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(
            status_code=400,
            detail="File quá lớn. Kích thước tối đa 10MB"
        )
    
    job_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"[JOB {job_id}] Nhận yêu cầu chuyển đổi: {file.filename} template={template_type}")
    
    # Tạo tên file an toàn
    original_name = Path(file.filename).stem  # Tên không có extension
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in original_name)
    
    job_folder = temp_folder / f"job_{job_id}"
    job_folder.mkdir(parents=True, exist_ok=True)
    input_filename = f"{safe_name}_{timestamp}.docx"
    input_path = job_folder / input_filename
    output_filename = f"{safe_name}_{timestamp}.tex"
    output_path = job_folder / output_filename
    images_folder = job_folder / f"{safe_name}_{timestamp}"
    images_folder.mkdir(parents=True, exist_ok=True)

    with open(input_path, "wb") as f:
        f.write(contents)
    
    # Chọn template (mặc định hoặc custom)
    if template_type == "twocolumn":
        template_type = "onecolumn"

    if template_type.startswith("custom_"):
        custom_name = template_type.replace("custom_", "", 1)
        template_path = custom_template_folder / f"{custom_name}.tex"
    else:
        template_path = template_folder / "latex_template_onecolumn.tex"
    
    if not template_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Template không tồn tại: {template_path.name}"
        )
    
    zip_filename = output_filename.replace('.tex', '.zip')
    zip_path = job_folder / zip_filename

    da_thanh_cong = False

    try:
        thoi_gian_bat_dau = time.time()
        print(f"[JOB {job_id}] Bắt đầu chuyển đổi Word → LaTeX")
        bo_chuyen_doi = ChuyenDoiWordSangLatex(
            duong_dan_word=str(input_path),
            duong_dan_template=str(template_path),
            duong_dan_dau_ra=str(output_path),
            thu_muc_anh=str(images_folder),
            mode='demo'
        )
        bo_chuyen_doi.chuyen_doi()

        print(f"[JOB {job_id}] Đã tạo file .tex, bắt đầu biên dịch PDF")

        bien_dich_latex(str(output_path))

        print(f"[JOB {job_id}] Đã chạy xelatex, đọc log/metadata")

        so_trang = None
        try:
            log_path = output_path.with_suffix('.log')
            log_text = doc_noi_dung_tex_an_toan(log_path)
            match = re.search(r'Output written on .*?\((\d+) pages?[,\)]', log_text)
            if match:
                so_trang = int(match.group(1))
        except Exception as loi:
            in_log_loi(f"Không thể lấy số trang từ log job_id={job_id}", loi)

        don_dep_file_rac(str(output_path))

        print(f"[JOB {job_id}] Đã dọn file rác, chuẩn bị zip")

        if not output_path.exists():
            raise Exception("Không tạo được file .tex đầu ra")

        tex_raw = doc_noi_dung_tex_an_toan(output_path)
        if not tex_raw.strip():
            raise Exception("Nội dung LaTeX rỗng hoặc không đọc được")

        so_hinh_anh = 0
        so_cong_thuc = 0
        try:
            so_hinh_anh = len(re.findall(r'\\includegraphics', tex_raw))

            so_equation_env = len(re.findall(r'\\begin\{(equation\*?|align\*?|eqnarray\*?)\}', tex_raw))
            so_bracket_math = len(re.findall(r'\\\[', tex_raw))
            so_inline_math = len(re.findall(r'\\\(', tex_raw))
            so_dollar_blocks = len(re.findall(r'\$\$', tex_raw)) // 2
            so_cong_thuc = so_equation_env + so_bracket_math + so_inline_math + so_dollar_blocks
        except Exception as loi:
            in_log_loi(f"Không thể đếm metadata job_id={job_id}", loi)

        thoi_gian_xu_ly_giay = max(0.0, time.time() - thoi_gian_bat_dau)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if output_path.exists():
                zipf.write(output_path, output_filename)

            pdf_path = output_path.with_suffix('.pdf')
            if pdf_path.exists():
                zipf.write(pdf_path, pdf_path.name)

            if images_folder.exists():
                for image_file in images_folder.rglob('*'):
                    if image_file.is_file():
                        arcname = (Path('images') / image_file.relative_to(job_folder)).as_posix()
                        zipf.write(image_file, arcname)

        print(f"[JOB {job_id}] Hoàn tất zip: {zip_path.name}")

        tex_content = tex_raw

        da_thanh_cong = True
        background_tasks.add_task(chay_don_dep_sau_15_phut, job_folder)

        return JSONResponse(status_code=200, content={
            "thanh_cong": True,
            "tex_content": tex_content,
            "job_id": job_id,
            "ten_file_zip": zip_filename,
            "ten_file_latex": output_filename,
            "metadata": {
                "so_trang": so_trang,
                "so_hinh_anh": so_hinh_anh,
                "so_cong_thuc": so_cong_thuc,
                "thoi_gian_xu_ly_giay": round(thoi_gian_xu_ly_giay, 2)
            }
        })
    except Exception as loi:
        in_log_loi(f"Lỗi chuyển đổi job_id={job_id}", loi)
        thong_diep_loi = str(loi).strip() if str(loi) else "File Word không hợp lệ hoặc không thể xử lý"
        return JSONResponse(status_code=400, content={"error": f"Lỗi khi chuyển đổi: {thong_diep_loi}"})
    finally:
        if not da_thanh_cong:
            xoa_thu_muc_an_toan(job_folder)


@app.get("/api/tai-ve-zip/{job_id}")
def tai_ve_zip_theo_job(job_id: str):
    # Tải file ZIP theo job_id trong thư mục temp
    job_folder = temp_folder / f"job_{job_id}"
    if not job_folder.exists() or not job_folder.is_dir():
        raise HTTPException(status_code=404, detail="Job không tồn tại hoặc đã bị dọn")

    danh_sach_zip = sorted(job_folder.glob('*.zip'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not danh_sach_zip:
        raise HTTPException(status_code=404, detail="Không tìm thấy file .zip trong job")

    zip_path = danh_sach_zip[0]
    return FileResponse(
        path=str(zip_path),
        filename=zip_path.name,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={zip_path.name}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@app.on_event("startup")
def xu_ly_don_dep_khi_khoi_dong():
    # Dọn dẹp các thư mục/file mồ côi trong temp khi server khởi động
    try:
        so_gio_ttl = int(os.getenv('TEMP_TTL_HOURS', '6').strip() or '6')
    except Exception as loi:
        in_log_loi('Giá trị TEMP_TTL_HOURS không hợp lệ, dùng mặc định 6 giờ', loi)
        so_gio_ttl = 6
    quet_xoa_thu_muc_mo_coi(temp_folder, so_gio_ttl)

    try:
        so_gio_ttl_output = int(os.getenv('OUTPUT_TTL_HOURS', '24').strip() or '24')
    except Exception as loi:
        in_log_loi('Giá trị OUTPUT_TTL_HOURS không hợp lệ, dùng mặc định 24 giờ', loi)
        so_gio_ttl_output = 24
    quet_xoa_thu_muc_mo_coi(outputs_folder, so_gio_ttl_output)


@app.get("/health")
def kiem_tra_suc_khoe():
    # Health check endpoint
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Chạy server với uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload khi code thay đổi (chỉ dùng development)
    )
