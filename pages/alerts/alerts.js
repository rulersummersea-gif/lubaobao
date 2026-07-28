const { request } = require('../../api/index')
const { getRetestTasks, completeRetestTask, resolveRetestTask } = require('../../api/inspection')
const { getState } = require('../../store/app-state')
const ui = require('../../utils/ui')
const retest = require('../../utils/retest')
Page({
  data: { list: [] },
  async onShow() {
    this.loadAlerts()
  },
  async loadAlerts() {
    try {
      ui.showLoading('加载告警')
      const dashboard = await request({ url: '/dashboard' })
      const state = getState()
      const boilerId = state.currentBoiler && state.currentBoiler.id
      let localAlerts = retest.getPendingReminders()
        .filter((item) => !boilerId || Number(item.boilerId) === Number(boilerId))
      try {
        const serverTasks = await getRetestTasks({ status: 'pending', ...(boilerId ? { boilerId } : {}) })
        if (serverTasks) {
          localAlerts = serverTasks.map((item) => ({
            ...item,
            serviceAdvice: item.serviceAdvice || '',
            serviceByName: item.serviceByName || '',
            serviceAtText: this.formatTime(item.serviceAt),
            serviceStatusText: item.serviceAdvice ? '已回复' : '待回复',
            actionText: [
              item.title,
              item.relatedItemNames ? `关联指标：${item.relatedItemNames}` : '',
              item.fieldAction ? `系统现场建议：${item.fieldAction}` : '',
              item.serviceAdvice ? `服务人员专业意见：${item.serviceAdvice}` : '',
              item.retestPlan ? `复测安排：${item.retestPlan}` : ''
            ].filter(Boolean).join('\n')
          }))
        }
      } catch (taskError) {}
      const remoteAlerts = (dashboard.alerts || []).map((item, index) => ({
        id: `remote-${index}`,
        title: item.title || item.boilerName || '异常提醒',
        desc: item.desc || item.text || '建议复测确认',
        action: '',
        relatedItemNames: '',
        level: item.level || 'warning',
        source: 'remote'
      }))
      this.setData({ list: localAlerts.length ? localAlerts : remoteAlerts })
    } catch (e) {
      ui.error('告警加载失败')
    } finally {
      ui.hideLoading()
    }
  },
  formatTime(value) {
    return value ? String(value).replace('T', ' ').slice(0, 16) : ''
  },
  async completeRetest(e) {
    const id = e.currentTarget.dataset.id
    const isLocal = String(id).indexOf('-') >= 0
    try {
      if (isLocal) retest.completeReminder(id)
      else await completeRetestTask(id)
    } catch (taskError) {
      retest.completeReminder(id)
    }
    ui.success('已完成')
    this.loadAlerts()
  },
  startRetest(e) {
    const index = Number(e.currentTarget.dataset.index)
    const item = this.data.list[index]
    if (!item) return ui.error('缺少复测任务')
    wx.setStorageSync('BG_RETEST_TASK', item)
    wx.switchTab({ url: '/pages/inspect/inspect' })
  },
  async skipRetest(e) {
    const id = e.currentTarget.dataset.id
    const isLocal = String(id).indexOf('-') >= 0
    try {
      if (isLocal) retest.completeReminder(id)
      else await resolveRetestTask(id, { resolutionType: 'no_retest', note: '现场选择暂不复测' })
    } catch (taskError) {
      retest.completeReminder(id)
    }
    ui.success('已记录')
    this.loadAlerts()
  },
  copyAction(e) {
    const index = Number(e.currentTarget.dataset.index)
    const item = this.data.list[index]
    if (!item || !item.actionText) return ui.error('暂无可复制内容')
    wx.setClipboardData({
      data: item.actionText,
      success: () => ui.success('已复制')
    })
  }
})
