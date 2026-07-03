// pages/result/result.js
// 结果页：展示最近一次巡检识别结果，并允许提交为正式巡检记录。
const { request } = require('../../api/index')
const ui = require('../../utils/ui')

Page({
  data: { result: null, submitting: false },

  onShow() {
    this.setData({ result: wx.getStorageSync('BG_LAST_RESULT') || { items: [], diagnosis: [] } })
  },

  async submitRecord() {
    if (this.data.submitting) return
    const inspectionId = wx.getStorageSync('BG_LAST_INSPECTION_ID')
    if (!inspectionId) return ui.error('缺少巡检ID')
    this.setData({ submitting: true })
    try {
      ui.showLoading('提交中')
      await request({ url: '/inspections/submit', method: 'POST', data: { inspectionId, remark: 'Mock提交成功' } })
      ui.success('已提交巡检记录')
      setTimeout(() => wx.switchTab({ url: '/pages/records/records' }), 300)
    } catch (e) {
      ui.error('提交失败')
    } finally {
      ui.hideLoading()
      this.setData({ submitting: false })
    }
  }
})
