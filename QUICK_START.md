# 🚀 Quick Start - Word2LaTeX Platform

## ✅ Hệ thống đã chạy thành công!

### 🔥 Backend API
- **URL:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **Status:** ✅ Running

### 💎 Frontend
- **URL:** http://localhost:3000
- **Status:** ✅ Running

---

## 📋 Các bước tiếp theo

### 1️⃣ Cấu hình Firebase (Bắt buộc)

Tạo file `.env` trong thư mục `frontend/`:

```bash
cd frontend
cp .env.example .env
```

Sau đó mở [HUONG_DAN_FIREBASE.md](HUONG_DAN_FIREBASE.md) và làm theo hướng dẫn để lấy Firebase credentials.

### 2️⃣ Test API với Swagger

1. Mở http://localhost:8000/docs
2. Chọn **POST /api/chuyen-doi**
3. Click "Try it out"
4. Upload file `.docx` (trong thư mục `input_data/`)
5. Chọn `template_type`: "onecolumn" hoặc "twocolumn"
6. Click "Execute"
7. Copy link download từ response

**Ví dụ response:**
```json
{
  "trang_thai": "thanh_cong",
  "job_id": "abc-123",
  "ten_file_dau_ra": "document_20260222_143022.tex",
  "duong_dan_tai_ve": "/api/tai-ve/document_20260222_143022.tex"
}
```

### 3️⃣ Test Frontend

1. Mở http://localhost:3000
2. **Lưu ý:** Cần cấu hình Firebase trước khi đăng nhập
3. Sau khi có Firebase:
   - Đăng ký tài khoản mới hoặc đăng nhập Google
   - Upload file `.docx`
   - Xem tiến trình chuyển đổi
   - Download file `.tex`
   - Xem lịch sử trong tab "Lịch Sử"

---

## 🛠️ Lệnh hữu ích

### Dừng các server
```powershell
# Trong terminal đang chạy, nhấn: Ctrl+C
```

### Chạy lại Backend
```powershell
& D:\Word2Latex_Research\.venv\Scripts\Activate.ps1
cd backend
python main.py
```

### Chạy lại Frontend
```powershell
cd frontend
npm run dev
```

### Xem logs Backend
Logs sẽ hiển thị trong terminal backend khi có request.

### Kill port nếu bị conflict
```powershell
# Nếu port 8000 đang được sử dụng
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Nếu port 3000 đang được sử dụng
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

---

## 📁 Cấu trúc thư mục quan trọng

```
Word2Latex_Research/
├── backend/
│   ├── main.py              # FastAPI server ✅
│   ├── uploads/             # File upload tạm thời
│   └── outputs/             # File .tex đã chuyển đổi
│       └── images/          # Ảnh từ Word
│
├── frontend/
│   ├── src/
│   │   ├── features/
│   │   │   ├── xac_thuc/   # Login/Register
│   │   │   ├── chuyen_doi/ # Upload & Conversion
│   │   │   └── lich_su/    # History
│   │   └── services/
│   │       ├── firebaseConfig.js  # Firebase setup
│   │       └── api.js             # API calls
│   └── .env                 # ⚠️ CẦN TẠO FILE NÀY
│
└── src/
    ├── chuyen_doi.py        # Python conversion engine
    └── ...
```

---

## 🎯 Test flow hoàn chỉnh

### A. Test Backend trực tiếp (không cần Frontend)

```powershell
# Dùng curl hoặc Postman
curl -X POST "http://localhost:8000/api/chuyen-doi" \
  -F "file=@input_data/word_template(mau5).docx" \
  -F "template_type=onecolumn"
```

Hoặc dùng Swagger UI tại http://localhost:8000/docs (dễ hơn!)

### B. Test Frontend + Backend

1. ✅ Backend running: http://localhost:8000
2. ✅ Frontend running: http://localhost:3000
3. ⚠️ Cấu hình Firebase (xem [HUONG_DAN_FIREBASE.md](HUONG_DAN_FIREBASE.md))
4. 🎉 Sử dụng giao diện web

---

## 🐛 Troubleshooting

### Backend không chạy?
```powershell
# Kiểm tra venv đã activate chưa
& D:\Word2Latex_Research\.venv\Scripts\Activate.ps1

# Kiểm tra dependencies
pip list | findstr fastapi

# Nếu thiếu, cài lại
cd backend
pip install -r requirements.txt
```

### Frontend không chạy?
```powershell
# Xóa node_modules và cài lại
cd frontend
Remove-Item -Recurse -Force node_modules
npm install
npm run dev
```

### Lỗi CORS?
Kiểm tra `backend/main.py` có dòng:
```python
allow_origins=["http://localhost:3000"]
```

### Frontend không gọi được API?
- Kiểm tra `frontend/src/services/api.js` có `baseURL: 'http://localhost:8000'`
- Kiểm tra Backend đang chạy: http://localhost:8000/health

---

## 📚 Documentation

- **[README.md](README.md)** - Tổng quan dự án
- **[DOCUMENTATION.txt](DOCUMENTATION.txt)** - Chi tiết kỹ thuật Python backend
- **[HUONG_DAN_FIREBASE.md](HUONG_DAN_FIREBASE.md)** - Hướng dẫn setup Firebase
- **[HUONG_DAN_BACKEND.md](HUONG_DAN_BACKEND.md)** - Chi tiết về FastAPI backend

---

## 🎉 Chúc mừng!

Hệ thống Word2LaTeX của bạn đã sẵn sàng! 🚀

**Next steps:**
1. ⚠️ Cấu hình Firebase để dùng Frontend
2. 🧪 Test với file Word mẫu trong `input_data/`
3. 🎨 Tùy chỉnh UI/UX trong `frontend/src/`
4. 🚀 Deploy lên production (Vercel + Railway/Heroku)

**Support:**
- Swagger API Docs: http://localhost:8000/docs
- Frontend Dev: http://localhost:3000
