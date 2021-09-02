import { filter, includes, join, map, some } from 'lodash'
import { prefixMatch, splitQuoted, combine } from '@/parse.js'
import { parseTimeOrOffset } from '@/time.js'
import store from '@/store'

const STATES = [
  'new', 
  'scheduled', 
  'running',
  'success',
  'failure',
  'error',
]

export class StateTerm {
  constructor(states) {
    if (typeof states === 'string') {
      const matchState = s => prefixMatch(STATES, s)
      this.states = filter(map(states.split(','), matchState))
    }
    else
      this.states = states
  }

  toString() {
    return 'state:' + join(this.states, ',')
  }

  get predicate() {
    return run => includes(this.states, run.state)
  }

  static get(query) {
    const terms = filter(map(splitQuoted(query), parse), t => t instanceof StateTerm)
    return terms.length === 0 ? [] : terms[0].states
  }
  
  static set(query, states) {
    return replace(query, StateTerm, states.length > 0 ? new StateTerm(states) : null)
  }
}

// -----------------------------------------------------------------------------

class ArgTerm {
  constructor(arg, val) {
    this.arg = arg
    this.val = val
  }

  toString() {
    return this.arg + '=' + this.val
  }

  get predicate() {
    return run => {
      const str = run.args[this.arg]
      return str !== undefined && str.indexOf(this.val) >= 0
    }
  }
}

// -----------------------------------------------------------------------------

class JobIdTerm {
  constructor(str) {
    this.str = str
  }

  toString() {
    return this.str
  }

  get predicate() {
    return run => run.job_id.indexOf(this.str) >= 0
  }
}

// -----------------------------------------------------------------------------

class LabelTerm {
  constructor(labels) {
    if (typeof labels === 'string')
      this.labels = labels.split(',')
    else
      this.labels = labels
  }

  toString() {
    return 'labels:' + join(this.labels, ',')
  }

  get predicate() {
    return run => some(map(run.labels, l => this.labels.includes(l)))
  }

  static get(query) {
    const terms = filter(map(splitQuoted(query), parse), t => t instanceof LabelTerm)
    return terms.length === 0 ? [] : terms[0].labels
  }
  
  static set(query, labels) {
    return replace(query, LabelTerm, labels.length > 0 ? new LabelTerm(labels) : null)
  }
}

// -----------------------------------------------------------------------------

export class SinceTerm {
  constructor(str) {
    this.str = str
  }

  toString() {
    return 'since:' + this.str
  }

  get predicate() {
    const date = parseTimeOrOffset(this.str, false, store.state.timeZone)
    return (
      date === null ? run => false
      : run => run.time_range && new Date(run.time_range[1]) >= date
    )
  }

  static get(query) {
    const terms = filter(map(splitQuoted(query), parse), t => t instanceof SinceTerm)
    return terms.length === 0 ? '' : terms[0].str
  }
  
  static set(query, str) {
    return replace(query, SinceTerm, str ? new SinceTerm(str) : null)
  }
}

// -----------------------------------------------------------------------------

function parse(part) {
  const clx = part.indexOf(':')
  const eqx = part.indexOf('=')
  if (clx !== -1 && (eqx === -1 || clx < eqx)) {
    // Found a "tag:val".
    const tag = part.substr(0, clx)
    const val = part.substr(clx + 1)
    if (tag === 'state' || tag === 'states')
      return new StateTerm(val)
    else if (tag === 'since')
      return new SinceTerm(val)
    else if (tag === 'label')
      return new LabelTerm(val)
    else
      return null  // FIXME
  }
  else if (eqx !== -1 && (clx === -1 || eqx < clx)) {
    // Found a 'arg=val'.  Match on arg values.
    const arg = part.substr(0, eqx)
    const val = part.substr(eqx + 1)
    return new ArgTerm(arg, val)
  }
  else
    // Just a keyword.  Search in job id.
    return new JobIdTerm(part)
}

export function makePredicate(str) {
  const terms = map(splitQuoted(str), parse)
  return combine(map(filter(terms), t => t.predicate))
}

/**
 * Replaces all terms of `type` in `query` with `value`.
 * @param {string} query 
 * @param {*} type - term type to replace
 * @param {*} term - replacement term or null to remove
 */
export function replace(query, type, replacement) {
  const terms = map(splitQuoted(query), parse)
  let found = false
  for (let i = 0; i < terms.length; ++i) {
    const term = terms[i]
    if (term instanceof type) {
      if (found || !replacement)
        // Remove it.
        terms.splice(i--, 1)
      else
        // Replace it.
        terms.splice(i, 1, replacement)
      found = true
    }
  }
  if (!found && replacement)
    terms.push(replacement)
  return terms.join(' ')
}

