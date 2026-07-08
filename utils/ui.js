// utils/ui.js
// 统一封装常用界面交互，避免每个页面重复写 toast / loading 代码。
let loadingCount = 0

function showLoading(title = '加载中') {
  loadingCount += 1
  wx.showLoading({ title, mask: true })
}

function hideLoading() {
  if (loadingCount <= 0) return
  loadingCount -= 1
  if (loadingCount === 0) wx.hideLoading()
}

function success(title = '成功') { wx.showToast({ title, icon: 'success' }) }
function error(title = '操作失败') { wx.showToast({ title, icon: 'none' }) }
module.exports = { showLoading, hideLoading, success, error }
