# Hướng dẫn chạy Backend

## 1. Kích hoạt Virtual Environment

```powershell
# Windows PowerShell
D:\Word2Latex_Research\.venv\Scripts\Activate.ps1

# Hoặc Command Prompt
D:\Word2Latex_Research\.venv\Scripts\activate.bat
```

## 2. Cài đặt dependencies

```bash
cd D:\Word2Latex_Research
pip install -r backend/requirements.txt
```

## 3. Chạy FastAPI server

```bash
cd backend
python main.py
```

Hoặc dùng uvicorn trực tiếp:
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 4. Kiểm tra server

Backend sẽ chạy tại: **http://localhost:8000**

- Truy cập: http://localhost:8000 - Xem thông tin API
- Truy cập: http://localhost:8000/docs - Swagger UI (test API)
- Truy cập: http://localhost:8000/health - Health check

## 5. Test API với Swagger

1. Mở http://localhost:8000/docs
2. Chọn endpoint **POST /api/chuyen-doi**
3. Nhấn "Try it out"
4. Upload file .docx
5. Chọn template_type: "onecolumn" hoặc "twocolumn"
6. Nhấn "Execute"
7. Copy đường dẫn từ response để download file .tex

## 6. Endpoints API

### POST /api/chuyen-doi
Upload file .docx và chuyển đổi sang LaTeX

**Request:**
- file: File .docx (max 10MB)
- template_type: "onecolumn" hoặc "twocolumn"

**Response:**
```json
{
  "trang_thai": "thanh_cong",
  "job_id": "uuid-string",
  "ten_file_goc": "document.docx",
  "ten_file_dau_ra": "document_20260222_143022.tex",
  "duong_dan_tai_ve": "/api/tai-ve/document_20260222_143022.tex",
  "thong_diep": "Chuyển đổi hoàn tất!"
}
```

### GET /api/tai-ve/{filename}
Download file LaTeX đã chuyển đổi

### GET /api/trang-thai/{job_id}
Kiểm tra trạng thái chuyển đổi

### DELETE /api/xoa/{filename}
Xóa file output (dọn dẹp)

## 7. Cấu trúc thư mục backend

```
backend/
├── main.py              # FastAPI application
├── requirements.txt     # Backend dependencies
├── uploads/            # Thư mục tạm để lưu file upload
└── outputs/            # Thư mục chứa file .tex đã chuyển đổi
    └── images/         # Ảnh từ Word document
```

## 8. Kết nối với Frontend

Frontend React đang gọi API tại `http://localhost:8000` trong file:
- `frontend/src/services/api.js`

Đảm bảo cả frontend (port 3000) và backend (port 8000) đều đang chạy.

## 9. Production Deployment

Để deploy lên production:

1. **Thay đổi CORS:**
   ```python
   # backend/main.py
   allow_origins=["https://your-frontend-domain.com"]
   ```

2. **Dùng production ASGI server:**
   ```bash
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

3. **Thêm .env cho backend** (nếu cần database, Redis, etc.)

4. **Sử dụng Nginx reverse proxy**

## 10. Troubleshooting

### Lỗi: "Module not found"
```bash
# Đảm bảo đã cài dependencies
pip install -r backend/requirements.txt
```

### Lỗi: "Address already in use"
```bash
# Port 8000 đang được sử dụng, kill process:
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Hoặc đổi port
uvicorn main:app --port 8001
```

### Lỗi: "Cannot find module 'chuyen_doi'"
```bash
# Chạy từ thư mục backend/
cd backend
python main.py
```
