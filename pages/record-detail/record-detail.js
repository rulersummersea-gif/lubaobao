// pages/record-detail/record-detail.js
// 记录详情页：展示单次巡检的完整内容，包括结果明细、诊断建议和备注。
const { request } = require('../../api/index')
const ui = require('../../utils/ui')

Page({
  data: { detail: { items: [], diagnosis: [] } },

  async onLoad(options) {
    try {
      ui.showLoading('加载详情')
      const detail = await request({ url: '/record-detail', method: 'GET', data: { id: options.id } })
      this.setData({ detail: detail || { items: [], diagnosis: [] } })
    } catch (e) {
      ui.error('详情加载失败')
    } finally {
      ui.hideLoading()
    }
  }
})
