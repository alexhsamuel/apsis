import { toPairs } from 'lodash'

export function joinArgs(args) {
  return toPairs(args).map(([n, v]) => n + '=' + v).join(', ')
}

/**
 * Updates store `state` with runs from a socket `msg`.
 */
export function updateRuns(msg, state) {
  const runs = new Map(state.runs)
  let nadd = 0
  let nchg = 0
  let ndel = 0
  for (const runId in msg.runs) {
    const run = msg.runs[runId]
    if (!run.state) {
      runs.delete(runId)
      ndel++
    }
    else {
      if (runs.has(runId))
        nchg++
      else
        nadd++
      // Build an instance key for quick determination of reruns.
      run.instance_key = run.job_id + '\0' + Object.values(run.args).join('\0')
      // We never change the runs, so freeze them to avoid reactivity.
      runs.set(runId, Object.freeze(run))
    }
  }
  console.log('runs message:', nadd, 'add,', nchg, 'chg,', ndel, 'del')
  state.runs = runs
}

