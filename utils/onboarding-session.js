const { getOnboardingStatus } = require('../api/auth')
const { getLastBoiler, getState, saveLastBoiler, setState } = require('../store/app-state')

async function refreshOnboardingState() {
  const state = getState()
  if (!state.token) return state

  const onboarding = await getOnboardingStatus()
  const binding = onboarding && onboarding.binding
  const serverBoiler = onboarding && onboarding.currentBoiler
    ? onboarding.currentBoiler
    : binding && binding.boilerId
    ? {
        id: binding.boilerId,
        name: binding.boilerName || `锅炉 #${binding.boilerId}`,
        enterpriseId: binding.enterpriseId
      }
    : null
  const savedBoiler = getLastBoiler(state.user && state.user.id)
  const preferredBoiler = savedBoiler || state.currentBoiler || null
  const sameEnterprise = preferredBoiler && serverBoiler && (
    !preferredBoiler.enterpriseId
    || !serverBoiler.enterpriseId
    || Number(preferredBoiler.enterpriseId) === Number(serverBoiler.enterpriseId)
  )
  const currentBoiler = onboarding && onboarding.required
    ? null
    : serverBoiler || (sameEnterprise ? preferredBoiler : null)
  if (currentBoiler) saveLastBoiler(state.user && state.user.id, currentBoiler)
  const next = setState({ onboarding, currentBoiler })
  const app = getApp()
  app.globalData.currentBoiler = currentBoiler
  return next
}

module.exports = { refreshOnboardingState }
