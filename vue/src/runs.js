import { sortBy, toPairs } from 'lodash'

export function joinArgs(args) {
  return toPairs(args).map(([n, v]) => n + '=' + v).join(', ')
}

/**
 * Returns the key by which runs are time-sorted.
 */
export function sortTime(run) {
  return run.times.schedule || run.times.running || run.times.error
}

/**
 * Updates store `state` with runs from a socket `msg`.
 */
export function updateRuns(msg, state) {
  const runs = new Map(state.runs)
  let nadd = 0
  let nchg = 0
  let ndel = 0

  // Add keys to runs in msg.
  let msgRuns = Object.values(msg.runs)
  msgRuns.forEach(run => {
    run.instance_key = run.job_id + '\0' + Object.values(run.args).join('\0')
    run.time_key = sortTime(run)
  })

  // Pre-sort by time, to keep future sorts quick.
  msgRuns = sortBy(msgRuns, r => r.time_key)

  for (const run of msgRuns)
    if (!run.state) {
      runs.delete(run.run_id)
      ndel++
    }
    else {
      if (runs.has(run.run_id))
        nchg++
      else
        nadd++
      // Build an instance key for quick determination of reruns.
      // We never change the runs, so freeze them to avoid reactivity.
      runs.set(run.run_id, Object.freeze(run))
    }

  console.log('runs message:', nadd, 'add,', nchg, 'chg,', ndel, 'del')
  state.runs = runs
}

