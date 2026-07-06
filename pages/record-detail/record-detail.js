// pages/record-detail/record-detail.js
// 记录详情页：展示单次巡检的完整内容，包括结果明细、诊断建议和备注。
const { getInspectionResult } = require('../../api/inspection')
const ui = require('../../utils/ui')

Page({
  data: { detail: { items: [], diagnosis: [] } },

  async onLoad(options) {
    try {
      ui.showLoading('加载详情')
      const detail = await getInspectionResult(options.id)
      this.setData({ detail: this.normalizeDetail(detail || {}, options.id) })
    } catch (e) {
      ui.error('详情加载失败')
    } finally {
      ui.hideLoading()
    }
  },

  normalizeDetail(raw, id) {
    return {
      id,
      boilerName: raw.boilerName || `巡检记录 #${id}`,
      time: raw.time || '',
      summary: raw.summary || '',
      items: (raw.items || []).map((item) => ({
        name: item.name || item.itemName || '-',
        value: item.value || '-',
        statusText: item.status === 'warning' || item.abnormal ? '异常' : '正常'
      })),
      diagnosis: (raw.diagnosis || []).map((item) => {
        if (typeof item === 'string') return { title: item, advice: item }
        return { title: item.title || '诊断建议', advice: item.advice || item.title || '' }
      })
    }
  }
})
