#  Word2LaTeX Research Project

Hệ thống nâng cao hỗ trợ chuyển đổi tài liệu Word (.docx) sang định dạng LaTeX chuẩn học thuật, tích hợp công nghệ xử lý công thức toán học và hình ảnh thông minh.

---

##  Giới thiệu Công nghệ & Thuật toán

Dự án sử dụng kiến trúc Backend-Frontend kết hợp, với các công nghệ lõi như sau:

### 1. Backend (Python & FastAPI)
Backend đóng vai trò là lõi chuyển đổi (Conversion Engine) với các module chuyên biệt:
- **FastAPI & Uvicorn**: Framework web tốc độ cao để xây dựng RESTful API xử lý file upload đồng thời.
- **python-docx**: Thư viện phân tích cấu trúc mã nguồn XML của file Word (đọc paragraphs, runs, tables, styles).
- **Thuật toán State Machine (Máy trạng thái)**: Sử dụng các cờ (flags) để bóc tách ngữ nghĩa tài liệu (Semantic Parsing) thành các vùng như Title, Abstract, Keywords, Body, Authors.
- **Thuật toán xử lý Toán học (Dual Pipeline)**:
  - OMML (Office Math): Dùng XSLT biến đổi từ mã OMML của Word sang MathML, sau đó phân tích thành LaTeX.
  - OLE Equation 3.0: Xây dựng trình parser nhị phân MTEF v3 tùy chỉnh để giải mã trực tiếp các công thức Equation Editor cũ thành LaTeX.
- **Thuật toán Chấm điểm Hình ảnh (Image Scoring)**: 
  Sử dụng thư viện Pillow kết hợp các phép phân tích ma trận điểm ảnh:
  - *Entropy Analysis* (Mức độ phức tạp thông tin)
  - *Color Variance* (Độ đa dạng màu sắc)
  - *Edge Detection* (Phát hiện biên/cạnh bằng bộ lọc Sobel)
  - *Histogram Analysis* (Phân tích khoảng sáng tối)
   Các bước này nhằm phân loại và tự động loại bỏ các hình ảnh trang trí rườm rà (decorative), chỉ giữ lại hình minh họa nội dung chính (content image).

### 2. Frontend (React 18 & Vite)
- **Vite & React**: Framework xây dựng giao diện người dùng (UI) Single Page Application nhanh chóng.
- **Tailwind CSS & Framer Motion**: Thiết kế UI/UX theo phong cách Glassmorphism (kính mờ), thêm hiệu ứng chuyển động mượt mà.
- **Firebase Auth & Firestore**: Quản lý định danh người dùng (Google/Email login) và lưu trữ lịch sử chuyển đổi thời gian thực.

---

##  Chi tiết Cấu trúc Thư mục & File

###  Bản đồ File hệ thống
- **start.bat**: Script Windows tự động thiết lập môi trường và khởi chạy đồng thời cả Backend (port 8000) và Frontend (port 5173).
- **ackend/main.py**: Điểm vào của API FastAPI. Định nghĩa các endpoint (như /api/chuyen-doi, /api/tai-ve-zip) và quản lý luồng nhận file Word, gọi lõi src để xử lý, sau đó gom kết quả File .tex và images/ vào file ZIP trả về cho người dùng.
- **src/chuyen_doi.py**: Module chỉ huy (Controller) trung tâm của quá trình chuyển đổi.
  - *Hàm chuyen_doi()*: Hàm khởi chạy chính.
  - *Hàm phan_tich_ngu_nghia()*: Duyệt cấu trúc Word và gán nhãn cho từng đoạn (tiêu đề, tác giả, nội dung).
  - *Các hàm _thay_the_*()*: Chèn nội dung Word đã dịch vào file mẫu LaTeX (.tex) theo đúng vị trí.
- **src/xu_ly_bang.py**: Module bóc tách bảng biểu.
  - *Hàm xu_ly_bang()*: Hàm chính chẩn đoán và phân tích dữ liệu bảng trong Word.
  - Chuyển cell matrix trong Word thành cấu trúc bảng LaTeX với lưới (grid) chuẩn sử dụng \hline và |.
- **src/xu_ly_toan.py & src/xu_ly_ole_equation.py**: Hai file đảm nhiệm dịch mọi chuẩn công thức toán học nội tuyến hoặc độc lập sang syntax $$...d:\Word2Latex_Research của LaTeX.
- **src/xu_ly_anh.py**: Chứa thuật toán phân tích điểm ảnh. Hàm cham_diem_anh() sẽ gọi logic tính Entropy và Variance để duyệt hoặc từ chối lưu ảnh.
- **rontend/**: Chứa toàn bộ project React. 
  - src/features/chuyen_doi/TrangChuyenDoi.jsx đảm nhận giao diện upload drag-n-drop file.
  - Thư mục services/api.js giao tiếp HTTP tới backend.

---

##  Hướng Dẫn Sử Dụng (Quick Start)

### Chạy hệ thống bằng 1 click
Tại thư mục gốc, nháy đúp chuột vào file **start.bat**. 
- API Backend sẽ được mở tại: http://localhost:8000/docs
- Giao diện Web App mở tại: http://localhost:5173 (hoặc 3000 tùy cấu hình).

### Quản lý mã nguồn & Cập nhật
Trong quá trình code (Developer Mode):
- Backend chạy uvicorn với tính năng auto-reload. Mọi chỉnh sửa trong thư mục src/ hoặc ackend/ đều được tải lại tự động.
- Frontend dùng ite với tính năng HMR (Hot Module Replacement), sửa file .jsx là trình duyệt tự động cập nhật ngay tức thì mà không cần ấn F5.

### Deploy (Đưa lên Internet)
- Frontend: Build bằng 
pm run build và deploy lên Vercel, Netlify.
- Backend: Chạy qua Gunicorn và deploy lên nền tảng như Railway, Render hoặc AWS EC2. Đừng quên thiết lập file .env chứa token Firebase và Allow CORS cho chính xác.
