/**
 * Apsis API client
 */

function getUrl() {
  return ['', 'api', 'v1'].concat(Array.from(arguments)).join('/')
}

export function getMarkUrl(run, state) {
  return getUrl('runs', run.run_id, 'mark', state)
}

export function getOutputDataUrl(run, output_id) {
  return getUrl('runs', run.run_id, 'output', output_id)
}

export function getOutputUrl(run) {
  return getUrl('runs', run.run_id, 'outputs')
}

export function getRerunUrl(run) {
  return getUrl('runs', run.run_id, 'rerun')
}

export function getRunUrl(run_id) {
  return getUrl('runs', run_id)
}

