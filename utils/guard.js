// utils/guard.js
// 鉴权守卫：当后端返回 401 / 登录失效时，统一清理登录态并跳回登录页。
const { clearToken } = require('./auth')
const { clearState } = require('../store/app-state')

function onAuthFailed() {
  try {
    clearToken()
    clearState()
  } catch (e) {}
  try {
    const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
    const current = pages.length ? pages[pages.length - 1].route : ''
    if (current !== 'pages/login/login') {
      wx.reLaunch({ url: '/pages/login/login' })
    }
  } catch (e) {
    wx.reLaunch({ url: '/pages/login/login' })
  }
}

module.exports = { onAuthFailed }
