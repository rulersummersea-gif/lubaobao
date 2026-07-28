const { getMonthlyReport } = require('../../api/report')
const { getState } = require('../../store/app-state')
const ui = require('../../utils/ui')

function currentMonth() {
  const date = new Date()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  return `${date.getFullYear()}-${month}`
}

Page({
  data: { report: null },
  async onShow() {
    const state = getState()
    try {
      ui.showLoading('加载报告')
      const report = await getMonthlyReport({
        enterpriseId: state.enterprise && state.enterprise.id,
        month: currentMonth()
      })
      this.setData({ report })
    } catch (e) {
      ui.error('报告加载失败')
    } finally {
      ui.hideLoading()
    }
  }
})
