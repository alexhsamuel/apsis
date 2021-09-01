import { filter, map } from 'lodash'

/**
 * Matches an unambiguous prefix.
 * @param {string[]} vals - strings to match to
 * @param {string} str - string to match
 * @returns {string|null} the matched string, or null for no / ambiguous match
 */
export function prefixMatch(vals, str) {
  const matches = filter(vals, s => s.startsWith(str))
  return matches.length === 1 ? matches[0] : null
}

export function splitQuoted(str) {
  const results = str.match(/("[^"]+"|[^"\s]+)/g)
  return map(results, s => s.replace(/^"([^"]+)"$/, '$1'))
}

/**
 * Produces the conjunction predicate.
 * @param {Object[]} predicates - array of predicates of a single arg
 * @returns the combined predicate
 */
export function combine(predicates) {
  // The combined filter function is true if all the filters are.
  return x => {
    for (let i = 0; i < predicates.length; ++i)
      if (!predicates[i](x))
        return false
    return true
  }
}

