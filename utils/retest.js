// utils/retest.js
// 本地复测提醒：先让现场闭环跑顺，后续可升级为后端任务表。
const STORAGE_KEY = 'BG_RETEST_REMINDERS'

function nowText() {
  const date = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function readReminders() {
  return wx.getStorageSync(STORAGE_KEY) || []
}

function writeReminders(list) {
  wx.setStorageSync(STORAGE_KEY, list || [])
}

function buildActionText(item) {
  return [
    item.title,
    item.relatedItemNames ? `关联指标：${item.relatedItemNames}` : '',
    item.fieldAction ? `现场处置：${item.fieldAction}` : '',
    item.retestPlan ? `复测要求：${item.retestPlan}` : ''
  ].filter(Boolean).join('\n')
}

function buildRemindersFromResult(result) {
  const diagnosis = result && result.diagnosis ? result.diagnosis : []
  return diagnosis
    .filter((item) => item && item.retestPlan && item.riskCode !== 'normal')
    .map((item, index) => ({
      id: `${result.inspectionId || 'latest'}-${item.riskCode || index}`,
      inspectionId: result.inspectionId || '',
      boilerName: result.boilerName || '当前锅炉',
      title: item.title || '复测提醒',
      desc: item.retestPlan,
      action: item.fieldAction || item.advice || '',
      relatedItemNames: item.relatedItemNames || '',
      actionText: buildActionText(item),
      level: item.level === 'high' ? 'high' : 'warning',
      status: 'pending',
      createdAt: nowText()
    }))
}

function upsertFromResult(result) {
  const incoming = buildRemindersFromResult(result)
  if (!incoming.length) return readReminders()
  const current = readReminders()
  const next = current.slice()
  incoming.forEach((item) => {
    const index = next.findIndex((old) => old.id === item.id)
    if (index >= 0) next[index] = { ...next[index], ...item, status: next[index].status || 'pending' }
    else next.unshift(item)
  })
  writeReminders(next)
  return next
}

function getPendingReminders() {
  return readReminders().filter((item) => item.status !== 'done')
}

function completeReminder(id) {
  const next = readReminders().map((item) => (
    item.id === id ? { ...item, status: 'done', completedAt: nowText() } : item
  ))
  writeReminders(next)
  return next
}

module.exports = {
  readReminders,
  upsertFromResult,
  getPendingReminders,
  completeReminder
}
