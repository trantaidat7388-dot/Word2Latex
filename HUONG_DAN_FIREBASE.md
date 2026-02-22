# Hướng dẫn lấy Firebase API Key

## Bước 1: Truy cập Firebase Console
1. Mở trình duyệt và truy cập: https://console.firebase.google.com/
2. Đăng nhập bằng tài khoản Google

## Bước 2: Tạo hoặc chọn Project
1. Nhấn **"Add project"** (hoặc chọn project có sẵn)
2. Đặt tên project, ví dụ: "Word2LaTeX"
3. Tắt Google Analytics (không bắt buộc)
4. Nhấn **"Create project"**

## Bước 3: Thêm Web App
1. Trong Firebase Console, nhấn biểu tượng **Web (</>)** 
2. Đặt tên app: "Word2LaTeX Frontend"
3. **KHÔNG** check "Also set up Firebase Hosting"
4. Nhấn **"Register app"**

## Bước 4: Copy Firebase Config
Firebase sẽ hiển thị code config như này:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  authDomain: "word2latex-xxxxx.firebaseapp.com",
  projectId: "word2latex-xxxxx",
  storageBucket: "word2latex-xxxxx.firebasestorage.app",
  messagingSenderId: "123456789012",
  appId: "1:123456789012:web:xxxxxxxxxxxxx"
};
```

## Bước 5: Tạo file .env
1. Copy file `.env.example` thành `.env`:
   ```bash
   cp frontend/.env.example frontend/.env
   ```

2. Mở file `frontend/.env` và điền thông tin:
   ```
   VITE_FIREBASE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   VITE_FIREBASE_AUTH_DOMAIN=word2latex-xxxxx.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=word2latex-xxxxx
   VITE_FIREBASE_STORAGE_BUCKET=word2latex-xxxxx.firebasestorage.app
   VITE_FIREBASE_MESSAGING_SENDER_ID=123456789012
   VITE_FIREBASE_APP_ID=1:123456789012:web:xxxxxxxxxxxxx
   ```

## Bước 6: Bật Authentication
1. Trong Firebase Console, vào **"Authentication"** → **"Get started"**
2. Chọn tab **"Sign-in method"**
3. Bật **Email/Password**: 
   - Nhấn "Email/Password" → Enable → Save
4. Bật **Google Sign-In**:
   - Nhấn "Google" → Enable 
   - Chọn email support → Save

## Bước 7: Tạo Firestore Database
1. Vào **"Firestore Database"** → **"Create database"**
2. Chọn **"Start in test mode"** (cho development)
3. Chọn location gần nhất (ví dụ: asia-southeast1)
4. Nhấn **"Enable"**

## Bước 8: Cấu hình Firestore Rules (trong test mode)
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if request.time < timestamp.date(2026, 6, 1);
    }
  }
}
```

## Bước 9: Restart Frontend
```bash
# Dừng Vite dev server (Ctrl+C)
# Chạy lại
npm run dev
```

## Lưu ý bảo mật
- **KHÔNG** commit file `.env` lên Git
- File `.gitignore` đã chứa `.env` để tránh lộ credentials
- Với production, chuyển Firestore sang Production mode và cấu hình rules nghiêm ngặt hơn
