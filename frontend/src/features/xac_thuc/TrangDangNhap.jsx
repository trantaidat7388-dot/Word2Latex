// TrangDangNhap.jsx - Trang đăng nhập với giao diện Glassmorphism

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  FileText, 
  Mail, 
  Lock, 
  Eye, 
  EyeOff, 
  ArrowRight, 
  Sparkles,
  Github,
  Loader2
} from 'lucide-react'
import toast from 'react-hot-toast'
import { 
  dangNhapVoiGoogle, 
  dangNhapVoiEmail, 
  dangKyVoiEmail 
} from '../../services/firebaseConfig'

const TrangDangNhap = () => {
  // Component trang đăng nhập/đăng ký với hiệu ứng kính mờ và animation
  const navigate = useNavigate()
  const [cheDoForm, setCheDoForm] = useState('dangNhap') // 'dangNhap' | 'dangKy'
  const [hienMatKhau, setHienMatKhau] = useState(false)
  const [dangXuLy, setDangXuLy] = useState(false)
  const [formData, setFormData] = useState({
    email: '',
    matKhau: '',
    xacNhanMatKhau: ''
  })

  const xuLyThayDoiInput = (e) => {
    // Cập nhật giá trị input vào state
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const xuLyDangNhapGoogle = async () => {
    // Xử lý đăng nhập bằng Google
    setDangXuLy(true)
    try {
      const ketQua = await dangNhapVoiGoogle()
      if (ketQua.thanhCong) {
        toast.success(`Chào mừng ${ketQua.nguoiDung.displayName || 'bạn'}!`)
        navigate('/chuyen-doi')
      } else {
        const msg = ketQua.loiMessage || 'Đăng nhập thất bại'
        if (msg.toLowerCase().includes('bị hủy')) {
          toast.error('Đăng nhập đã bị hủy')
        } else {
          toast.error(msg)
        }
      }
    } catch (loi) {
      const maLoi = loi?.code || ''
      if (maLoi === 'auth/popup-closed-by-user' || maLoi === 'auth/cancelled-popup-request') {
        toast.error('Đăng nhập đã bị hủy')
        return
      }
      toast.error('Không thể kết nối đến Google')
    } finally {
      setDangXuLy(false)
    }
  }

  const xuLyGuiForm = async (e) => {
    // Xử lý submit form đăng nhập hoặc đăng ký
    e.preventDefault()
    
    if (!formData.email || !formData.matKhau) {
      toast.error('Vui lòng điền đầy đủ thông tin')
      return
    }

    if (cheDoForm === 'dangKy' && formData.matKhau !== formData.xacNhanMatKhau) {
      toast.error('Mật khẩu xác nhận không khớp')
      return
    }

    setDangXuLy(true)
    try {
      let ketQua
      if (cheDoForm === 'dangNhap') {
        ketQua = await dangNhapVoiEmail(formData.email, formData.matKhau)
      } else {
        ketQua = await dangKyVoiEmail(formData.email, formData.matKhau)
      }

      if (ketQua.thanhCong) {
        toast.success(cheDoForm === 'dangNhap' ? 'Đăng nhập thành công!' : 'Đăng ký thành công!')
        navigate('/chuyen-doi')
      } else {
        toast.error(ketQua.loiMessage)
      }
    } catch (loi) {
      toast.error('Đã xảy ra lỗi không mong muốn')
    } finally {
      setDangXuLy(false)
    }
  }

  const chuyenCheDo = () => {
    // Chuyển đổi giữa form đăng nhập và đăng ký
    setCheDoForm(prev => prev === 'dangNhap' ? 'dangKy' : 'dangNhap')
    setFormData({ email: '', matKhau: '', xacNhanMatKhau: '' })
  }

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1, delayChildren: 0.2 }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { type: 'spring', stiffness: 100, damping: 12 }
    }
  }

  const formVariants = {
    hidden: { opacity: 0, x: 20 },
    visible: { 
      opacity: 1, 
      x: 0,
      transition: { type: 'spring', stiffness: 100, damping: 15 }
    },
    exit: { 
      opacity: 0, 
      x: -20,
      transition: { duration: 0.2 }
    }
  }

  return (
    <div className="min-h-screen bg-gradient-animated flex items-center justify-center p-4 relative overflow-hidden">
      {/* Hiệu ứng nền - Floating orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          className="absolute w-96 h-96 bg-primary-500/20 rounded-full blur-3xl"
          animate={{
            x: [0, 100, 0],
            y: [0, -50, 0],
          }}
          transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
          style={{ top: '10%', left: '10%' }}
        />
        <motion.div
          className="absolute w-80 h-80 bg-purple-500/15 rounded-full blur-3xl"
          animate={{
            x: [0, -80, 0],
            y: [0, 80, 0],
          }}
          transition={{ duration: 15, repeat: Infinity, ease: 'easeInOut' }}
          style={{ bottom: '10%', right: '15%' }}
        />
        <motion.div
          className="absolute w-64 h-64 bg-blue-500/10 rounded-full blur-3xl"
          animate={{
            x: [0, 50, 0],
            y: [0, -30, 0],
          }}
          transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut' }}
          style={{ top: '50%', right: '5%' }}
        />
      </div>

      {/* Container chính */}
      <motion.div
        className="w-full max-w-md relative z-10"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Logo và tiêu đề */}
        <motion.div 
          className="text-center mb-8"
          variants={itemVariants}
        >
          <motion.div
            className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 mb-4 shadow-lg shadow-primary-500/30"
            whileHover={{ scale: 1.05, rotate: 5 }}
            whileTap={{ scale: 0.95 }}
          >
            <FileText className="w-10 h-10 text-white" />
          </motion.div>
          <h1 className="text-3xl font-bold text-white mb-2">
            Word2LaTeX
          </h1>
          <p className="text-white/60 text-sm">
            Chuyển đổi Word sang LaTeX chuẩn học thuật
          </p>
        </motion.div>

        {/* Card Glassmorphism */}
        <motion.div
          className="glass-card p-8 shadow-2xl"
          variants={itemVariants}
        >
          {/* Tab chuyển đổi */}
          <div className="flex bg-white/5 rounded-xl p-1 mb-6">
            <button
              onClick={() => setCheDoForm('dangNhap')}
              className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-300 ${
                cheDoForm === 'dangNhap'
                  ? 'bg-primary-600 text-white shadow-lg'
                  : 'text-white/60 hover:text-white'
              }`}
            >
              Đăng nhập
            </button>
            <button
              onClick={() => setCheDoForm('dangKy')}
              className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-300 ${
                cheDoForm === 'dangKy'
                  ? 'bg-primary-600 text-white shadow-lg'
                  : 'text-white/60 hover:text-white'
              }`}
            >
              Đăng ký
            </button>
          </div>

          {/* Nút đăng nhập Google */}
          <motion.button
            onClick={xuLyDangNhapGoogle}
            disabled={dangXuLy}
            className="w-full flex items-center justify-center gap-3 bg-white/10 hover:bg-white/15 border border-white/20 hover:border-white/30 rounded-xl py-3.5 text-white font-medium transition-all duration-300 mb-6 group"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {dangXuLy ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                <span>Tiếp tục với Google</span>
                <Sparkles className="w-4 h-4 text-yellow-400 opacity-0 group-hover:opacity-100 transition-opacity" />
              </>
            )}
          </motion.button>

          {/* Divider */}
          <div className="flex items-center gap-4 mb-6">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-white/40 text-sm">hoặc</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>

          {/* Form đăng nhập/đăng ký */}
          <AnimatePresence mode="wait">
            <motion.form
              key={cheDoForm}
              onSubmit={xuLyGuiForm}
              variants={formVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="space-y-4"
            >
              {/* Email */}
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={xuLyThayDoiInput}
                  placeholder="Email của bạn"
                  className="input-glass pl-12"
                  disabled={dangXuLy}
                />
              </div>

              {/* Mật khẩu */}
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                <input
                  type={hienMatKhau ? 'text' : 'password'}
                  name="matKhau"
                  value={formData.matKhau}
                  onChange={xuLyThayDoiInput}
                  placeholder="Mật khẩu"
                  className="input-glass pl-12 pr-12"
                  disabled={dangXuLy}
                />
                <button
                  type="button"
                  onClick={() => setHienMatKhau(!hienMatKhau)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/60 transition-colors"
                >
                  {hienMatKhau ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>

              {/* Xác nhận mật khẩu (chỉ hiển thị khi đăng ký) */}
              {cheDoForm === 'dangKy' && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="relative"
                >
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                  <input
                    type={hienMatKhau ? 'text' : 'password'}
                    name="xacNhanMatKhau"
                    value={formData.xacNhanMatKhau}
                    onChange={xuLyThayDoiInput}
                    placeholder="Xác nhận mật khẩu"
                    className="input-glass pl-12"
                    disabled={dangXuLy}
                  />
                </motion.div>
              )}

              {/* Quên mật khẩu (chỉ hiển thị khi đăng nhập) */}
              {cheDoForm === 'dangNhap' && (
                <div className="text-right">
                  <button
                    type="button"
                    className="text-sm text-primary-400 hover:text-primary-300 transition-colors"
                  >
                    Quên mật khẩu?
                  </button>
                </div>
              )}

              {/* Nút submit */}
              <motion.button
                type="submit"
                disabled={dangXuLy}
                className="btn-primary w-full flex items-center justify-center gap-2"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {dangXuLy ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <>
                    <span>{cheDoForm === 'dangNhap' ? 'Đăng nhập' : 'Tạo tài khoản'}</span>
                    <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </motion.button>
            </motion.form>
          </AnimatePresence>
        </motion.div>

        {/* Link chuyển đổi */}
        <motion.p
          className="text-center mt-6 text-white/50 text-sm"
          variants={itemVariants}
        >
          {cheDoForm === 'dangNhap' ? 'Chưa có tài khoản? ' : 'Đã có tài khoản? '}
          <button
            onClick={chuyenCheDo}
            className="text-primary-400 hover:text-primary-300 font-medium transition-colors"
          >
            {cheDoForm === 'dangNhap' ? 'Đăng ký ngay' : 'Đăng nhập'}
          </button>
        </motion.p>

        {/* Footer */}
        <motion.div
          className="text-center mt-8 text-white/30 text-xs"
          variants={itemVariants}
        >
          <p>© 2026 Word2LaTeX Research Project</p>
          <div className="flex items-center justify-center gap-4 mt-2">
            <a href="#" className="hover:text-white/50 transition-colors">Chính sách</a>
            <span>•</span>
            <a href="#" className="hover:text-white/50 transition-colors">Điều khoản</a>
            <span>•</span>
            <a 
              href="https://github.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-white/50 transition-colors inline-flex items-center gap-1"
            >
              <Github className="w-3 h-3" />
              GitHub
            </a>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}

export default TrangDangNhap
