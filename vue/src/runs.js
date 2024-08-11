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

let nextSeq = 0

/**
 * Updates store `state` with runs from run summaries in `msgs`.
 */
export function processMsgs(msgs, state) {
  const seq = nextSeq++

  const runs = new Map(state.runs)
  const jobs = new Map(state.jobs)

  let runStats = {add: 0, chg: 0, del: 0}
  let jobStats = {add: 0, chg: 0, del: 0}

  // Pre-sort by time, to keep future sorts quick.
  msgs = sortBy(msgs, m => m.run_summary && timeKey(m.run_summary))

  for (const msg of msgs)
    // Treat new and changed jobs the same.
    if (msg.type === 'job' || msg.type === 'job_add') {
      const job = msg.job
      if (jobs.has(job.job_id))
        jobStats.chg++
      else
        jobStats.add++
      jobs.set(job.job_id, Object.freeze(job))
    }
    else if (msg.type === 'job_delete') {
      jobs.delete(msg.job_id)
      jobStats.del++
    }
    else if (msg.type === 'run_summary') {
      let run = msg.run_summary
      // Add sort and group keys to runs in msg.
      run.group_key = groupKey(run)
      run.time_key = timeKey(run)
      run.seq = seq
      if (runs.has(run.run_id))
        runStats.chg++
      else
        runStats.add++
      // Build an instance key for quick determination of reruns.
      // We never change the runs, so freeze them to avoid reactivity.
      runs.set(run.run_id, Object.freeze(run))
    }
    else if (msg.type === 'run_delete') {
      runs.delete(msg.run_id)
      runStats.del++
    }

  if (runStats.add > 0 || runStats.chg > 0 || runStats.del > 0) {
    console.log(
      'runs messages:',
      runStats.add, 'add,', runStats.chg, 'chg,', runStats.del, 'del'
    )
    // Set the new map to trigger reactivity updates.
    state.runs = runs
  }

  if (jobStats.add > 0 || jobStats.chg > 0 || jobStats.del > 0) {
      console.log(
        'jobs messages:',
        jobStats.add, 'add,', jobStats.chg, 'chg,', jobStats.del, 'del')
    // Set the new map to trigger reactivity updates.
    state.jobs = jobs
  }
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

