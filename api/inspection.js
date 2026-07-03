const { request } = require('./index')

function createInspection(data) {
  return request({ url: '/inspections/create', method: 'POST', data })
}

function recognizeInspection(data) {
  return request({ url: '/inspections/recognize', method: 'POST', data })
}

function getInspectionResult(inspectionId) {
  return request({ url: '/inspections/result', method: 'GET', data: { inspectionId } })
}

function submitInspection(data) {
  return request({ url: '/inspections/submit', method: 'POST', data })
}

function getRecords() {
  return request({ url: '/records' })
}

function getRecordDetail(id) {
  return request({ url: '/record-detail', method: 'GET', data: { id } })
}

module.exports = {
  createInspection,
  recognizeInspection,
  getInspectionResult,
  submitInspection,
  getRecords,
  getRecordDetail
}
