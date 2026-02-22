// TrangLichSu.jsx - Trang hiển thị lịch sử chuyển đổi

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { 
  History, 
  RefreshCw, 
  Search,
  Filter,
  Calendar,
  Trash2
} from 'lucide-react'
import toast from 'react-hot-toast'
import BangLichSu from './BangLichSu'
import { NutBam } from '../../components'
import { layLichSuChuyenDoi } from '../../services/firebaseConfig'

const TrangLichSu = ({ nguoiDung }) => {
  // Trang hiển thị danh sách lịch sử chuyển đổi của người dùng
  const [danhSachLichSu, setDanhSachLichSu] = useState([])
  const [danhSachLoc, setDanhSachLoc] = useState([])
  const [dangTai, setDangTai] = useState(true)
  const [tuKhoaTimKiem, setTuKhoaTimKiem] = useState('')
  const [boLocTrangThai, setBoLocTrangThai] = useState('tat_ca')

  const taiLichSu = useCallback(async () => {
    // Tải danh sách lịch sử từ Firestore
    setDangTai(true)
    try {
      const ketQua = await layLichSuChuyenDoi(nguoiDung.uid)
      if (ketQua.thanhCong) {
        setDanhSachLichSu(ketQua.danhSach)
        setDanhSachLoc(ketQua.danhSach)
      } else {
        toast.error(ketQua.loiMessage || 'Không thể tải lịch sử')
      }
    } catch (loi) {
      toast.error('Đã xảy ra lỗi khi tải dữ liệu')
    } finally {
      setDangTai(false)
    }
  }, [nguoiDung.uid])

  useEffect(() => {
    // Tải lịch sử khi component mount
    taiLichSu()
  }, [taiLichSu])

  useEffect(() => {
    // Lọc danh sách theo từ khóa và trạng thái
    let ketQua = [...danhSachLichSu]

    // Lọc theo từ khóa
    if (tuKhoaTimKiem.trim()) {
      const tuKhoa = tuKhoaTimKiem.toLowerCase()
      ketQua = ketQua.filter(item => 
        item.tenFileGoc.toLowerCase().includes(tuKhoa)
      )
    }

    // Lọc theo trạng thái
    if (boLocTrangThai !== 'tat_ca') {
      ketQua = ketQua.filter(item => item.trangThai === boLocTrangThai)
    }

    setDanhSachLoc(ketQua)
  }, [tuKhoaTimKiem, boLocTrangThai, danhSachLichSu])

  const thongKe = {
    tongSo: danhSachLichSu.length,
    thanhCong: danhSachLichSu.filter(i => i.trangThai === 'Thành công').length,
    thatBai: danhSachLichSu.filter(i => i.trangThai === 'Thất bại').length,
    dangXuLy: danhSachLichSu.filter(i => i.trangThai === 'Đang xử lý').length,
  }

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { type: 'spring', stiffness: 100 }
    }
  }

  return (
    <div className="min-h-screen bg-gradient-animated pt-20 pb-12 px-4">
      <motion.div 
        className="max-w-5xl mx-auto"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Header */}
        <motion.div 
          className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8"
          variants={itemVariants}
        >
          <div>
            <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
              <History className="w-8 h-8 text-primary-400" />
              Lịch sử chuyển đổi
            </h1>
            <p className="text-white/60">
              Quản lý và tải lại các file đã chuyển đổi
            </p>
          </div>
          <NutBam
            onClick={taiLichSu}
            bienThe="secondary"
            icon={RefreshCw}
            dangTai={dangTai}
          >
            Làm mới
          </NutBam>
        </motion.div>

        {/* Stats */}
        <motion.div 
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8"
          variants={itemVariants}
        >
          {[
            { nhan: 'Tổng số', giaTri: thongKe.tongSo, mau: 'text-white', bg: 'bg-white/10' },
            { nhan: 'Thành công', giaTri: thongKe.thanhCong, mau: 'text-green-400', bg: 'bg-green-500/10' },
            { nhan: 'Thất bại', giaTri: thongKe.thatBai, mau: 'text-red-400', bg: 'bg-red-500/10' },
            { nhan: 'Đang xử lý', giaTri: thongKe.dangXuLy, mau: 'text-yellow-400', bg: 'bg-yellow-500/10' },
          ].map((stat, index) => (
            <motion.div
              key={index}
              className={`glass-card p-4 ${stat.bg}`}
              whileHover={{ scale: 1.02 }}
            >
              <p className={`text-3xl font-bold ${stat.mau}`}>
                {stat.giaTri}
              </p>
              <p className="text-white/50 text-sm">{stat.nhan}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* Filters */}
        <motion.div 
          className="flex flex-col sm:flex-row gap-4 mb-6"
          variants={itemVariants}
        >
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
            <input
              id="search-input"
              name="search"
              type="text"
              placeholder="Tìm kiếm theo tên file..."
              value={tuKhoaTimKiem}
              onChange={(e) => setTuKhoaTimKiem(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 pl-12 
                         text-white placeholder-white/40 focus:outline-none focus:border-primary-500/50 
                         focus:bg-white/10 transition-all duration-300"
            />
          </div>

          {/* Status filter */}
          <div className="relative">
            <Filter className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
            <select
              id="status-filter"
              name="statusFilter"
              value={boLocTrangThai}
              onChange={(e) => setBoLocTrangThai(e.target.value)}
              className="appearance-none bg-white/5 border border-white/10 rounded-xl px-4 py-3 pl-12 pr-10
                         text-white focus:outline-none focus:border-primary-500/50 
                         focus:bg-white/10 transition-all duration-300 cursor-pointer min-w-[160px]"
            >
              <option value="tat_ca" className="bg-slate-800">Tất cả</option>
              <option value="Thành công" className="bg-slate-800">Thành công</option>
              <option value="Thất bại" className="bg-slate-800">Thất bại</option>
              <option value="Đang xử lý" className="bg-slate-800">Đang xử lý</option>
            </select>
          </div>
        </motion.div>

        {/* Results info */}
        {!dangTai && danhSachLoc.length !== danhSachLichSu.length && (
          <motion.p 
            className="text-white/50 text-sm mb-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            Hiển thị {danhSachLoc.length} / {danhSachLichSu.length} kết quả
          </motion.p>
        )}

        {/* Table */}
        <motion.div variants={itemVariants}>
          <BangLichSu 
            danhSach={danhSachLoc} 
            dangTai={dangTai}
            onCapNhat={taiLichSu}
          />
        </motion.div>
      </motion.div>
    </div>
  )
}

export default TrangLichSu
