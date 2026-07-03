// pages/mine/mine.js
// 我的页面：显示当前登录用户信息，并提供退出登录能力。
const { getState, clearState } = require('../../store/app-state')
const { clearToken } = require('../../utils/auth')

const config = require('../../config/index')

Page({
  data: {
    envKey: config.getEnvKey ? config.getEnvKey() : 'dev', user: {}, enterprise: {}, boiler: null },

  onShow() {
    this.setData({ envKey: config.getEnvKey ? config.getEnvKey() : 'dev' })
    const state = getState()
    this.setData({ user: state.user || {}, enterprise: state.enterprise || {}, boiler: state.currentBoiler || null })
  },


  switchEnv() {
    const envs = ['dev','staging','prod']
    const current = config.getEnvKey ? config.getEnvKey() : 'dev'
    const idx = envs.indexOf(current)
    const next = envs[(idx + 1) % envs.length]
    try {
      config.setEnv && config.setEnv(next)
      this.setData({ envKey: next })
      wx.showToast({ title: `环境已切换: ${next}`, icon: 'none' })
    } catch (e) {
      wx.showToast({ title: '环境切换失败', icon: 'none' })
    }
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
