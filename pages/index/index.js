// pages/index/index.js
// 首页工作台：展示当前用户、企业、锅炉、统计数据和快捷入口。
const { request } = require('../../api/index')
const { getRetestTasks } = require('../../api/inspection')
const { getState } = require('../../store/app-state')
const ui = require('../../utils/ui')
const retest = require('../../utils/retest')

Page({
  data: {
    user: null,
    enterprise: null,
    currentBoiler: null,
    stats: [],
    alerts: [],
    latestSummary: '',
    canInspect: true,
    packWarning: ''
  },

  async onShow() {
    const state = getState()
    if (!state.token) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    try {
      ui.showLoading('加载中')
      const dashboard = await request({ url: '/dashboard' })
      let localAlerts = retest.getPendingReminders().slice(0, 3)
      try {
        const serverTasks = await getRetestTasks({ status: 'pending' })
        if (serverTasks && serverTasks.length) localAlerts = serverTasks.slice(0, 3)
      } catch (taskError) {}
      const remoteAlerts = (dashboard.alerts || []).map((item) => ({
        title: item.title || item.boilerName || '异常提醒',
        desc: item.desc || item.text || '建议复测确认',
        level: item.level || 'warning'
      }))
      const lastResult = wx.getStorageSync('BG_LAST_RESULT') || {}
      this.setData({
        user: state.user,
        enterprise: state.enterprise,
        currentBoiler: state.currentBoiler || null,
        canInspect: !state.onboarding || state.onboarding.canInspect !== false,
        packWarning: state.onboarding && state.onboarding.canInspect === false ? state.onboarding.message : '',
        stats: dashboard.stats || [],
        alerts: (localAlerts.length ? localAlerts : remoteAlerts).slice(0, 3),
        latestSummary: lastResult.summary || ''
      })
    } catch (e) {
      ui.error('首页加载失败')
    } finally {
      ui.hideLoading()
    }
  },
  goInspect() {
    if (!this.data.canInspect) return this.goReplacePack()
    wx.switchTab({ url: '/pages/inspect/inspect' })
  },
  goReplacePack() {
    const state = getState()
    const reason = encodeURIComponent((state.onboarding && state.onboarding.reason) || 'pack_expired')
    wx.navigateTo({ url: `/pages/onboarding/onboarding?reason=${reason}` })
  },
  goActivate() { wx.navigateTo({ url: '/pages/activate/activate' }) },
  goBoilers() { wx.navigateTo({ url: '/pages/boiler/boiler' }) },
  goReport() { wx.navigateTo({ url: '/pages/report/report' }) },
  goBoilerRegister() { wx.navigateTo({ url: '/pages/boiler-register/boiler-register' }) },
  goAlerts() { wx.navigateTo({ url: '/pages/alerts/alerts' }) }
})
