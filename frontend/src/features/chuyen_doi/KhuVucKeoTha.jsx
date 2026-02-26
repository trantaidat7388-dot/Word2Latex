// KhuVucKeoTha.jsx - Component kéo thả file với hiệu ứng glow

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload,
  FileText,
  X,
  AlertCircle,
  CheckCircle2,
  File
} from 'lucide-react'

const KhuVucKeoTha = ({
  onChonFile,
  dangTaiLen = false,
  fileHienTai = null,
  onXoaFile,
  loiValidation = null
}) => {
  // Component dropzone với hiệu ứng glow khi kéo file vào
  const [dangKeoVao, setDangKeoVao] = useState(false)

  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    // Xử lý khi file được thả vào dropzone
    setDangKeoVao(false)

    if (rejectedFiles.length > 0) {
      const loi = rejectedFiles[0].errors[0]
      if (loi.code === 'file-invalid-type') {
        onChonFile(null, 'Chỉ chấp nhận file .docx hoặc .docm')
      } else if (loi.code === 'file-too-large') {
        onChonFile(null, 'File quá lớn (tối đa 10MB)')
      }
      return
    }

    if (acceptedFiles.length > 0) {
      onChonFile(acceptedFiles[0], null)
    }
  }, [onChonFile])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      // Chấp nhận cả file .docx và .docm (Word Macro-Enabled)
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.ms-word.document.macroEnabled.12': ['.docm']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: false,
    disabled: dangTaiLen,
    onDragEnter: () => setDangKeoVao(true),
    onDragLeave: () => setDangKeoVao(false)
  })

  const layKichThuocFile = (bytes) => {
    // Chuyển đổi bytes sang đơn vị KB/MB dễ đọc
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  return (
    <div className="w-full">
      <AnimatePresence mode="wait">
        {!fileHienTai ? (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
          >
            <div
              {...getRootProps()}
              className={`
                relative overflow-hidden rounded-2xl border-2 border-dashed 
                transition-all duration-300 cursor-pointer
                ${dangTaiLen ? 'opacity-50 cursor-not-allowed' : ''}
                ${isDragActive || dangKeoVao
                  ? 'border-primary-400 bg-primary-500/10 shadow-[0_0_40px_rgba(99,102,241,0.4)]'
                  : 'border-white/20 bg-white/5 hover:border-primary-500/50 hover:bg-white/10'
                }
              `}
            >
              <input {...getInputProps()} />

              {/* Hiệu ứng glow khi kéo */}
              <AnimatePresence>
                {(isDragActive || dangKeoVao) && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute inset-0 bg-gradient-to-br from-primary-500/20 to-purple-500/20"
                  />
                )}
              </AnimatePresence>

              <div className="relative z-10 flex flex-col items-center justify-center py-12 px-6">
                <motion.div
                  className={`
                    w-20 h-20 rounded-2xl mb-6 flex items-center justify-center
                    transition-all duration-300
                    ${isDragActive || dangKeoVao
                      ? 'bg-primary-500/30 shadow-lg shadow-primary-500/30'
                      : 'bg-white/10'
                    }
                  `}
                  animate={isDragActive || dangKeoVao ? {
                    scale: [1, 1.1, 1],
                    rotate: [0, 5, -5, 0]
                  } : {}}
                  transition={{ duration: 0.5, repeat: isDragActive ? Infinity : 0 }}
                >
                  <Upload className={`
                    w-10 h-10 transition-colors duration-300
                    ${isDragActive || dangKeoVao ? 'text-primary-300' : 'text-white/50'}
                  `} />
                </motion.div>

                <h3 className="text-lg font-medium text-white mb-2">
                  {isDragActive || dangKeoVao
                    ? 'Thả file vào đây!'
                    : 'Kéo & thả file Word của bạn'
                  }
                </h3>

                <p className="text-white/50 text-sm mb-4">
                  hoặc nhấp để chọn file
                </p>

                <div className="flex items-center gap-4 text-xs text-white/40">
                  <span className="flex items-center gap-1">
                    <FileText className="w-4 h-4" />
                    Chấp nhận .docx / .docm
                  </span>
                  <span>•</span>
                  <span>Tối đa 10MB</span>
                </div>
              </div>

              {/* Animated border khi kéo */}
              {(isDragActive || dangKeoVao) && (
                <motion.div
                  className="absolute inset-0 rounded-2xl pointer-events-none"
                  initial={{ opacity: 0 }}
                  animate={{
                    opacity: [0.5, 1, 0.5],
                    boxShadow: [
                      '0 0 20px rgba(99,102,241,0.3)',
                      '0 0 40px rgba(99,102,241,0.5)',
                      '0 0 20px rgba(99,102,241,0.3)'
                    ]
                  }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  style={{ border: '2px solid rgba(99,102,241,0.5)' }}
                />
              )}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="file-selected"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="glass-card p-6"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-primary-500/20 flex items-center justify-center flex-shrink-0">
                <File className="w-7 h-7 text-primary-400" />
              </div>

              <div className="flex-1 min-w-0">
                <h4 className="text-white font-medium truncate">
                  {fileHienTai.name}
                </h4>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-white/50 text-sm">
                    {layKichThuocFile(fileHienTai.size)}
                  </span>
                  <span className="flex items-center gap-1 text-green-400 text-sm">
                    <CheckCircle2 className="w-4 h-4" />
                    Sẵn sàng
                  </span>
                </div>
              </div>

              {!dangTaiLen && (
                <motion.button
                  onClick={onXoaFile}
                  className="p-2 rounded-xl hover:bg-white/10 text-white/50 hover:text-white transition-colors"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                >
                  <X className="w-5 h-5" />
                </motion.button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Thông báo lỗi */}
      <AnimatePresence>
        {loiValidation && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-3 flex items-center gap-2 text-red-400 text-sm"
          >
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{loiValidation}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default KhuVucKeoTha
