import { sortBy, toPairs } from 'lodash'

export function joinArgs(args) {
  return toPairs(args).map(([n, v]) => n + '=' + v).join(', ')
}

// FIXME: Merge with updateRuns.
export function updateJobs(msgs, state) {
  // Map is not reactive in Vue2, so we create a new map including the updates.

  let jobs = new Map(state.jobs)
  let nadd = 0
  let nchg = 0
  let ndel = 0

  for (const msg of msgs)
    if (msg.type === 'job') {
      const job = msg.job
      if (jobs.has(job.job_id))
        nchg++
      else
        nadd++
      jobs.set(job.job_id, Object.freeze(job))
    }

  console.log('jobs messages:', nadd, 'add,', nchg, 'chg,', ndel, 'del')
  // Set the new map to trigger reactivity updates.
  state.jobs = jobs
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

let nextSeq = 0

/**
 * Updates store `state` with runs from run summaries in `msgs`.
 */
export function updateRuns(msgs, state) {
  const seq = nextSeq++
  const runs = new Map(state.runs)
  let nadd = 0
  let nchg = 0
  let ndel = 0

  // Pre-sort by time, to keep future sorts quick.
  msgs = sortBy(msgs, m => m.run_summary && timeKey(m.run_summary))

  for (const msg of msgs)
    if (msg.type === 'run_summary') {
      let run = msg.run_summary
      // Add sort and group keys to runs in msg.
      run.group_key = groupKey(run)
      run.time_key = timeKey(run)
      run.seq = seq
      if (runs.has(run.run_id))
        nchg++
      else
        nadd++
      // Build an instance key for quick determination of reruns.
      // We never change the runs, so freeze them to avoid reactivity.
      runs.set(run.run_id, Object.freeze(run))
    }
    else if (msg.type === 'run_delete') {
      runs.delete(msg.run_id)
      ndel++
    }

  console.log('runs messages:', nadd, 'add,', nchg, 'chg,', ndel, 'del')
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

export const OPERATIONS = {
  'new'         : [],
  'scheduled'   : ['start', 'skip'],
  'waiting'     : ['start', 'skip'],
  'starting'    : [],
  'running'     : ['terminate', 'kill'],
  'success'     : ['rerun', 'mark failure', 'mark skipped', 'mark error'],
  'failure'     : ['rerun', 'mark success', 'mark skipped', 'mark error'],
  'skipped'     : ['rerun', 'mark success', 'mark failure', 'mark error'],
  'error'       : ['rerun', 'mark success', 'mark failure', 'mark skipped'],
}

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

