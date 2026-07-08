const mockUser = {
  id: 1,
  name: '张三',
  role: '巡检员',
  enterprise: { id: 101, name: '华能蒸汽示范工厂' }
}
const mockDashboard = {
  stats: [
    { label: '本月巡检', value: 18 },
    { label: '异常次数', value: 5 },
    { label: '锅炉数量', value: 2 },
    { label: '健康评分', value: 72 }
  ],
  alerts: [
    { id: 1, boilerName: '1号蒸汽锅炉', level: 'warning', text: 'pH偏低，建议2小时后复测' },
    { id: 2, boilerName: '2号蒸汽锅炉', level: 'normal', text: '当前状态正常' }
  ]
}
const mockBoilers = [
  { id: 1001, name: '1号蒸汽锅炉', code: 'GL-001', location: '动力车间', status: 'warning', pressure: '1.25MPa', evaporation: '4t/h' },
  { id: 1002, name: '2号蒸汽锅炉', code: 'GL-002', location: 'B区锅炉房', status: 'normal', pressure: '1.0MPa', evaporation: '2t/h' }
]
const mockMaterialPack = { id: 5001, code: 'BW-202607-000128', type: '基础版', expireAt: '2026-07-31' }
const mockResult = {
  riskLevel: 'warning',
  items: [
    { itemName: 'pH', value: '8.2', normalRange: '8.5-10.5', abnormal: true },
    { itemName: '磷酸根', value: '8', normalRange: '10-30 mg/L', abnormal: true },
    { itemName: '亚硫酸根', value: '18', normalRange: '10-30 mg/L', abnormal: false },
    { itemName: '总碱度', value: '22', normalRange: '6-26 mmol/L', abnormal: false },
    { itemName: '氯离子', value: '320', normalRange: '≤300 mg/L', abnormal: true },
    { itemName: '硬度', value: '0.05', normalRange: '≤0.03 mmol/L', abnormal: true }
  ],
  diagnosis: [
    { title: '结垢风险预警', reason: '硬度超标且磷酸根偏低，疑似软化器失效或加药不足', advice: '检查软化器、补加药剂，2小时后复测' }
  ]
}
const mockRecords = [
  { id: 8001, time: '2026-07-05 10:30', boilerName: '1号蒸汽锅炉', riskLevel: 'warning', summary: 'pH偏低，建议补加药剂' },
  { id: 8002, time: '2026-07-04 09:10', boilerName: '2号蒸汽锅炉', riskLevel: 'normal', summary: '检测正常' }
]
module.exports = { mockUser, mockDashboard, mockBoilers, mockMaterialPack, mockResult, mockRecords }
