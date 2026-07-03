const { request } = require('../../api/index')
const ui = require('../../utils/ui')
Page({
  data: { list: [] },
  async onShow() {
    try {
      ui.showLoading('加载告警')
      const dashboard = await request({ url: '/dashboard' })
      this.setData({ list: dashboard.alerts || [] })
    } catch (e) {
      ui.error('告警加载失败')
    } finally {
      ui.hideLoading()
    }
  }
})
