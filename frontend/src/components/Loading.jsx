// Loading.jsx - Component loading với nhiều kiểu hiển thị

import { motion } from 'framer-motion'
import { FileText } from 'lucide-react'

export const LoadingSpinner = ({ 
  kichThuoc = 'md', 
  className = '' 
}) => {
  // Spinner loading đơn giản
  const lopKichThuoc = {
    sm: 'w-5 h-5 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4'
  }

  return (
    <div 
      className={`
        ${lopKichThuoc[kichThuoc]} 
        border-primary-500 border-t-transparent 
        rounded-full animate-spin
        ${className}
      `} 
    />
  )
}

export const LoadingManHinh = ({ thongBao = 'Đang tải...' }) => {
  // Loading toàn màn hình với logo animation
  return (
    <div className="min-h-screen bg-gradient-animated flex items-center justify-center">
      <motion.div 
        className="flex flex-col items-center gap-4"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
      >
        <motion.div
          className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-500/30"
          animate={{ 
            rotateY: [0, 360],
          }}
          transition={{ 
            duration: 2, 
            repeat: Infinity, 
            ease: 'easeInOut' 
          }}
        >
          <FileText className="w-8 h-8 text-white" />
        </motion.div>
        <div className="flex items-center gap-2">
          <LoadingSpinner kichThuoc="sm" />
          <p className="text-white/60">{thongBao}</p>
        </div>
      </motion.div>
    </div>
  )
}

export const LoadingXuLy = ({ 
  tienTrinh = 0, 
  thongBao = 'Đang xử lý...',
  chiTiet = ''
}) => {
  // Loading với thanh tiến trình cho quá trình chuyển đổi
  return (
    <motion.div
      className="glass-card p-6 w-full max-w-md"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="flex items-center gap-4 mb-4">
        <motion.div
          className="w-12 h-12 rounded-xl bg-primary-500/20 flex items-center justify-center"
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        >
          <FileText className="w-6 h-6 text-primary-400" />
        </motion.div>
        <div className="flex-1">
          <p className="text-white font-medium">{thongBao}</p>
          {chiTiet && (
            <p className="text-white/50 text-sm">{chiTiet}</p>
          )}
        </div>
        <span className="text-primary-400 font-mono text-lg">
          {Math.round(tienTrinh)}%
        </span>
      </div>
      
      {/* Thanh tiến trình */}
      <div className="h-2 bg-white/10 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-primary-600 to-primary-400 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${tienTrinh}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>
    </motion.div>
  )
}

export default LoadingSpinner
