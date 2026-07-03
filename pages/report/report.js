const { request } = require('../../api/index')
const ui = require('../../utils/ui')
Page({
  data: { report: null },
  async onShow() {
    try {
      ui.showLoading('加载报告')
      const report = await request({ url: '/report' })
      this.setData({ report })
    } catch (e) {
      ui.error('报告加载失败')
    } finally {
      ui.hideLoading()
    }
  }
})
