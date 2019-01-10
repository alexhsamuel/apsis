import { filter, includes, join, map } from 'lodash'

/**
 * Matches an unambiguous prefix.
 * @param {string[]} vals - strings to match to
 * @param {string} str - string to match
 * @returns {string|null} the matched string, or null for no / ambiguous match
 */
function prefixMatch(vals, str) {
  const matches = filter(vals, s => s.startsWith(str))
  return matches.length === 1 ? matches[0] : null
}

export function splitQuoted(str) {
  const results = str.match(/("[^"]+"|[^"\s]+)/g)
  return map(results, s => s.replace(/^"([^"]+)"$/, '$1'))
}

// --------

const STATES = [
  'new', 
  'scheduled', 
  'running',
  'success',
  'failure',
  'error',
]

class StateTerm {
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
}


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


class JobNameTerm {
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


// --------

/**
 * Produces the conjunction predicate.
 * @param {Object[]} predicates
 * @returns the combined predicate
 */
function combine(predicates) {
  // The combined filter function is true if all the filters are.
  return x => {
    for (let i = 0; i < predicates.length; ++i)
      if (!predicates[i](x))
        return false
    return true
  }
}

function parse(part) {
  const clx = part.indexOf(':')
  const eqx = part.indexOf('=')
  if (clx !== -1 && (eqx === -1 || clx < eqx)) {
    // Found a "tag:val".
    const tag = part.substr(0, clx)
    const val = part.substr(clx + 1)
    if (tag === 'state' || tag === 'states')
      return new StateTerm(val)
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
    return new JobNameTerm(part)
}

export function makePredicate(str) {
  const terms = map(splitQuoted(str), parse)
  return combine(map(filter(terms), t => t.predicate))
}

export function getStates(query) {
  const terms = filter(map(splitQuoted(query), parse), t => t instanceof StateTerm)
  if (terms.length === 0)
    return []
  else
    return terms[0].states
}

/**
 * 
 * @param {*} query 
 * @param {*} states 
 */
export function setStates(query, states) {
  const terms = map(splitQuoted(query), parse)
  let found = 0
  for (let i = 0; i < terms.length; ++i) {
    const term = terms[i]
    if (term instanceof StateTerm)
      if (found === 0 && states.length > 0) {
        // Update it with new states.
        term.states = states
        found = 1
      }
      else
        // Remove it.
        terms.splice(i--, 1)
  }
  if (found === 0 && states.length > 0)
    terms.push(new StateTerm(states))
  return terms.join(' ')
}
