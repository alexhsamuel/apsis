import { each, every, filter, map, some, trim, values } from 'lodash'

// Returns the filter function for jobs and args.
//
// The filter string is made of terms.  Each is
// either just a value, which is matched against all
// argument values, or a key=value pair.  All terms must
// match.
//
// For example, "foo bar=baz bif=" matches if any job ID
// contains 'foo', the value of bar contains 'baz', and any
// argument bif is defined.
export function makeJobPredicate(jobFilter) {
  const parts = filter(map(jobFilter.split(' '), trim))
  if (parts.length === 0)
    return r => true

  // Construct an array of predicates over runs, one for each term.
  const filters = map(parts, p => {
    const i = p.indexOf('=')
    if (i === -1)
      // Substring search of job IDs.
      return run => run.job_id.indexOf(p) >= 0
    else {
      // Substrings search of values of the named arg.
      const name = p.substr(0, i)
      const value = p.substr(i + 1)
      const find = s => s !== undefined && s.indexOf(value) >= 0
      return run => find(run.args[name])
    }
  })

  // The combined filter function is true if all the filters are.
  return run => every(map(filters, f => f(run)))
}

export function makeStatePredicate(stateFilter) {
  if (stateFilter.length === 0)
    return run => true
  else
    return run => some(map(stateFilter, s => run.state === s))
}

// Organizes runs by rerun group.
export function groupReruns(runs) {
  // Collect reruns of the same run into an object keyed by run ID.
  // FIXME: Use _.groupBy.
  let reruns = {}
  each(values(runs), r => {
    if (r.rerun)
      (reruns[r.rerun] || (reruns[r.rerun] = [])).push(r)
    else 
      // FIXME: Do we need this?
      (reruns[r.run_id] || (reruns[r.run_id] = [])).splice(0, 0, r)
  })
  return values(reruns)
}
