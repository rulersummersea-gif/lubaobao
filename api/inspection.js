const { request } = require('./index')
function createInspection(data) {
  return request({ url: '/inspections/create', method: 'POST', data })
}
function recognizeInspection(data) {
  return request({ url: '/inspections/recognize', method: 'POST', data })
}
function submitInspection(data) {
  return request({ url: '/inspections/submit', method: 'POST', data })
}
function getRecords() {
  return request({ url: '/records' })
}
function getRecordDetail(id) {
  return request({ url: '/record-detail', method: 'GET', data: { id } })
}
module.exports = { createInspection, recognizeInspection, submi
...[参数过长，已省略 9658 字符]...
 function onAuthFailed() {
  clearToken()
  const pages = getCurrentPages ? getCurrentPages() : []
  const current = pages.length ? pages[pages.length - 1].route : ''
  if (current !== 'pages/login/login') {
    wx.reLaunch({ url: '/pages/login/login' })
  }
}
module.exports = { onAuthFailed }
