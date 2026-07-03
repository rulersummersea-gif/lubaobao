const config = require('../config/index')
const { getToken, clearToken } = require('../utils/auth')
const { clearState } = require('../store/app-state')

function unwrapResponse(payload) {
  if (payload == null) return payload

  // 兼容：{ code, message, data }
  if (typeof payload.code !== 'undefined') {
    const ok = Number(payload.code) === 0 || Number(payload.code) === 200
    if (!ok) throw new Error(payload.message || payload.msg || '请求失败')
    return typeof payload.data === 'undefined' ? payload : payload.data
  }

  // 兼容：{ success, data, message }
  if (typeof payload.success !== 'undefined') {
    if (!payload.success) throw new Error(payload.message || payload.msg || '请求失败')
    return typeof payload.data === 'undefined' ? payload : payload.data
  }

  // 兼容：{ data }
  if (typeof payload.data !== 'undefined' && Object.keys(payload).length <= 3) {
    return payload.data
  }

  return payload
}

function on401() {
  try { clearToken() } catch (e) {}
  try { clearState() } catch (e) {}
  const pages = getCurrentPages ? getCurrentPages() : []
  const current = pages.length ? pages[pages.length - 1].route : ''
  if (current !== 'pages/login/login') {
    wx.reLaunch({ url: '/pages/login/login' })
  }
}

function http({ url, method = 'GET', data = {}, header = {} }) {
  const cfg = config.getConfig ? config.getConfig() : config
  const token = getToken()

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${cfg.baseURL}${url}`,
      method,
      data,
      timeout: cfg.timeout || 15000,
      header: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...header
      },
      success: (res) => {
        try {
          const status = res.statusCode
          if (status === 401) {
            on401()
            return reject(new Error('登录已失效，请重新登录'))
          }
          if (status < 200 || status >= 300) {
            const requestId = (res.header && (res.header['x-request-id'] || res.header['X-Request-Id'])) || ''
            return reject(new Error(`HTTP ${status}${requestId ? ` (rid:${requestId})` : ''}`))
          }
          const unwrapped = unwrapResponse(res.data)
          resolve(unwrapped)
        } catch (e) {
          reject(e)
        }
      },
      fail: (err) => {
        reject(new Error((err && err.errMsg) || '网络请求失败'))
      }
    })
  })
}

module.exports = { http, unwrapResponse }
