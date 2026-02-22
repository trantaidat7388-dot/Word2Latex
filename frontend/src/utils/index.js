// index.js - Các hàm tiện ích dùng chung

/**
 * Định dạng kích thước file thành chuỗi dễ đọc
 */
export const dinhDangKichThuoc = (bytes) => {
  // Chuyển đổi bytes sang KB/MB/GB
  if (!bytes || bytes === 0) return '0 B'
  
  const donVi = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  
  return `${(bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)} ${donVi[i]}`
}

/**
 * Định dạng ngày giờ thành chuỗi tiếng Việt
 */
export const dinhDangNgayGio = (date, coGio = true) => {
  // Chuyển đổi Date object thành chuỗi định dạng Việt Nam
  if (!date) return 'N/A'
  
  const dateObj = date instanceof Date ? date : new Date(date)
  
  const options = {
    day: '2-digit',
    month: '2-digit', 
    year: 'numeric',
    ...(coGio && { hour: '2-digit', minute: '2-digit' })
  }
  
  return dateObj.toLocaleDateString('vi-VN', options)
}

/**
 * Định dạng thời gian tương đối (vd: "5 phút trước")
 */
export const dinhDangThoiGianTuongDoi = (date) => {
  // Trả về chuỗi thời gian tương đối
  if (!date) return 'N/A'
  
  const now = new Date()
  const dateObj = date instanceof Date ? date : new Date(date)
  const diff = now - dateObj
  
  const giay = Math.floor(diff / 1000)
  const phut = Math.floor(diff / 60000)
  const gio = Math.floor(diff / 3600000)
  const ngay = Math.floor(diff / 86400000)
  
  if (giay < 60) return 'Vừa xong'
  if (phut < 60) return `${phut} phút trước`
  if (gio < 24) return `${gio} giờ trước`
  if (ngay < 7) return `${ngay} ngày trước`
  
  return dinhDangNgayGio(dateObj)
}

/**
 * Rút gọn tên file nếu quá dài
 */
export const rutGonTenFile = (tenFile, maxLength = 30) => {
  // Rút gọn tên file nhưng giữ extension
  if (!tenFile || tenFile.length <= maxLength) return tenFile
  
  const dotIndex = tenFile.lastIndexOf('.')
  const extension = dotIndex > 0 ? tenFile.slice(dotIndex) : ''
  const name = dotIndex > 0 ? tenFile.slice(0, dotIndex) : tenFile
  
  const availableLength = maxLength - extension.length - 3 // 3 for "..."
  if (availableLength <= 0) return tenFile.slice(0, maxLength)
  
  return name.slice(0, availableLength) + '...' + extension
}

/**
 * Tạo ID ngẫu nhiên
 */
export const taoId = (length = 8) => {
  // Tạo chuỗi ID ngẫu nhiên
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

/**
 * Debounce function
 */
export const debounce = (func, wait = 300) => {
  // Trì hoãn thực thi function
  let timeout
  return (...args) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func.apply(this, args), wait)
  }
}

/**
 * Kiểm tra file có phải .docx không
 */
export const laFileDocx = (file) => {
  // Kiểm tra MIME type và extension của file
  if (!file) return false
  
  const validTypes = [
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ]
  const validExtensions = ['.docx']
  
  const hasValidType = validTypes.includes(file.type)
  const hasValidExtension = validExtensions.some(ext => 
    file.name.toLowerCase().endsWith(ext)
  )
  
  return hasValidType || hasValidExtension
}

/**
 * Sleep function for async operations
 */
export const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))
