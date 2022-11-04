/**
 * Apsis API client
 */

function getUrl() {
  return ['', 'api', 'v1'].concat(Array.from(arguments)).join('/')
}

export function getCancelUrl(run_id) {
  return getUrl('runs', run_id, 'cancel')
}

export function getMarkUrl(run_id, state) {
  return getUrl('runs', run_id, 'mark', state)
}

export function getOutputDataUrl(run_id, output_id) {
  return getUrl('runs', run_id, 'output', output_id)
}

export function getOutputUrl(run_id) {
  return getUrl('runs', run_id, 'outputs')
}

export function getRerunUrl(run_id) {
  return getUrl('runs', run_id, 'rerun')
}

export function getRunUrl(run_id) {
  return getUrl('runs', run_id)
}

export function getSignalUrl(run_id, signame) {
  return getUrl('runs', run_id, 'signal', signame)
}

export function getSkipUrl(run_id) {
  return getUrl('runs', run_id, 'skip')
}

export function getStartUrl(run_id) {
  return getUrl('runs', run_id, 'start')
}

export function getUrlForOperation(operation, run_id) {
  switch (operation) {
    case 'cancel': return getCancelUrl(run_id)
    case 'skip': return getSkipUrl(run_id)
    case 'start': return getStartUrl(run_id)
    case 'rerun': return getRerunUrl(run_id)
    case 'terminate': return getSignalUrl(run_id, 'SIGTERM')
    case 'kill': return getSignalUrl(run_id, 'SIGKILL')
    default:
      if (operation.startsWith('mark ')) return getMarkUrl(run_id, operation.substring(5))
  }
  console.error('unknown operation:', operation)
  return ''
}
