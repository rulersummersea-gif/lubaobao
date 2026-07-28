// store/app-state.js
// 本地状态管理：统一保存 token、用户、企业、当前锅炉。
const DEFAULT_KEY = 'BG_APP_STATE'
const LAST_BOILER_KEY = 'BG_LAST_BOILER_BY_USER'

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

function getLastBoiler(userId) {
  if (!userId) return null
  try {
    const saved = wx.getStorageSync(LAST_BOILER_KEY) || {}
    return saved[String(userId)] || null
  } catch (e) {
    return null
  }
}

function saveLastBoiler(userId, boiler) {
  if (!userId || !boiler || !boiler.id) return
  try {
    const saved = wx.getStorageSync(LAST_BOILER_KEY) || {}
    saved[String(userId)] = boiler
    wx.setStorageSync(LAST_BOILER_KEY, saved)
  } catch (e) {}
}

module.exports = { getState, setState, clearState, getLastBoiler, saveLastBoiler }
