// services/http.js
// 真实后端请求层：统一处理 baseURL、token、错误提示、超时、返回结构适配。
const config = require('../config/index')
const { getToken } = require('../utils/auth')
const { onAuthFailed } = require('../utils/guard')

function unwrapResponse(raw) {
  if (raw && typeof raw === 'object') {
    if (Object.prototype.hasOwnProperty.call(raw, 'code')) {
      if (raw.code === 0 || raw.code === 200) return raw.data
      if (raw.code === 401) {
        onAuthFailed()
        throw new Error(raw.message || '登录已失效')
      }
      throw new Error(raw.message || '请求失败')
    }
    if (Object.prototype.hasOwnProperty.call(raw, 'success')) {
      if (raw.success) return raw.data !== undefined ? raw.data : raw
      throw new Error(raw.message || '请求失败')
    }
  }
  return raw
}

function http({ url, method = 'GET', data = {}, header = {} }) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${config.baseURL}${url}`,
      method,
      data,
      timeout: config.timeout || 15000,
      header: {
        Authorization: getToken() ? `Bearer ${getToken()}` : '',
        ...header
      },
      success: (res) => {
        try {
          resolve(unwrapResponse(res.data))
        } catch (e) {
          reject(e)
        }
      },
      fail: reject
    })
  })
}

module.exports = { http, unwrapResponse }
