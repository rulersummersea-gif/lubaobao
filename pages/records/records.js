// pages/records/records.js
// 巡检记录列表页：展示历史记录，支持进入详情查看检测值和诊断建议。
const { request } = require('../../api/index')
const ui = require('../../utils/ui')

Page({
  data: { list: [] },

  async onShow() {
    try {
      ui.showLoading('加载记录')
      const list = await request({ url: '/records' })
      this.setData({ list: list || [] })
    } catch (e) {
      ui.error('记录加载失败')
    } finally {
      ui.hideLoading()
    }
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/record-detail/record-detail?id=' + e.currentTarget.dataset.id })
  }
})
