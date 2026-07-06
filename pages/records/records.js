// pages/records/records.js
// 巡检记录列表页：展示历史记录，支持进入详情查看检测值和诊断建议。
const { getRecords } = require('../../api/inspection')
const ui = require('../../utils/ui')

Page({
  data: { list: [] },

  async onShow() {
    try {
      ui.showLoading('加载记录')
      const list = await getRecords()
      this.setData({ list: (list || []).map(this.normalizeRecord) })
    } catch (e) {
      ui.error('记录加载失败')
    } finally {
      ui.hideLoading()
    }
  },

  normalizeRecord(item) {
    const result = item.result || {}
    const status = result.status || item.status || 'normal'
    const warning = String(status).toLowerCase() === 'warning' || (result.summary || '').indexOf('偏') >= 0
    return {
      id: item.inspectionId || item.id,
      boilerName: item.boilerName || `锅炉 #${item.boilerId || '-'}`,
      time: item.time || item.createdAt || '',
      summary: result.summary || item.summary || `状态：${item.status || '-'}`,
      riskLabel: warning ? '预警' : '正常',
      riskClass: warning ? 'tag-warn' : 'tag-normal'
    }
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/record-detail/record-detail?id=' + e.currentTarget.dataset.id })
  }
})
