// api/index.js
// 统一 API 出口：支持 mock / 真实接口双模式切换。
const config = require('../config/index')
const mock = require('../services/mock-service')
const { http } = require('../services/http')

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

// 真实接口版：上传巡检图片（当前只预留接口）
function uploadInspectionImage(filePath, inspectionId) {
  if (config.useMock) {
    return Promise.resolve({ success: true, imageUrl: filePath, inspectionId })
  }
  // 当前灰测后端 0.4.0-rbac 暂未暴露图片上传接口，先保留本地图片路径并放行识别流程。
  return Promise.resolve({ success: true, imageUrl: filePath, inspectionId, skippedUpload: true })
}

module.exports = { request, wxLogin, verifyPack, uploadInspectionImage }
