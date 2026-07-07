// pages/result/result.js
// 结果页：展示最近一次巡检识别结果，并允许提交为正式巡检记录。
const { request } = require('../../api/index')
const ui = require('../../utils/ui')

Page({
  data: { result: null, submitting: false },

  onShow() {
    this.setData({ result: this.normalizeResult(wx.getStorageSync('BG_LAST_RESULT') || {}) })
  },

  normalizeResult(raw) {
    const status = raw.status || raw.riskLevel || 'normal'
    const items = (raw.items || []).map((item) => ({
      name: item.name || item.itemName || '-',
      value: item.value || '-',
      normalRange: item.normalRange || '',
      statusText: item.status === 'warning' || item.abnormal ? '异常' : '正常'
    }))
    const warning = String(status).toLowerCase() === 'warning' || items.some((item) => item.statusText === '异常')
    const diagnosis = (raw.diagnosis || []).map((item) => {
      if (typeof item === 'string') return { title: item, reason: '', advice: item }
      return {
        title: item.title || item.advice || '诊断建议',
        reason: item.reason || '',
        advice: item.advice || item.title || ''
      }
    })
    return {
      ...raw,
      items,
      diagnosis,
      summary: raw.summary || '',
      riskLabel: warning ? '预警' : '正常',
      riskClass: warning ? 'tag-warn' : 'tag-normal'
    }
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
