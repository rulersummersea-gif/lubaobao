const { request } = require('../../api/index')
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
      const localAlerts = retest.getPendingReminders()
      const remoteAlerts = (dashboard.alerts || []).map((item, index) => ({
        id: `remote-${index}`,
        title: item.title || item.boilerName || '异常提醒',
        desc: item.desc || item.text || '建议复测确认',
        action: '',
        relatedItemNames: '',
        level: item.level || 'warning',
        source: 'remote'
      }))
      this.setData({ list: localAlerts.concat(remoteAlerts) })
    } catch (e) {
      ui.error('告警加载失败')
    } finally {
      ui.hideLoading()
    }
  },
  completeRetest(e) {
    const id = e.currentTarget.dataset.id
    retest.completeReminder(id)
    ui.success('已完成')
    this.setData({ list: retest.getPendingReminders().concat(this.data.list.filter((item) => item.source === 'remote')) })
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
