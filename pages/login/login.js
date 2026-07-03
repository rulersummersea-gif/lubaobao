// pages/login/login.js
// 登录页：先接入真实微信登录流程结构；当前后端未接通时仍可通过 config.useMock 走 mock。
const api = require('../../api/index')
const { setState } = require('../../store/app-state')
const { setToken } = require('../../utils/auth')
const ui = require('../../utils/ui')

Page({
  data: { submitting: false },

  async handleLogin() {
    if (this.data.submitting) return
    this.setData({ submitting: true })
    try {
      ui.showLoading('登录中')
      const loginRes = await new Promise((resolve, reject) => {
        wx.login({ success: resolve, fail: reject })
      })
      const res = await api.wxLogin(loginRes.code || 'mock_code')
      setToken(res.token)
      setState({ token: res.token, user: res.user, enterprise: res.enterprise })
      const app = getApp()
      app.globalData.user = res.user
      app.globalData.enterprise = res.enterprise
      app.globalData.isLoggedIn = true
      ui.hideLoading()
      ui.success('登录成功')
      setTimeout(() => wx.switchTab({ url: '/pages/index/index' }), 200)
    } catch (e) {
      ui.hideLoading()
      ui.error('登录失败')
      console.error('login error', e)
    } finally {
      this.setData({ submitting: false })
    }
  }
})
