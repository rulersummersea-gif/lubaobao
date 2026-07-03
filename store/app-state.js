// store/app-state.js
// 本地状态管理：统一保存 token、用户、企业、当前锅炉。
const DEFAULT_KEY = 'BG_APP_STATE'
function getState() {
  try {
    return wx.getStorageSync(DEFAULT_KEY) || {}
  } catch (e) {
    return {}
  }
}
function setState(patch) {
  const prev = getState()
  const next = { ...prev, ...patch }
  wx.setStorageSync(DEFAULT_KEY, next)
  return next
}
function clearState() {
  wx.removeStorageSync(DEFAULT_KEY)
}
module.exports = { getState, setState, clearState }
