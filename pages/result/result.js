// pages/result/result.js
// 结果页：展示最近一次巡检识别结果，并允许提交为正式巡检记录。
const { request } = require('../../api/index')
const ui = require('../../utils/ui')
const retest = require('../../utils/retest')

Page({
  data: { result: null, submitting: false },

  onShow() {
    const raw = wx.getStorageSync('BG_LAST_RESULT') || {}
    if (raw && raw.diagnosis) retest.upsertFromResult(raw)
    this.setData({ result: this.normalizeResult(raw) })
  },

  normalizeResult(raw) {
    const status = raw.status || raw.riskLevel || 'normal'
    const items = (raw.items || []).map((item) => ({
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
      confidence: typeof item.confidence === 'number' ? Math.round(item.confidence * 100) : '',
      recognitionSource: item.recognitionSource || raw.recognitionSource || '',
      reviewRequired: !!item.reviewRequired,
      statusText: item.status === 'unknown' || item.standardMatched === false ? '待配置' : (item.status === 'warning' || item.abnormal ? '异常' : '正常')
    }))
    const warning = String(status).toLowerCase() === 'warning' || items.some((item) => item.statusText === '异常')
    const diagnosis = (raw.diagnosis || []).map((item) => {
      if (typeof item === 'string') return { title: item, reason: '', advice: item, fieldAction: item, retestPlan: '', relatedItemNames: '', actionText: item }
      const normalized = {
        title: item.title || item.advice || '诊断建议',
        riskType: item.riskType || '',
        level: item.level || '',
        reason: item.reason || '',
        advice: item.advice || item.title || '',
        fieldAction: item.fieldAction || item.advice || '',
        retestPlan: item.retestPlan || '',
        relatedItemNames: item.relatedItemNames || ''
      }
      normalized.actionText = this.buildActionText(normalized)
      return normalized
    })
    return {
      ...raw,
      sampleType: raw.sampleType || 'boiler_water',
      sampleTypeName: raw.sampleTypeName || (raw.sampleType === 'combined' ? '软化水 + 炉水' : raw.sampleType === 'softened_water' ? '软化水' : '炉水'),
      items,
      diagnosis,
      summary: raw.summary || '',
      standardWarnings: raw.standardWarnings || [],
      sourceLabel: raw.recognitionSource === 'manual_gray' ? '人工读数（灰测）' : raw.recognitionSource === 'sample_fallback' ? '样例兜底' : '智能识别',
      riskLabel: warning ? '预警' : '正常',
      riskClass: warning ? 'tag-warn' : 'tag-normal'
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
    const item = this.data.result.diagnosis[index]
    if (!item || !item.actionText) return ui.error('暂无可复制内容')
    wx.setClipboardData({
      data: item.actionText,
      success: () => ui.success('已复制')
    })
  },

  async submitRecord() {
    if (this.data.submitting) return
    const inspectionId = wx.getStorageSync('BG_LAST_INSPECTION_ID')
    if (!inspectionId) return ui.error('缺少巡检ID')
    this.setData({ submitting: true })
    try {
      ui.showLoading('提交中')
      await request({ url: '/inspections/submit', method: 'POST', data: { inspectionId, remark: '小程序确认提交' } })
      ui.success('已提交巡检记录')
      setTimeout(() => wx.switchTab({ url: '/pages/records/records' }), 300)
    } catch (e) {
      ui.error(e.message || '提交失败')
    } finally {
      ui.hideLoading()
      this.setData({ submitting: false })
    }
  }
})
