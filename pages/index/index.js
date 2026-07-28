// pages/index/index.js
// 首页工作台：展示当前用户、企业、锅炉、统计数据和快捷入口。
const { request } = require('../../api/index')
const { getRetestTasks } = require('../../api/inspection')
const { getState } = require('../../store/app-state')
const { refreshOnboardingState } = require('../../utils/onboarding-session')
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
    let state = getState()
    if (!state.token) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    try {
      ui.showLoading('加载中')
      try {
        state = await refreshOnboardingState()
      } catch (statusError) {
        console.warn('onboarding status refresh failed', statusError)
      }
      const dashboard = await request({ url: '/dashboard' })
      const boilerId = state.currentBoiler && state.currentBoiler.id
      let localAlerts = retest.getPendingReminders()
        .filter((item) => !boilerId || Number(item.boilerId) === Number(boilerId))
        .slice(0, 3)
      try {
        const serverTasks = await getRetestTasks({ status: 'pending', ...(boilerId ? { boilerId } : {}) })
        if (serverTasks && serverTasks.length) localAlerts = serverTasks.slice(0, 3)
      } catch (taskError) {}
      const remoteAlerts = (dashboard.alerts || []).map((item) => ({
        title: item.title || item.boilerName || '异常提醒',
        desc: item.desc || item.text || '建议复测确认',
        level: item.level || 'warning'
      }))
      const lastResult = wx.getStorageSync('BG_LAST_RESULT') || {}
      const alerts = (localAlerts.length ? localAlerts : remoteAlerts).slice(0, 3).map((item, index) => ({
        ...item,
        serviceLabel: item.serviceAdvice ? '服务人员已给出专业意见' : (item.id ? '专业意见待复核' : ''),
        key: item.id || item.riskCode || `${item.title || 'alert'}-${index}`
      }))
      this.setData({
        user: state.user,
        enterprise: state.enterprise,
        currentBoiler: state.currentBoiler || null,
        canInspect: !state.onboarding || state.onboarding.canInspect !== false,
        packWarning: state.onboarding && state.onboarding.canInspect === false ? state.onboarding.message : '',
        stats: dashboard.stats || [],
        alerts,
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
