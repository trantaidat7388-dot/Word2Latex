// api.js - Service gọi API backend Python để chuyển đổi file
import { API_BASE_URL } from '../config/apiConfig'

export const luuBlobThanhFile = (blob, tenFile) => {
  // Lưu blob thành file tải xuống trên trình duyệt
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = tenFile
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export const docLoiJsonTuResponse = async (response) => {
  // Đọc lỗi JSON từ response và trả về message tiếng Việt
  try {
    const data = await response.json()
    return data?.error || data?.detail || data?.message || 'Đã xảy ra lỗi khi xử lý'
  } catch {
    return 'Đã xảy ra lỗi khi xử lý'
  }
}

export const chuyenDoiFile = async (file, templateType = 'onecolumn') => {
  // Upload file Word và nhận JSON (tex_content + job_id) từ backend
  const formData = new FormData()
  formData.append('file', file)

  try {
    const controller = new AbortController()
    const timeoutMs = 180000
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

    const response = await fetch(`${API_BASE_URL}/api/chuyen-doi?template_type=${templateType}`, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    }).finally(() => {
      clearTimeout(timeoutId)
    })

    if (!response.ok) {
      const message = await docLoiJsonTuResponse(response)
      throw new Error(message)
    }

    const data = await response.json().catch(() => ({}))
    const texContent = data?.tex_content || ''
    const jobId = data?.job_id || ''
    const tenFileZip = data?.ten_file_zip || ''
    const tenFileLatex = data?.ten_file_latex || ''
    const metadata = data?.metadata || {}

    return {
      thanhCong: true,
      data: {
        texContent,
        jobId,
        tenFileZip,
        tenFileLatex,
        metadata,
      }
    }
  } catch (loi) {
    if (loi?.name === 'AbortError') {
      return {
        thanhCong: false,
        loiMessage: 'Xử lý quá lâu. Vui lòng thử lại hoặc tắt biên dịch PDF nếu máy server yếu.'
      }
    }
    return {
      thanhCong: false,
      loiMessage: loi.message || 'Không thể kết nối đến server'
    }
  }
}

export const taiFile = async (duongDan, tenFile) => {
  // Tải file từ server
  try {
    const response = await fetch(duongDan)
    
    if (!response.ok) {
      throw new Error('Không thể tải file')
    }

    const blob = await response.blob()
    luuBlobThanhFile(blob, tenFile)
    return { thanhCong: true }
  } catch (loi) {
    return {
      thanhCong: false,
      loiMessage: loi.message || 'Không thể tải file'
    }
  }
}

export const taiFileZip = async (jobId, tenFileZipFallback = '') => {
  // Tải file ZIP theo jobId từ server
  try {
    if (!jobId || typeof jobId !== 'string') {
      throw new Error('Job ID không hợp lệ')
    }

    const response = await fetch(`${API_BASE_URL}/api/tai-ve-zip/${jobId}`, {
      method: 'GET'
    })

    if (!response.ok) {
      const message = await docLoiJsonTuResponse(response)
      throw new Error(message)
    }

    const blob = await response.blob()
    const contentDisposition = response.headers.get('content-disposition') || ''
    const match = contentDisposition.match(/filename=([^;]+)/i)
    const tenFileTuHeader = match?.[1]?.replace(/"/g, '') || ''
    const tenFileZip = tenFileTuHeader || tenFileZipFallback || `${jobId}.zip`
    luuBlobThanhFile(blob, tenFileZip)
    return { thanhCong: true }
  } catch (loi) {
    return {
      thanhCong: false,
      loiMessage: loi.message || 'Không thể tải file ZIP'
    }
  }
}

export const layDanhSachTemplate = async () => {
  // Lấy danh sách template từ backend
  try {
    const response = await fetch(`${API_BASE_URL}/api/templates`)
    if (!response.ok) throw new Error('Không thể tải danh sách template')
    const data = await response.json()
    return { thanhCong: true, templates: data.templates || [] }
  } catch (loi) {
    return { thanhCong: false, templates: [], loiMessage: loi.message }
  }
}

export const taiLenTemplate = async (file) => {
  // Upload template LaTeX tùy chỉnh lên backend
  try {
    const formData = new FormData()
    formData.append('file', file)
    const response = await fetch(`${API_BASE_URL}/api/templates/upload`, {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || 'Không thể tải lên template')
    }
    const data = await response.json()
    return { thanhCong: true, template: data.template, message: data.message }
  } catch (loi) {
    return { thanhCong: false, loiMessage: loi.message }
  }
}

export const xoaTemplate = async (templateId) => {
  // Xóa template LaTeX tùy chỉnh trên backend
  try {
    const response = await fetch(`${API_BASE_URL}/api/templates/${templateId}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || 'Không thể xóa template')
    }
    return { thanhCong: true }
  } catch (loi) {
    return { thanhCong: false, loiMessage: loi.message }
  }
}

export const kiemTraServer = async () => {
  // Kiểm tra server backend có hoạt động hay không
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET'
    })
    return response.ok
  } catch {
    return false
  }
}

export default {
  chuyenDoiFile,
  luuBlobThanhFile,
  taiFile,
  taiFileZip,
  layDanhSachTemplate,
  taiLenTemplate,
  xoaTemplate,
  kiemTraServer
}
