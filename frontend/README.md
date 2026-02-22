# Word2LaTeX Frontend

Giao diện React hiện đại cho nền tảng chuyển đổi Word sang LaTeX chuẩn học thuật.

## 🚀 Tech Stack

- **Framework**: React 18 + Vite
- **Styling**: Tailwind CSS (Glassmorphism theme)
- **Animation**: Framer Motion
- **Icons**: Lucide React
- **Drag & Drop**: react-dropzone
- **Backend**: Firebase (Auth + Firestore)
- **Toast**: react-hot-toast

## 📁 Cấu trúc thư mục

```
src/
├── assets/              # Hình ảnh, fonts
├── components/          # UI components dùng chung
│   ├── NutBam.jsx       # Button với nhiều biến thể
│   ├── KhungThongBao.jsx # Alert/notification
│   ├── Loading.jsx      # Loading spinners & screens
│   └── ThanhDieuHuong.jsx # Navigation header
├── features/            # Logic theo tính năng
│   ├── xac_thuc/        # Đăng nhập/Đăng ký
│   │   └── TrangDangNhap.jsx
│   ├── chuyen_doi/      # Upload & chuyển đổi
│   │   ├── KhuVucKeoTha.jsx
│   │   └── TrangChuyenDoi.jsx
│   └── lich_su/         # Lịch sử chuyển đổi
│       ├── BangLichSu.jsx
│       └── TrangLichSu.jsx
├── services/            # API & Firebase
│   ├── firebaseConfig.js
│   └── api.js
├── utils/               # Hàm tiện ích
│   └── index.js
├── App.jsx              # Root component
├── main.jsx             # Entry point
└── index.css            # Global styles
```

## 🛠️ Cài đặt

1. **Cài dependencies:**
```bash
cd frontend
npm install
```

2. **Cấu hình Firebase:**
```bash
cp .env.example .env
# Điền Firebase credentials vào .env
```

3. **Chạy development:**
```bash
npm run dev
```

4. **Build production:**
```bash
npm run build
```

## 🔐 Cấu hình Firebase

Tạo project Firebase và bật:
- **Authentication**: Email/Password + Google Sign-In
- **Firestore**: Database cho lịch sử chuyển đổi

Schema Firestore `lich_su_chuyen_doi`:
```json
{
  "uid": "string",
  "tenFileGoc": "string",
  "trangThai": "Thành công | Thất bại | Đang xử lý",
  "thoiGian": "timestamp",
  "duongDanTaiVe": "string"
}
```

## 🎨 UI/UX Features

- **Dark theme** học thuật (Deep Blue/Slate)
- **Glassmorphism** cards (`backdrop-blur-md`)
- **Animations** với Framer Motion
- **Glow effect** khi kéo file vào dropzone
- **Responsive** trên mọi thiết bị

## 📝 Quy ước code

- Component: `PascalCase` tiếng Việt (VD: `TrangDangNhap`)
- Hàm/Biến: `camelCase` tiếng Việt (VD: `xuLyDangNhap`)
- Comment: 1 dòng `//` tiếng Việt sau khai báo hàm
- Error handling: Luôn dùng `try...catch` + Toast

## 🔗 Kết nối Backend

Cấu hình API URL trong `.env`:
```env
VITE_API_URL=http://localhost:8000
```

## 📄 License

MIT License - Word2LaTeX Research Project © 2026
