// pages/records/records.js
// 巡检记录列表页：展示历史记录，支持进入详情查看检测值和诊断建议。
const { getRecords } = require('../../api/inspection')
const { getState } = require('../../store/app-state')
const ui = require('../../utils/ui')

Page({
  data: { list: [] },

  async onShow() {
    try {
      ui.showLoading('加载记录')
      const state = getState()
      const boilerId = state.currentBoiler && state.currentBoiler.id
      const list = await getRecords({ status: 'submitted', ...(boilerId ? { boilerId } : {}) })
      this.setData({ list: (list || []).map(this.normalizeRecord) })
    } catch (e) {
      ui.error('记录加载失败')
    } finally {
      ui.hideLoading()
    }
  },

  normalizeRecord(item) {
    const result = item.result || {}
    const riskLevel = String(result.riskLevel || '').toLowerCase()
    const warning = ['warning', 'high', 'critical'].includes(riskLevel)
      || (result.items || []).some((row) => row.status === 'warning')
    return {
      id: item.inspectionId || item.id,
      boilerName: item.boilerName || `锅炉 #${item.boilerId || '-'}`,
      time: item.time || item.createdAt || '',
      inspectorName: item.inspectorName || '',
      sampleTypeName: result.sampleTypeName || item.sampleTypeName || (result.sampleType === 'combined' || item.sampleType === 'combined' ? '软化水 + 炉水' : result.sampleType === 'softened_water' || item.sampleType === 'softened_water' ? '软化水' : '炉水'),
      summary: result.summary || item.summary || `状态：${item.status || '-'}`,
      riskLabel: warning ? '预警' : '正常',
      riskClass: warning ? 'tag-warn' : 'tag-normal'
    }
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/record-detail/record-detail?id=' + e.currentTarget.dataset.id })
  }
})
