const config = require('../config/index')
const { request } = require('./index')

function getBoilers(params = {}) {
  const url = config.useMock ? '/boilers' : '/boilers'
  return request({ url, method: 'GET', data: params })
}

function createBoiler(data) {
  const url = config.useMock ? '/boilers/create' : '/boilers'
  // real: 后端建议字段使用 snake_case
  const payload = config.useMock ? data : {
    enterpriseId: data.enterpriseId,
    deviceCode: data.deviceCode,
    productNo: data.productNo,
    model: data.model,
    deviceType: data.deviceType,
    ratedCapacity: data.ratedCapacity,
    ratedPressure: data.ratedPressure,
    ratedSteamTemp: data.ratedSteamTemp,
    fuelType: data.fuelType,
    efficiency: data.efficiency,
    manufacturer: data.manufacturer,
    manufactureDate: data.manufactureDate,
    licenseNo: data.licenseNo
  }
  return request({ url, method: 'POST', data: payload })
}

module.exports = { getBoilers, createBoiler }
