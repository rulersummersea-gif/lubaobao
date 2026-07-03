const { createBoiler } = require('../../api/boiler')
const ui = require('../../utils/ui')

Page({
  data: {
    boilerTypes: ['蒸汽锅炉', '热水锅炉'],
    typeIndex: 0,
    form: {
      deviceCode: '',
      productNo: '',
      model: '',
      deviceType: '',
      ratedCapacity: '',
      ratedPressure: '',
      ratedSteamTemp: '',
      fuelType: '',
      efficiency: '',
      manufacturer: '',
      manufactureDate: '',
      licenseNo: ''
    }
  },
  onTypeChange(e) {
    const idx = Number(e.detail.value || 0)
    this.setData({ typeIndex: idx, 'form.deviceType': this.data.boilerTypes[idx] })
  },
  onInput(e) {
    const key = e.currentTarget.dataset.key
    this.setData({ [`form.${key}`]: e.detail.value })
  },
  validate(form) {
    const required = ['deviceCode','productNo','model','deviceType','ratedCapacity','ratedPressure','fuelType','manufacturer','manufactureDate','licenseNo']
    for (const k of required) {
      if (!String(form[k] || '').trim()) return false
    }
    return true
  },
  async submit() {
    const form = this.data.form
    if (!this.validate(form)) return ui.error('请先填写完整必填信息')
    try {
      ui.showLoading('提交中')
      const res = await createBoiler(form)
      ui.success('锅炉注册成功')
      wx.setStorageSync('BG_LAST_REGISTERED_BOILER', res || form)
      setTimeout(() => wx.navigateBack({ delta: 1 }), 300)
    } catch (e) {
      ui.error(e.message || '提交失败')
    } finally {
      ui.hideLoading()
    }
  }
})
