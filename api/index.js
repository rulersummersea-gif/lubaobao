// api/index.js
// 统一 API 出口：支持 mock / 真实接口双模式切换。
const config = require('../config/index')
const mock = require('../services/mock-service')
const { http } = require('../services/http')
const { getToken } = require('../utils/auth')

function request({ url, method = 'GET', data = {} }) {
  if (config.useMock) {
    const routeMap = {
      '/auth/login': () => mock.login(data),
      '/dashboard': () => mock.getDashboard(),
      '/boilers': () => mock.getBoilers(),
      '/boilers/create': () => mock.createBoiler(data),
      '/material-packs/verify': () => mock.verifyMaterialPack(data.code),
      '/material-packs/activate': () => mock.activateMaterialPack(data),
      '/inspections/create': () => mock.createInspection(data),
      '/inspections/recognize': () => mock.recognizeInspection(data),
      '/records': () => mock.getRecords(),
      '/record-detail': () => mock.getRecordDetail(data.id),
      '/inspections/submit': () => mock.submitInspection(data),
      '/report': () => mock.getReport()
    }
    const handler = routeMap[url]
    if (!handler) return Promise.reject(new Error('未定义的Mock接口: ' + url))
    return handler()
  }
  return http({ url, method, data })
}

// 真实接口版：微信登录接口
function wxLogin(code) {
  if (config.useMock) return request({ url: '/auth/login', method: 'POST', data: { code } })
  return http({ url: '/auth/wx-login', method: 'POST', data: { code } })
}

// 真实接口版：扫描材料包后校验
function verifyPack(code) {
  return request({ url: '/material-packs/verify', method: 'POST', data: { code } })
}

// 真实接口版：上传巡检图片
function uploadInspectionImage(filePath, inspectionId) {
  if (config.useMock) {
    return Promise.resolve({ success: true, imageUrl: filePath, inspectionId })
  }
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: config.baseURL + '/inspections/upload-image',
      filePath,
      name: 'file',
      formData: { inspectionId },
      header: { Authorization: getToken() ? `Bearer ${getToken()}` : '' },
      success: (res) => {
        try {
          const payload = JSON.parse(res.data || '{}')
          if (res.statusCode < 200 || res.statusCode >= 300) {
            reject(new Error(payload.detail || payload.message || '图片上传失败'))
            return
          }
          resolve(payload)
        } catch (e) { reject(e) }
      },
      fail: reject
    })
  })
}

module.exports = { request, wxLogin, verifyPack, uploadInspectionImage }
