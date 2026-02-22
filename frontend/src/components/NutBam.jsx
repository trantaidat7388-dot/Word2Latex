// NutBam.jsx - Component nút bấm tái sử dụng với nhiều biến thể

import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'

const NutBam = ({
  children,
  bienThe = 'primary', // 'primary' | 'secondary' | 'ghost' | 'danger'
  kichThuoc = 'md', // 'sm' | 'md' | 'lg'
  dangTai = false,
  tatHieuUng = false,
  className = '',
  icon: Icon,
  iconViTri = 'left',
  ...props
}) => {
  // Component nút bấm đa năng với animation và loading state
  
  const lopBienThe = {
    primary: 'bg-gradient-to-r from-primary-600 to-primary-500 text-white shadow-lg shadow-primary-500/25 hover:shadow-primary-500/40 hover:from-primary-500 hover:to-primary-400',
    secondary: 'bg-white/10 backdrop-blur-md border border-white/20 text-white hover:bg-white/20 hover:border-white/30',
    ghost: 'bg-transparent text-white/70 hover:text-white hover:bg-white/10',
    danger: 'bg-gradient-to-r from-red-600 to-red-500 text-white shadow-lg shadow-red-500/25 hover:shadow-red-500/40'
  }

  const lopKichThuoc = {
    sm: 'py-2 px-4 text-sm gap-1.5',
    md: 'py-3 px-6 text-base gap-2',
    lg: 'py-4 px-8 text-lg gap-2.5'
  }

  const kichThuocIcon = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6'
  }

  return (
    <motion.button
      className={`
        inline-flex items-center justify-center font-medium rounded-xl
        transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed
        ${lopBienThe[bienThe]}
        ${lopKichThuoc[kichThuoc]}
        ${className}
      `}
      whileHover={!tatHieuUng && !props.disabled ? { scale: 1.02 } : {}}
      whileTap={!tatHieuUng && !props.disabled ? { scale: 0.98 } : {}}
      disabled={dangTai || props.disabled}
      {...props}
    >
      {dangTai ? (
        <Loader2 className={`${kichThuocIcon[kichThuoc]} animate-spin`} />
      ) : (
        <>
          {Icon && iconViTri === 'left' && <Icon className={kichThuocIcon[kichThuoc]} />}
          {children}
          {Icon && iconViTri === 'right' && <Icon className={kichThuocIcon[kichThuoc]} />}
        </>
      )}
    </motion.button>
  )
}

export default NutBam
