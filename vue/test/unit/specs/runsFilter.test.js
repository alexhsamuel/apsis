import * as runsFilter from '@/runsFilter'

describe('JobIdPathPrefix', () => {
  test('matches exactly', () => {
    const pred = (new runsFilter.JobIdPathPrefix('foo/bar')).predicate
    const check = (job_id) => pred({job_id: job_id})
    expect(check('foo/bar')).toBeTruthy()
    expect(check('fox/bar')).toBeFalsy()
    expect(check('foo/barber')).toBeFalsy()
    expect(check('foo/baz')).toBeFalsy()
    expect(check('foo')).toBeFalsy()
  })

  test('matches path prefixes', () => {
    const pred = (new runsFilter.JobIdPathPrefix('foo/bar')).predicate
    const check = (job_id) => pred({job_id: job_id})
    expect(check('foo/bar/baz')).toBeTruthy()
    expect(check('foo/bar/bif')).toBeTruthy()
    expect(check('foo/box/baz')).toBeFalsy()
  })
})

