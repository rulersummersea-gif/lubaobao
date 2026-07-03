const config = require('../config/index')
const { request } = require('./index')

function getMonthlyReport(params = {}) {
  const url = config.useMock ? '/report' : '/reports/monthly'
  return request({ url, method: 'GET', data: params })
}

module.exports = { getMonthlyReport }
