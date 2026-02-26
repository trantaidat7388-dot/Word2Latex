// TrangChuyenDoi.jsx - Trang chính cho chức năng chuyển đổi Word sang LaTeX

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  Download,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Zap,
  Clock,
  FileCode,
  Image,
  AlignJustify,
  Eye,
  Copy,
  Upload,
  Trash2,
  Settings
} from 'lucide-react'
import toast from 'react-hot-toast'
import KhuVucKeoTha from './KhuVucKeoTha'
import { NutBam, LoadingXuLy } from '../../components'
import { db, auth } from '../../services/firebaseConfig'
import { addDoc, collection, serverTimestamp } from 'firebase/firestore'
import { chuyenDoiFile, taiFileZip, layDanhSachTemplate, taiLenTemplate, xoaTemplate } from '../../services/api'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TrangChuyenDoi = ({ nguoiDung }) => {
  // Trang chính xử lý upload file và hiển thị tiến trình chuyển đổi
  const [fileChon, setFileChon] = useState(null)
  const [loiValidation, setLoiValidation] = useState(null)
  const [trangThaiXuLy, setTrangThaiXuLy] = useState('cho') // 'cho' | 'dang_xu_ly' | 'hoan_thanh' | 'loi'
  const [isUploading, setIsUploading] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isDone, setIsDone] = useState(false)
  const [error, setError] = useState(null)
  const [tienTrinh, setTienTrinh] = useState(0)
  const [ketQuaChuyenDoi, setKetQuaChuyenDoi] = useState(null)
  const [thongBaoTienTrinh, setThongBaoTienTrinh] = useState('')
  const [loaiTemplate, setLoaiTemplate] = useState('ieee_conference')
  const [texContent, setTexContent] = useState('')
  const [jobId, setJobId] = useState('')
  const [hienThiMaLatex, setHienThiMaLatex] = useState(false)
  const [danhSachTemplate, setDanhSachTemplate] = useState([])
  const [hienThiQuanLyTemplate, setHienThiQuanLyTemplate] = useState(false)
  const [dangTaiTemplate, setDangTaiTemplate] = useState(false)
  const templateInputRef = useRef(null)

  const luuLichSuChuyenDoi = async (user, file, jobIdMoi) => {
    // Lưu một bản ghi lịch sử chuyển đổi vào Firestore
    if (!user?.uid || !file?.name) return
    try {
      await addDoc(collection(db, 'lich_su_chuyen_doi'), {
        uid: user.uid,
        tenFileGoc: file.name,
        thoiGian: serverTimestamp(),
        trangThai: 'Thành công',
        jobId: jobIdMoi || ''
      })
    } catch {
      toast.error('Không thể lưu lịch sử lên Firebase, nhưng file .zip vẫn tải được')
    }
  }

  const xuLyCopyMa = async () => {
    // Copy mã LaTeX vào clipboard
    try {
      if (!texContent) throw new Error('Không có mã để copy')
      await navigator.clipboard.writeText(texContent)
      toast.success('Đã copy mã LaTeX')
    } catch (loi) {
      toast.error(loi.message || 'Không thể copy')
    }
  }

  const xuLyChonFile = (file, loi) => {
    // Xử lý khi người dùng chọn hoặc kéo file vào
    if (loi) {
      setLoiValidation(loi)
      setFileChon(null)
      return
    }
    setFileChon(file)
    setLoiValidation(null)
    setTrangThaiXuLy('cho')
    setKetQuaChuyenDoi(null)
  }

  // Tải danh sách templates khi component mount
  useEffect(() => {
    const taiTemplates = async () => {
      const kq = await layDanhSachTemplate()
      if (kq.thanhCong) setDanhSachTemplate(kq.templates)
    }
    taiTemplates()
  }, [])

  const xuLyTaiLenTemplate = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setDangTaiTemplate(true)
    try {
      const kq = await taiLenTemplate(file)
      if (kq.thanhCong) {
        toast.success(kq.message || 'Đã tải lên template')
        // Reload templates
        const dsKq = await layDanhSachTemplate()
        if (dsKq.thanhCong) setDanhSachTemplate(dsKq.templates)
        setLoaiTemplate(kq.template.id)
      } else {
        toast.error(kq.loiMessage || 'Lỗi tải lên template')
      }
    } catch {
      toast.error('Lỗi tải lên template')
    } finally {
      setDangTaiTemplate(false)
      if (templateInputRef.current) templateInputRef.current.value = ''
    }
  }

  const xuLyXoaTemplate = async (templateId) => {
    const kq = await xoaTemplate(templateId)
    if (kq.thanhCong) {
      toast.success('Đã xóa template')
      if (loaiTemplate === templateId) setLoaiTemplate('ieee_conference')
      const dsKq = await layDanhSachTemplate()
      if (dsKq.thanhCong) setDanhSachTemplate(dsKq.templates)
    } else {
      toast.error(kq.loiMessage || 'Lỗi xóa template')
    }
  }

  const xuLyXoaFile = () => {
    // Xóa file đã chọn và reset trạng thái
    setFileChon(null)
    setLoiValidation(null)
    setTrangThaiXuLy('cho')
    setIsUploading(false)
    setIsProcessing(false)
    setIsDone(false)
    setError(null)
    setTienTrinh(0)
    setKetQuaChuyenDoi(null)
    setTexContent('')
    setJobId('')
    setHienThiMaLatex(false)
  }

  const xuLyChuyenDoi = async () => {
    // Xử lý chuyển đổi file Word sang LaTeX
    if (!fileChon) {
      toast.error('Vui lòng chọn file trước')
      return
    }

    setTrangThaiXuLy('dang_xu_ly')
    setIsUploading(true)
    setIsProcessing(true)
    setIsDone(false)
    setError(null)
    setTienTrinh(0)

    try {
      // Gọi API backend để chuyển đổi
      setThongBaoTienTrinh('Đang tải file lên...')
      setTienTrinh(20)

      const ketQuaAPI = await chuyenDoiFile(fileChon, loaiTemplate)

      if (!ketQuaAPI || !ketQuaAPI.thanhCong) {
        throw new Error(ketQuaAPI?.loiMessage || 'Lỗi khi chuyển đổi')
      }

      setIsUploading(false)
      setThongBaoTienTrinh('Hệ thống đang xử lý cấu trúc LaTeX...')
      setTienTrinh(60)

      await new Promise(resolve => setTimeout(resolve, 500))

      setThongBaoTienTrinh('Hoàn thành!')
      setTienTrinh(100)

      const apiData = ketQuaAPI.data || {}
      const metadata = apiData.metadata || {}
      const ketQua = {
        jobId: apiData.jobId || '',
        tenFileZip: apiData.tenFileZip || '',
        tenFileLatex: apiData.tenFileLatex || '',
        thoiGianXuLy: `${metadata.thoi_gian_xu_ly_giay ?? 0}s`,
        soTrang: metadata.so_trang ?? '—',
        soCongThuc: metadata.so_cong_thuc ?? 0,
        soHinhAnh: metadata.so_hinh_anh ?? 0
      }

      const userHienTai = auth.currentUser || nguoiDung
      const texMoi = apiData.texContent || ''
      setTexContent(texMoi)
      setJobId(apiData.jobId || '')
      if (!texMoi.trim()) {
        toast.error('Không đọc được mã LaTeX. Vui lòng tải file .zip để kiểm tra hoặc restart backend.')
      }
      await luuLichSuChuyenDoi(userHienTai, fileChon, apiData.jobId || '')

      setKetQuaChuyenDoi(ketQua)
      setTrangThaiXuLy('hoan_thanh')
      setIsProcessing(false)
      setIsDone(true)
      toast.success('Chuyển đổi thành công!')

    } catch (loi) {
      setTrangThaiXuLy('loi')
      setIsUploading(false)
      setIsProcessing(false)
      setIsDone(false)
      setError(loi.message || 'Đã xảy ra lỗi khi chuyển đổi')
      toast.error(loi.message || 'Đã xảy ra lỗi khi chuyển đổi')
      console.error(loi)
    }
  }

  const xuLyTaiVe = async () => {
    // Xử lý tải file kết quả ZIP
    try {
      toast.loading('Đang tải xuống...', { id: 'download' })
      const kq = await taiFileZip(jobId || ketQuaChuyenDoi?.jobId, ketQuaChuyenDoi?.tenFileZip || '')
      if (!kq.thanhCong) throw new Error(kq.loiMessage || 'Không thể tải file')
      toast.success('Tải file thành công!', { id: 'download' })
    } catch (loi) {
      toast.error(loi.message || 'Không thể tải file', { id: 'download' })
    }
  }

  const xuLyChuyenDoiMoi = () => {
    // Reset để chuyển đổi file mới
    setFileChon(null)
    setTrangThaiXuLy('cho')
    setIsUploading(false)
    setIsProcessing(false)
    setIsDone(false)
    setError(null)
    setTienTrinh(0)
    setKetQuaChuyenDoi(null)
    setThongBaoTienTrinh('')
    setTexContent('')
    setJobId('')
    setHienThiMaLatex(false)
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
        className="max-w-3xl mx-auto"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Header */}
        <motion.div
          className="text-center mb-8"
          variants={itemVariants}
        >
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-500/20 text-primary-300 text-sm mb-4"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <Sparkles className="w-4 h-4" />
            Hỗ trợ OMML & OLE Equation
          </motion.div>
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">
            Chuyển đổi Word sang LaTeX
          </h1>
          <p className="text-white/60 max-w-xl mx-auto">
            Upload file .docx / .docm và nhận file LaTeX (.tex) chuẩn học thuật
            với đầy đủ công thức toán học, bảng biểu và hình ảnh.
          </p>
        </motion.div>

        {/* Main Content Area */}
        <motion.div variants={itemVariants}>
          <AnimatePresence mode="wait">
            {/* Trạng thái chờ: Hiển thị Dropzone */}
            {trangThaiXuLy === 'cho' && (
              <motion.div
                key="dropzone-area"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                <KhuVucKeoTha
                  onChonFile={xuLyChonFile}
                  fileHienTai={fileChon}
                  onXoaFile={xuLyXoaFile}
                  loiValidation={loiValidation}
                />

                {fileChon && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 space-y-4"
                  >
                    {/* Template selector */}
                    <div className="glass-card p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white/70 text-sm font-medium">Chọn Template LaTeX:</span>
                        <button
                          onClick={() => setHienThiQuanLyTemplate(!hienThiQuanLyTemplate)}
                          className="flex items-center gap-1 text-xs text-primary-400 hover:text-primary-300 transition-colors"
                        >
                          <Settings className="w-3.5 h-3.5" />
                          Quản lý
                        </button>
                      </div>

                      {/* Template buttons */}
                      <div className="flex flex-wrap items-center justify-center gap-2">
                        <button
                          onClick={() => setLoaiTemplate('ieee_conference')}
                          className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all duration-200 text-sm ${loaiTemplate === 'ieee_conference'
                              ? 'bg-primary-500/30 border-primary-500 text-primary-300'
                              : 'bg-white/5 border-white/10 text-white/50 hover:bg-white/10'
                            }`}
                        >
                          <FileCode className="w-4 h-4" />
                          IEEE Conference (2 cột)
                        </button>
                        <button
                          onClick={() => setLoaiTemplate('onecolumn')}
                          className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all duration-200 text-sm ${loaiTemplate === 'onecolumn'
                              ? 'bg-primary-500/30 border-primary-500 text-primary-300'
                              : 'bg-white/5 border-white/10 text-white/50 hover:bg-white/10'
                            }`}
                        >
                          <FileCode className="w-4 h-4" />
                          Article (1 cột)
                        </button>
                        {danhSachTemplate.filter(t => t.loai === 'tuy_chinh').map(t => (
                          <button
                            key={t.id}
                            onClick={() => setLoaiTemplate(t.id)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all duration-200 text-sm ${loaiTemplate === t.id
                                ? 'bg-purple-500/30 border-purple-500 text-purple-300'
                                : 'bg-white/5 border-white/10 text-white/50 hover:bg-white/10'
                              }`}
                          >
                            <FileCode className="w-4 h-4" />
                            {t.ten}
                          </button>
                        ))}
                      </div>

                      {/* Template management panel */}
                      <AnimatePresence>
                        {hienThiQuanLyTemplate && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="border-t border-white/10 pt-3 mt-1 space-y-2">
                              {/* Upload button */}
                              <div className="flex items-center gap-2">
                                <input
                                  ref={templateInputRef}
                                  type="file"
                                  accept=".tex"
                                  onChange={xuLyTaiLenTemplate}
                                  className="hidden"
                                  id="template-upload"
                                />
                                <button
                                  onClick={() => templateInputRef.current?.click()}
                                  disabled={dangTaiTemplate}
                                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-500/20 border border-primary-500/30 text-primary-300 text-xs hover:bg-primary-500/30 transition-all disabled:opacity-50"
                                >
                                  <Upload className="w-3.5 h-3.5" />
                                  {dangTaiTemplate ? 'Đang tải...' : 'Tải lên template .tex'}
                                </button>
                                <span className="text-white/40 text-xs">Yêu cầu: file .tex có \\documentclass</span>
                              </div>

                              {/* Custom template list */}
                              {danhSachTemplate.filter(t => t.loai === 'tuy_chinh').length > 0 && (
                                <div className="space-y-1">
                                  <p className="text-white/40 text-xs">Template tùy chỉnh:</p>
                                  {danhSachTemplate.filter(t => t.loai === 'tuy_chinh').map(t => (
                                    <div key={t.id} className="flex items-center justify-between px-3 py-1.5 rounded bg-white/5">
                                      <span className="text-white/70 text-xs">{t.ten}.tex ({(t.kichThuoc / 1024).toFixed(1)}KB)</span>
                                      <button
                                        onClick={() => xuLyXoaTemplate(t.id)}
                                        className="text-red-400/60 hover:text-red-400 transition-colors"
                                      >
                                        <Trash2 className="w-3.5 h-3.5" />
                                      </button>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    <div className="flex justify-center">
                      <NutBam
                        onClick={xuLyChuyenDoi}
                        icon={Zap}
                        kichThuoc="lg"
                      >
                        Bắt đầu chuyển đổi
                      </NutBam>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            )}

            {/* Trạng thái đang xử lý */}
            {trangThaiXuLy === 'dang_xu_ly' && (
              <motion.div
                key="processing"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="flex justify-center"
              >
                <LoadingXuLy
                  tienTrinh={tienTrinh}
                  thongBao={thongBaoTienTrinh || 'Đang xử lý...'}
                  chiTiet={fileChon?.name}
                />
              </motion.div>
            )}

            {/* Trạng thái hoàn thành */}
            {trangThaiXuLy === 'hoan_thanh' && ketQuaChuyenDoi && (
              <motion.div
                key="completed"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="glass-card p-8"
              >
                {/* Success Icon */}
                <div className="text-center mb-6">
                  <motion.div
                    className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-500/20 mb-4"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', delay: 0.2 }}
                  >
                    <CheckCircle2 className="w-10 h-10 text-green-400" />
                  </motion.div>
                  <h2 className="text-2xl font-bold text-white mb-2">
                    Chuyển đổi thành công!
                  </h2>
                  <p className="text-white/60">
                    File LaTeX đã sẵn sàng để tải về
                  </p>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-4 gap-3 mb-6">
                  <div className="text-center p-4 rounded-xl bg-white/5">
                    <FileCode className="w-6 h-6 text-primary-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{ketQuaChuyenDoi.soTrang}</p>
                    <p className="text-white/50 text-sm">Trang</p>
                  </div>
                  <div className="text-center p-4 rounded-xl bg-white/5">
                    <FileText className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{ketQuaChuyenDoi.soCongThuc}</p>
                    <p className="text-white/50 text-sm">Công thức</p>
                  </div>
                  <div className="text-center p-4 rounded-xl bg-white/5">
                    <Image className="w-6 h-6 text-green-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{ketQuaChuyenDoi.soHinhAnh}</p>
                    <p className="text-white/50 text-sm">Hình ảnh</p>
                  </div>
                  <div className="text-center p-4 rounded-xl bg-white/5">
                    <Clock className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{ketQuaChuyenDoi.thoiGianXuLy}</p>
                    <p className="text-white/50 text-sm">Thời gian</p>
                  </div>
                </div>

                {/* File info */}
                <div className="bg-white/5 rounded-xl p-4 mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-primary-500/20 flex items-center justify-center">
                      <FileText className="w-6 h-6 text-primary-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-white font-medium">{ketQuaChuyenDoi.tenFileZip || 'output.zip'}</p>
                      <p className="text-white/50 text-sm">
                        Bao gồm: {ketQuaChuyenDoi.tenFileLatex || 'output.tex'}, file PDF, images/
                      </p>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex flex-col sm:flex-row gap-3">
                  <NutBam
                    onClick={xuLyTaiVe}
                    icon={Download}
                    className="flex-1"
                    kichThuoc="lg"
                  >
                    Tải xuống (.zip)
                  </NutBam>
                  <NutBam
                    onClick={() => setHienThiMaLatex(true)}
                    bienThe="secondary"
                    icon={Eye}
                    className="flex-1"
                    kichThuoc="lg"
                  >
                    Xem mã LaTeX
                  </NutBam>
                  <NutBam
                    onClick={xuLyChuyenDoiMoi}
                    bienThe="secondary"
                    icon={RefreshCw}
                    className="flex-1"
                    kichThuoc="lg"
                  >
                    Chuyển đổi file khác
                  </NutBam>
                </div>

                <AnimatePresence>
                  {hienThiMaLatex && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="fixed inset-0 z-50 flex items-center justify-center px-4"
                    >
                      <div
                        className="absolute inset-0 bg-black/60"
                        onClick={() => setHienThiMaLatex(false)}
                      />
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 10 }}
                        className="relative w-full max-w-3xl glass-card p-0 overflow-hidden"
                      >
                        <div className="flex items-center justify-between px-4 py-3 bg-white/5 border-b border-white/10">
                          <span className="text-white/80 text-sm font-medium">Mã LaTeX</span>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={xuLyCopyMa}
                              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-500/20 border border-primary-500/30 text-primary-300 text-xs hover:bg-primary-500/30 transition-all"
                            >
                              <Copy className="w-3.5 h-3.5" />
                              Copy Code
                            </button>
                            <button
                              onClick={() => setHienThiMaLatex(false)}
                              className="text-white/50 hover:text-white/80 transition-colors text-sm"
                            >
                              Đóng
                            </button>
                          </div>
                        </div>
                        <pre className="p-4 text-green-300 font-mono text-xs overflow-auto max-h-[70vh] whitespace-pre-wrap">
                          <code>{texContent || 'Không có nội dung LaTeX'}</code>
                        </pre>
                      </motion.div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )}

            {/* Trạng thái lỗi */}
            {trangThaiXuLy === 'loi' && (
              <motion.div
                key="error"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="glass-card p-8 text-center"
              >
                <motion.div
                  className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-red-500/20 mb-4"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                >
                  <AlertCircle className="w-10 h-10 text-red-400" />
                </motion.div>
                <h2 className="text-2xl font-bold text-white mb-2">
                  Đã xảy ra lỗi
                </h2>
                <p className="text-white/60 mb-6">
                  Không thể chuyển đổi file. Vui lòng thử lại hoặc kiểm tra định dạng file.
                </p>
                <NutBam
                  onClick={xuLyChuyenDoiMoi}
                  icon={RefreshCw}
                >
                  Thử lại
                </NutBam>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Features */}
        <motion.div
          className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4"
          variants={itemVariants}
        >
          {[
            { icon: FileText, tieuDe: 'Công thức OMML', moTa: 'Chuyển đổi chính xác công thức Word' },
            { icon: Zap, tieuDe: 'OLE Equation', moTa: 'Hỗ trợ Equation Editor 3.0' },
            { icon: CheckCircle2, tieuDe: 'Chuẩn học thuật', moTa: 'Output theo chuẩn IEEE/ACM' },
          ].map((feature, index) => (
            <motion.div
              key={index}
              className="glass-card-hover p-4 text-center"
              whileHover={{ y: -5 }}
            >
              <feature.icon className="w-8 h-8 text-primary-400 mx-auto mb-2" />
              <h3 className="text-white font-medium mb-1">{feature.tieuDe}</h3>
              <p className="text-white/50 text-sm">{feature.moTa}</p>
            </motion.div>
          ))}
        </motion.div>
      </motion.div>
    </div>
  )
}

export default TrangChuyenDoi
