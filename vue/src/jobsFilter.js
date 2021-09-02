import { filter, join, map, some } from 'lodash'
import { splitQuoted, combine } from '@/parse.js'
import * as runsFilter from '@/runsFilter.js'

// -----------------------------------------------------------------------------

export class JobIdTerm {
  constructor(str) {
    this.str = str
  }

  toString() {
    return this.str
  }

  get predicate() {
    // Match substring.
    return job => job.job_id.indexOf(this.str) >= 0
  }
}

// -----------------------------------------------------------------------------

export class LabelTerm {
  constructor(labels) {
    if (typeof labels === 'string')
      this.labels = labels.split(',')
    else
      this.labels = labels
  }

  toString() {
    return 'label:' + join(this.labels, ',')
  }

  get predicate() {
    return job => some(map(job.metadata.labels || [], l => this.labels.includes(l)))
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

function parse(part) {
  const clx = part.indexOf(':')
  const eqx = part.indexOf('=')
  if (clx !== -1 && (eqx === -1 || clx < eqx)) {
    // Found a "tag:val".
    const tag = part.substr(0, clx)
    const val = part.substr(clx + 1)
    if (tag === 'label')
      return new LabelTerm(val)
    else
      return null  // FIXME
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
 * @param {string} query - user query string
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

/**
 * Converts a (jobs) query to a runs query.
 * @param {*} query 
 * @returns the correpsonding runs query
 */
export function toRunsQuery(query) {
  function convert(term) {
    if (term instanceof JobIdTerm)
      return new runsFilter.JobIdTerm(term.str)
    else if (term instanceof LabelTerm)
      return new runsFilter.LabelTerm(term.labels)
    else
      // Ignore anything else.
      return null
  }

  // Parse into terms.
  const terms = map(splitQuoted(query), parse)
  // Convert terms to run query terms and reassemble into a query.
  return filter(map(terms, convert)).join(' ')
}

