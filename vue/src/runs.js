import { toPairs } from 'lodash'

export function joinArgs(args) {
  return toPairs(args).map(([n, v]) => n + '=' + v).join(', ')
}

/**
 * Updates store `state` with runs from a socket `msg`.
 */
export function updateRuns(msg, state) {
  const runs = Object.assign({}, state.runs)
  let nadd = 0
  let nchg = 0
  let ndel = 0
  for (const runId in msg.runs) {
    const run = msg.runs[runId]
    if (!run.state) {
      delete runs[runId]
      ndel++
    }
    else {
      if (runId in runs)
        nchg++
      else
        nadd++
      // We never change the runs, so freeze them to avoid reactivity.
      runs[runId] = Object.freeze(msg.runs[runId])
    }
  }
  console.log('runs message:', nadd, 'add,', nchg, 'chg,', ndel, 'del')
  state.runs = runs
}

