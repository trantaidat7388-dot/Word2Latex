// BangLichSu.jsx - Bảng hiển thị lịch sử chuyển đổi từ Firestore

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  FileText, 
  Download, 
  Trash2, 
  CheckCircle2, 
  XCircle, 
  Clock,
  MoreVertical
} from 'lucide-react'
import toast from 'react-hot-toast'
import { xoaLichSuChuyenDoi } from '../../services/firebaseConfig'
import { taiFileZip, taiFile } from '../../services/api'

const BangLichSu = ({ danhSach, dangTai, onCapNhat }) => {
  // Component bảng hiển thị lịch sử với các action xóa và tải
  const [menuMoId, setMenuMoId] = useState(null)
  const [dangXoa, setDangXoa] = useState(null)

  const layIconTrangThai = (trangThai) => {
    // Trả về icon và màu tương ứng với trạng thái
    switch (trangThai) {
      case 'Thành công':
        return { icon: CheckCircle2, mau: 'text-green-400', bg: 'bg-green-500/20' }
      case 'Thất bại':
        return { icon: XCircle, mau: 'text-red-400', bg: 'bg-red-500/20' }
      case 'Đang xử lý':
      default:
        return { icon: Clock, mau: 'text-yellow-400', bg: 'bg-yellow-500/20' }
    }
  }

  const dinhDangThoiGian = (date) => {
    // Định dạng thời gian thành chuỗi dễ đọc
    if (!date) return 'N/A'
    
    const now = new Date()
    const diff = now - date
    const phut = Math.floor(diff / 60000)
    const gio = Math.floor(diff / 3600000)
    const ngay = Math.floor(diff / 86400000)

    if (phut < 1) return 'Vừa xong'
    if (phut < 60) return `${phut} phút trước`
    if (gio < 24) return `${gio} giờ trước`
    if (ngay < 7) return `${ngay} ngày trước`

    return date.toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const xuLyXoa = async (docId, tenFile) => {
    // Xử lý xóa một bản ghi lịch sử
    setDangXoa(docId)
    try {
      const ketQua = await xoaLichSuChuyenDoi(docId)
      if (ketQua.thanhCong) {
        toast.success(`Đã xóa "${tenFile}"`)
        onCapNhat?.()
      } else {
        toast.error(ketQua.loiMessage)
      }
    } catch (loi) {
      toast.error('Không thể xóa')
    } finally {
      setDangXoa(null)
      setMenuMoId(null)
    }
  }

  const xuLyTaiVe = async (item) => {
    // Xử lý tải file kết quả từ lịch sử
    try {
      if (item?.jobId) {
        toast.loading('Đang tải file .zip...', { id: 'tai-zip' })
        const kq = await taiFileZip(item.jobId)
        if (!kq.thanhCong) throw new Error(kq.loiMessage || 'Không thể tải file .zip')
        toast.success('Tải file thành công!', { id: 'tai-zip' })
        return
      }

      if (item?.duongDanTaiVe) {
        toast.loading('Đang tải file...', { id: 'tai-zip' })
        const kq = await taiFile(item.duongDanTaiVe, `${item.tenFileGoc || 'output'}.zip`)
        if (!kq.thanhCong) throw new Error(kq.loiMessage || 'Không thể tải file')
        toast.success('Tải file thành công!', { id: 'tai-zip' })
        return
      }

      toast.error('Link tải không khả dụng')
    } catch (loi) {
      toast.error(loi.message || 'Không thể tải file', { id: 'tai-zip' })
    } finally {
      setMenuMoId(null)
    }
  }

  // Loading state
  if (dangTai) {
    return (
      <div className="glass-card p-8">
        <div className="flex flex-col items-center justify-center py-8">
          <div className="w-10 h-10 border-3 border-primary-500 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-white/60">Đang tải lịch sử...</p>
        </div>
      </div>
    )
  }

  // Empty state
  if (!danhSach || danhSach.length === 0) {
    return (
      <motion.div 
        className="glass-card p-8 text-center"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-4">
          <FileText className="w-10 h-10 text-white/30" />
        </div>
        <h3 className="text-xl font-medium text-white mb-2">
          Chưa có lịch sử
        </h3>
        <p className="text-white/50">
          Các file bạn chuyển đổi sẽ xuất hiện ở đây
        </p>
      </motion.div>
    )
  }

  return (
    <div className="glass-card overflow-hidden">
      {/* Header */}
      <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-4 bg-white/5 border-b border-white/10">
        <div className="col-span-5 text-white/60 text-sm font-medium">
          Tên file
        </div>
        <div className="col-span-2 text-white/60 text-sm font-medium">
          Trạng thái
        </div>
        <div className="col-span-3 text-white/60 text-sm font-medium">
          Thời gian
        </div>
        <div className="col-span-2 text-white/60 text-sm font-medium text-right">
          Thao tác
        </div>
      </div>

      {/* Rows */}
      <div className="divide-y divide-white/10">
        <AnimatePresence>
          {danhSach.map((item, index) => {
            const { icon: StatusIcon, mau, bg } = layIconTrangThai(item.trangThai)
            const coTheTai = item.trangThai === 'Thành công' && (item.jobId || item.duongDanTaiVe)

            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20, height: 0 }}
                transition={{ delay: index * 0.05 }}
                className="grid grid-cols-1 md:grid-cols-12 gap-4 px-6 py-4 hover:bg-white/5 transition-colors items-center"
              >
                {/* File name */}
                <div className="md:col-span-5 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-5 h-5 text-primary-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-white font-medium truncate">
                      {item.tenFileGoc}
                    </p>
                    <p className="text-white/40 text-xs md:hidden">
                      {dinhDangThoiGian(item.thoiGian)}
                    </p>
                  </div>
                </div>

                {/* Status */}
                <div className="md:col-span-2">
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${bg} ${mau}`}>
                    <StatusIcon className="w-3.5 h-3.5" />
                    {item.trangThai}
                  </span>
                </div>

                {/* Time */}
                <div className="hidden md:block md:col-span-3 text-white/60 text-sm">
                  {dinhDangThoiGian(item.thoiGian)}
                </div>

                {/* Actions */}
                <div className="md:col-span-2 flex items-center justify-end gap-2">
                  {coTheTai && (
                    <motion.button
                      onClick={() => xuLyTaiVe(item)}
                      className="p-2 rounded-xl text-primary-400 hover:bg-primary-500/20 transition-colors"
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      title="Tải xuống"
                    >
                      <Download className="w-5 h-5" />
                    </motion.button>
                  )}

                  {/* More menu */}
                  <div className="relative">
                    <motion.button
                      onClick={() => setMenuMoId(menuMoId === item.id ? null : item.id)}
                      className="p-2 rounded-xl text-white/50 hover:text-white hover:bg-white/10 transition-colors"
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                    >
                      <MoreVertical className="w-5 h-5" />
                    </motion.button>

                    <AnimatePresence>
                      {menuMoId === item.id && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.95, y: 10 }}
                          animate={{ opacity: 1, scale: 1, y: 0 }}
                          exit={{ opacity: 0, scale: 0.95, y: 10 }}
                          className="absolute right-0 mt-2 w-44 glass-card py-2 shadow-xl z-10"
                        >
                          {coTheTai && (
                            <button
                              onClick={() => xuLyTaiVe(item)}
                              className="w-full flex items-center gap-2 px-4 py-2 text-sm text-white/80 hover:bg-white/10 transition-colors"
                            >
                              <Download className="w-4 h-4" />
                              Tải xuống
                            </button>
                          )}
                          <button
                            onClick={() => xuLyXoa(item.id, item.tenFileGoc)}
                            disabled={dangXoa === item.id}
                            className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50"
                          >
                            {dangXoa === item.id ? (
                              <div className="w-4 h-4 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
                            ) : (
                              <Trash2 className="w-4 h-4" />
                            )}
                            Xóa khỏi lịch sử
                          </button>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>

      {/* Click outside to close menu */}
      {menuMoId && (
        <div 
          className="fixed inset-0 z-[5]" 
          onClick={() => setMenuMoId(null)} 
        />
      )}
    </div>
  )
}

export default BangLichSu
