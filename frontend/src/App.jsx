// App.jsx - Component gốc của ứng dụng Word2LaTeX

import { Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { theoDoiTrangThaiXacThuc } from './services/firebaseConfig'
import { ThanhDieuHuong, LoadingManHinh } from './components'
import { TrangDangNhap } from './features/xac_thuc'
import { TrangChuyenDoi } from './features/chuyen_doi'
import { TrangLichSu } from './features/lich_su'

const App = () => {
  // Component điều hướng chính của ứng dụng
  const [nguoiDung, setNguoiDung] = useState(null)
  const [dangTai, setDangTai] = useState(true)

  useEffect(() => {
    // Theo dõi trạng thái xác thực khi app khởi động
    const huyTheoDoiXacThuc = theoDoiTrangThaiXacThuc((user) => {
      setNguoiDung(user)
      setDangTai(false)
    })

    return () => huyTheoDoiXacThuc()
  }, [])

  if (dangTai) {
    // Hiển thị loading khi đang kiểm tra trạng thái xác thực
    return <LoadingManHinh thongBao="Đang khởi động..." />
  }

  return (
    <Routes>
      {/* Route công khai - Đăng nhập */}
      <Route 
        path="/dang-nhap" 
        element={nguoiDung ? <Navigate to="/chuyen-doi" replace /> : <TrangDangNhap />} 
      />
      
      {/* Routes yêu cầu đăng nhập */}
      <Route element={<LayoutChung nguoiDung={nguoiDung} />}>
        <Route 
          path="/chuyen-doi" 
          element={
            nguoiDung ? (
              <TrangChuyenDoi nguoiDung={nguoiDung} />
            ) : (
              <Navigate to="/dang-nhap" replace />
            )
          } 
        />
        <Route 
          path="/lich-su" 
          element={
            nguoiDung ? (
              <TrangLichSu nguoiDung={nguoiDung} />
            ) : (
              <Navigate to="/dang-nhap" replace />
            )
          } 
        />
      </Route>
      
      {/* Redirect mặc định */}
      <Route 
        path="*" 
        element={<Navigate to={nguoiDung ? "/chuyen-doi" : "/dang-nhap"} replace />} 
      />
    </Routes>
  )
}

// Layout chung cho các trang có thanh điều hướng
const LayoutChung = ({ nguoiDung }) => {
  // Layout wrapper bao gồm navigation và nội dung chính
  if (!nguoiDung) {
    return <Navigate to="/dang-nhap" replace />
  }

  return (
    <>
      <ThanhDieuHuong nguoiDung={nguoiDung} />
      <Outlet />
    </>
  )
}

export default App
