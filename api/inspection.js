const config = require('../config/index')
const { request, uploadInspectionImage } = require('./index')

function createInspection(data) {
  const url = config.useMock ? '/inspections/create' : '/inspections'
  return request({ url, method: 'POST', data })
}

function uploadImage(filePath, inspectionId) {
  return uploadInspectionImage(filePath, inspectionId)
}

function recognizeInspection(data) {
  const url = config.useMock ? '/inspections/recognize' : `/inspections/${data.inspectionId}/recognize`
  return request({ url, method: 'POST', data })
}

function getInspectionResult(inspectionId) {
  const url = config.useMock ? '/inspections/result' : `/inspections/${inspectionId}/result`
  const method = 'GET'
  const data = config.useMock ? { inspectionId } : {}
  return request({ url, method, data })
}

function submitInspection(data) {
  const url = config.useMock ? '/inspections/submit' : '/inspections/submit'
  return request({ url, method: 'POST', data })
}

function getRecords(params = {}) {
  const url = config.useMock ? '/records' : '/inspections/records'
  return request({ url, method: 'GET', data: params })
}

function getRecordDetail(id) {
  const url = config.useMock ? '/record-detail' : `/inspections/records/${id}`
  const method = 'GET'
  const data = config.useMock ? { id } : {}
  return request({ url, method, data })
}

module.exports = {
  createInspection,
  uploadImage,
  recognizeInspection,
  getInspectionResult,
  submitInspection,
  getRecords,
  getRecordDetail
}
