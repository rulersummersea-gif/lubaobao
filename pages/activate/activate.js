// pages/activate/activate.js
// 材料包激活页：先校验材料包，再绑定当前锅炉完成激活。
const { request } = require('../../api/index')
const { getState } = require('../../store/app-state')
const ui = require('../../utils/ui')

Page({
  data: { code: 'BW-202607-000128', pack: null, submitting: false },

  onInput(e) { this.setData({ code: e.detail.value }) },

  async verifyPack() {
    try {
      ui.showLoading('校验中')
      const res = await request({ url: '/material-packs/verify', method: 'POST', data: { code: this.data.code } })
      this.setData({ pack: res.pack })
      ui.success('校验成功')
    } catch (e) {
      ui.error('校验失败')
    } finally {
      ui.hideLoading()
    }
  },

  async activatePack() {
    if (this.data.submitting) return
    const state = getState()
    const currentBoiler = state.currentBoiler
    if (!this.data.pack) return ui.error('请先校验材料包')
    if (!currentBoiler) return ui.error('请先选择锅炉')
    this.setData({ submitting: true })
    try {
      ui.showLoading('激活中')
      await request({
        url: '/material-packs/activate',
        method: 'POST',
        data: { packId: this.data.pack.id, boilerId: currentBoiler.id, enterpriseId: state.enterprise.id }
      })
      ui.success('激活成功')
    } catch (e) {
      ui.error('激活失败')
    } finally {
      ui.hideLoading()
      this.setData({ submitting: false })
    }
  }
})
