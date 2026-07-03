// utils/ui.js
// 统一封装常用界面交互，避免每个页面重复写 toast / loading 代码。
function showLoading(title = '加载中') { wx.showLoading({ title, mask: true }) }
function hideLoading() { wx.hideLoading() }
function success(title = '成功') { wx.showToast({ title, icon: 'success' }) }
function error(title = '操作失败') { wx.showToast({ title, icon: 'none' }) }
module.exports = { showLoading, hideLoading, success, error }
