// pages/mine/mine.js
// 我的页面：显示当前登录用户信息，并提供退出登录能力。
const { getState, clearState } = require('../../store/app-state')
const { clearToken } = require('../../utils/auth')

Page({
  data: { user: {}, enterprise: {}, boiler: null },

  onShow() {
    const state = getState()
    this.setData({ user: state.user || {}, enterprise: state.enterprise || {}, boiler: state.currentBoiler || null })
  },

  logout() {
    clearToken()
    clearState()
    const app = getApp()
    app.globalData.user = null
    app.globalData.enterprise = null
    app.globalData.currentBoiler = null
    app.globalData.isLoggedIn = false
    wx.reLaunch({ url: '/pages/login/login' })
  }
})
