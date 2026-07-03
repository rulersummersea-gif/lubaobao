const { mockUser, mockBoilers, mockRecords, mockMaterialPack, mockResult, mockDashboard } = require('../utils/mock')
function wait(data, timeout = 150) {
  return new Promise(resolve => setTimeout(() => resolve(JSON.parse(JSON.stringify(data))), timeout))
}
module.exports = {
  login() {
    return wait({ token: 'mock-token', user: mockUser, enterprise: mockUser.enterprise })
  },
  getDashboard() {
    return wait(mockDashboard)
  },
  getBoilers() {
    return wait(mockBoilers)
  },
  verifyMaterialPack(code) {
    return wait({ valid: true, code: code || mockMaterialPack.code, pack: mockMaterialPack })
  },
  activateMaterialPack({ packId, boilerId }) {
    return wait({ success: true, packId, boilerId, status: 'activated' })
  },
  createInspection({ boilerId, materialPackId }) {
    return wait({ inspectionId: Date.now(), boilerId, materialPackId, status: 'pending_upload' })
  },
  recognizeInspection() {
    return wait(mockResult)
  },
  getInspectionResult() {
    return wait({ status: 'done', result: mockResult })
  },
  getRecords() {
    return wait(mockRecords)
  },
  getRecordDetail(id) {
    const item = mockRecords.find(i => String(i.id) === String(id)) || mockRecords[0]
    return wait({ ...item, imageUrl: '/images/mock-board.png', items: mockResult.items, diagnosis: mockResult.diagnosis })
  },
  submitInspection({ inspectionId, remark }) {
    return wait({ success: true, inspectionId, recordId: String(inspectionId), remark })
  },
  getReport() {
    return wait({ score: 72, abnormalCount: 5, inspectionCount: 18, suggestions: ['检查软化器再生', '补加药剂并2小时复测'] })
  }
}
