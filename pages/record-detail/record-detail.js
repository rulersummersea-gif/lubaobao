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
      ratedPressureMpa: raw.ratedPressureMpa || '',
      standardWarnings: raw.standardWarnings || [],
      items: (raw.items || []).map((item) => ({
        name: item.name || item.itemName || '-',
        value: `${item.value || '-'}${item.unit ? ' ' + item.unit : ''}`,
        method: item.method || '',
        normalRange: item.normalRange || '',
        standardSource: item.standardSource || '',
        standardNote: item.standardNote || '',
        pressureSegment: item.pressureSegment || '',
        ratedPressureMpa: item.ratedPressureMpa || '',
        standardMatched: item.standardMatched !== false,
        meaning: item.meaning || '',
        maintenance: item.maintenance || '',
        priority: item.priority || '',
        statusText: item.status === 'unknown' || item.standardMatched === false ? '待配置' : (item.status === 'warning' || item.abnormal ? '异常' : '正常')
      })),
      diagnosis: (raw.diagnosis || []).map((item) => {
        if (typeof item === 'string') return { title: item, riskType: '', reason: '', advice: item, fieldAction: item, retestPlan: '', relatedItemNames: '', actionText: item }
        const normalized = {
          title: item.title || '诊断建议',
          riskType: item.riskType || '',
          reason: item.reason || '',
          advice: item.advice || item.title || '',
          fieldAction: item.fieldAction || item.advice || '',
          retestPlan: item.retestPlan || '',
          relatedItemNames: item.relatedItemNames || ''
        }
        normalized.actionText = this.buildActionText(normalized)
        return normalized
      })
    }
  },

  buildActionText(item) {
    return [
      item.title,
      item.relatedItemNames ? `关联指标：${item.relatedItemNames}` : '',
      item.fieldAction ? `现场处置：${item.fieldAction}` : '',
      item.retestPlan ? `复测要求：${item.retestPlan}` : ''
    ].filter(Boolean).join('\n')
  },

  copyAction(e) {
    const index = Number(e.currentTarget.dataset.index)
    const item = this.data.detail.diagnosis[index]
    if (!item || !item.actionText) return ui.error('暂无可复制内容')
    wx.setClipboardData({
      data: item.actionText,
      success: () => ui.success('已复制')
    })
  }
})
