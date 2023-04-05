import { sortBy, toPairs } from 'lodash'

export function joinArgs(args) {
  return toPairs(args).map(([n, v]) => n + '=' + v).join(', ')
}

const RUN_STATE_GROUPS = {
  'new': 'S',  
  'scheduled': 'S',
  'waiting': 'R',
  'starting': 'R',
  'running': 'R',
  'success': 'C',
  'failure': 'C',
  'error': 'C',
  'skipped': 'C',
}

function groupKey(run) {
  const sgrp = RUN_STATE_GROUPS[run.state]
  return sgrp + (
    sgrp === 'R'
    // Waiting and running runs are never grouped.  
    ? run.run_id
    // Runs in other state are grouped by instance.
    : run.job_id + '\0' + Object.values(run.args).join('\0')
  )
}

/**
 * Returns the key by which runs are time-sorted.
 */
function timeKey(run) {
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

  let msgRuns = Object.values(msg.runs)
  // Pre-sort by time, to keep future sorts quick.
  msgRuns = sortBy(msgRuns, r => r.time_key)

  for (const run of msgRuns)
    if (!run.state) {
      runs.delete(run.run_id)
      ndel++
    }
    else {
      // Add sort and group keys to runs in msg.
      run.group_key = groupKey(run)
      run.time_key = timeKey(run)
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

export const STATES = [
  'new',
  'scheduled',
  'waiting',
  'starting',
  'running',
  'success',
  'failure',
  'skipped',
  'error',
]

export function sortStates(states) {
  return sortBy(states, s => STATES.indexOf(s))
}

/**
 * Converts a run args dict to an array of PARAM=VALUE strings.
 */
export function argsToArray(args) {
  return Object.entries(args).map(([param, val]) => param + '=' + val)
}

/**
 * Converts an array of PARAM=VALUE strings to an args dict.
 */
export function arrayToArgs(arr) {
  const args = {}
  for (const el of arr) {
    const i = el.indexOf('=')
    if (i === -1)
      args[el] = null
    else
      args[el.slice(0, i)] = el.slice(i + 1)
  }
  return args
}

/**
 * Returns true if each member of `keywords` is a substring of `string`.
 */
export function matchKeywords(keywords, string) {
  for (const keyword of keywords)
    if (string.indexOf(keyword) === -1)
      return false
  return true
}

/**
 * Returns true if each members of `arr0` is in `arr1`.
 */
export function includesAll(arr0, arr1) {
  for (const el of arr0)
    if (!arr1.includes(el))
      return false
  return true
}

