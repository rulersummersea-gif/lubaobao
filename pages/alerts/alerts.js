const { request } = require('../../api/index')
const { getRetestTasks, completeRetestTask, resolveRetestTask } = require('../../api/inspection')
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
      let localAlerts = retest.getPendingReminders()
      try {
        const serverTasks = await getRetestTasks({ status: 'pending' })
        if (serverTasks) localAlerts = serverTasks
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
