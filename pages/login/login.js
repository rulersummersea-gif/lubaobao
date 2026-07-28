// pages/login/login.js
// 登录页：先接入真实微信登录流程结构；当前后端未接通时仍可通过 config.useMock 走 mock。
const api = require('../../api/index')
const config = require('../../config/index')
const { getLastBoiler, setState } = require('../../store/app-state')
const { setToken } = require('../../utils/auth')
const ui = require('../../utils/ui')

Page({
  data: { submitting: false, envKey: config.getEnvKey(), canUseLocal: config.getEnvKey() !== 'prod', scene: '' },

  onLoad(options = {}) {
    let scene = ''
    try { scene = decodeURIComponent(options.scene || '') } catch (e) { scene = options.scene || '' }
    this.setData({ scene })
  },

  useLocalEnv() {
    config.setEnv('local')
    this.setData({ envKey: 'local' })
    ui.success('已切换本地环境')
  },

  async handleLogin() {
    if (this.data.submitting) return
    this.setData({ submitting: true })
    try {
      ui.showLoading('登录中')
      const loginRes = await new Promise((resolve, reject) => {
        wx.login({ success: resolve, fail: reject })
      })
      const res = await api.wxLogin(loginRes.code || 'mock_code')
      const savedBoiler = getLastBoiler(res.user && res.user.id)
      const sameEnterprise = savedBoiler && (
        !savedBoiler.enterpriseId
        || !res.user.enterpriseId
        || Number(savedBoiler.enterpriseId) === Number(res.user.enterpriseId)
      )
      const currentBoiler = res.currentBoiler || (sameEnterprise ? savedBoiler : null)
      setToken(res.token)
      setState({
        token: res.token,
        user: res.user,
        enterprise: res.enterprise,
        currentBoiler,
        onboarding: res.onboarding || null
      })
      const app = getApp()
      app.globalData.user = res.user
      app.globalData.enterprise = res.enterprise
      app.globalData.currentBoiler = currentBoiler
      app.globalData.isLoggedIn = true
      ui.hideLoading()
      ui.success('登录成功')
      if (this.data.scene) {
        const scene = encodeURIComponent(this.data.scene)
        setTimeout(() => wx.reLaunch({ url: `/pages/onboarding/onboarding?reason=scan_code&scene=${scene}` }), 200)
      } else if (res.onboarding && res.onboarding.required) {
        const reason = encodeURIComponent(res.onboarding.reason || 'first_login')
        setTimeout(() => wx.reLaunch({ url: `/pages/onboarding/onboarding?reason=${reason}` }), 200)
      } else {
        setTimeout(() => wx.switchTab({ url: '/pages/index/index' }), 200)
      }
    } catch (e) {
      ui.hideLoading()
      ui.error('登录失败')
      console.error('login error', e)
    } finally {
      this.setData({ submitting: false })
    }
  }
})
