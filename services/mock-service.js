const { mockUser, mockBoilers, mockRecords, mockMaterialPack, mockResult, mockDashboard, mockRetestTasks } = require('../utils/mock')
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
  createBoiler(data) {
    return wait({ id: Date.now(), ...data })
  },
  verifyMaterialPack(code) {
    return wait({ valid: true, code: code || mockMaterialPack.code, pack: mockMaterialPack })
  },
  activateMaterialPack({ packId, boilerId }) {
    return wait({ success: true, packId, boilerId, status: 'activated' })
  },
  createInspection({ boilerId, materialPackId, inspectionType, retestTaskId }) {
    return wait({ inspectionId: Date.now(), boilerId, materialPackId, inspectionType, retestTaskId, status: 'pending_upload' })
  },
  recognizeInspection(data = {}) {
    if (data.values) {
      const result = JSON.parse(JSON.stringify(mockResult))
      result.recognitionSource = 'manual_gray'
      result.items = result.items.map((item) => {
        const map = { pH: 'ph', '磷酸根': 'phosphate', '亚硫酸根': 'sulfite', '总碱度': 'alkalinity', '氯离子': 'chloride', '硬度': 'hardness' }
        const code = map[item.itemName]
        return { ...item, value: data.values[code] || item.value, confidence: 1, recognitionSource: 'manual_gray', reviewRequired: false }
      })
      return wait(result)
    }
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
  getRetestTasks() {
    return wait(mockRetestTasks.filter(item => item.status !== 'done'))
  },
  completeRetestTask(url) {
    const id = String(url).split('/')[2]
    const task = mockRetestTasks.find(item => String(item.id) === id)
    if (task) task.status = 'done'
    return wait({ id, status: 'done' })
  },
  resolveRetestTask(url, data) {
    const id = String(url).split('/')[2]
    const task = mockRetestTasks.find(item => String(item.id) === id)
    if (task) {
      task.status = data.resolutionType === 'retest' ? 'retested' : data.resolutionType === 'no_retest' ? 'no_retest' : 'done'
      task.resolutionType = data.resolutionType
      task.resolutionNote = data.note || ''
    }
    return wait({ id, status: task ? task.status : 'done', resolutionType: data.resolutionType })
  },
  getReport() {
    return wait({ score: 72, abnormalCount: 5, inspectionCount: 18, suggestions: ['检查软化器再生', '补加药剂并2小时复测'] })
  }
}
