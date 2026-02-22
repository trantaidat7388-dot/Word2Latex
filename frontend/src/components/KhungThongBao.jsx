// KhungThongBao.jsx - Component thông báo dạng card với nhiều loại

import { motion, AnimatePresence } from 'framer-motion'
import { 
  CheckCircle2, 
  AlertCircle, 
  Info, 
  AlertTriangle,
  X 
} from 'lucide-react'

const KhungThongBao = ({
  loai = 'info', // 'success' | 'error' | 'warning' | 'info'
  tieuDe,
  noiDung,
  hienThi = true,
  coThedong = false,
  onDong,
  className = ''
}) => {
  // Component hiển thị thông báo với icon và màu sắc tương ứng
  
  const cauHinh = {
    success: {
      icon: CheckCircle2,
      bgClass: 'bg-green-500/10 border-green-500/30',
      iconClass: 'text-green-400',
      titleClass: 'text-green-300'
    },
    error: {
      icon: AlertCircle,
      bgClass: 'bg-red-500/10 border-red-500/30',
      iconClass: 'text-red-400',
      titleClass: 'text-red-300'
    },
    warning: {
      icon: AlertTriangle,
      bgClass: 'bg-yellow-500/10 border-yellow-500/30',
      iconClass: 'text-yellow-400',
      titleClass: 'text-yellow-300'
    },
    info: {
      icon: Info,
      bgClass: 'bg-blue-500/10 border-blue-500/30',
      iconClass: 'text-blue-400',
      titleClass: 'text-blue-300'
    }
  }

  const { icon: Icon, bgClass, iconClass, titleClass } = cauHinh[loai]

  return (
    <AnimatePresence>
      {hienThi && (
        <motion.div
          initial={{ opacity: 0, y: -10, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -10, scale: 0.95 }}
          transition={{ duration: 0.2 }}
          className={`
            rounded-xl border backdrop-blur-md p-4
            ${bgClass}
            ${className}
          `}
        >
          <div className="flex items-start gap-3">
            <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${iconClass}`} />
            <div className="flex-1 min-w-0">
              {tieuDe && (
                <h4 className={`font-medium mb-1 ${titleClass}`}>
                  {tieuDe}
                </h4>
              )}
              {noiDung && (
                <p className="text-white/70 text-sm">
                  {noiDung}
                </p>
              )}
            </div>
            {coTheDong && onDong && (
              <button
                onClick={onDong}
                className="p-1 rounded-lg hover:bg-white/10 transition-colors"
              >
                <X className="w-4 h-4 text-white/50" />
              </button>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export default KhungThongBao
