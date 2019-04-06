import moment from 'moment-timezone'

const TIME_FORMAT = 'YYYY-MM-DD HH:mm:ss'

export function formatTime(time, tz, format) {
  if (time)
    return moment(time).tz(tz).format(format || TIME_FORMAT)
  else
    return ''
}

export function formatDuration(elapsed) {
  return (
      elapsed < 0 ? '??'
    : elapsed < 1e-5 ? (elapsed * 1e6).toPrecision(2) + ' µs'
    : elapsed < 1e-3 ? (elapsed * 1e6).toPrecision(3) + ' µs'
    : elapsed < 1e-2 ? (elapsed * 1e3).toPrecision(2) + ' ms'
    : elapsed < 1e+0 ? (elapsed * 1e3).toPrecision(3) + ' ms'
    : elapsed < 1e+1 ? (elapsed      ).toPrecision(2) + ' s'
    : elapsed < 60   ? (elapsed      ).toPrecision(3) + ' s'
    : elapsed < 3600 ? 
          Math.trunc(elapsed / 60) 
        + ':' + ('' + Math.trunc(elapsed % 60)).padStart(2, '0')
    :     Math.trunc(elapsed / 3660) 
        + ':' + ('' + Math.trunc(elapsed / 60 % 60)).padStart(2, '0')
        + ':' + ('' + Math.trunc(elapsed % 60)).padStart(2, '0')
  )
}

export function formatElapsed(elapsed) {
  return (
      elapsed < 3600 ? 
          Math.trunc(elapsed / 60) 
        + ':' + ('' + Math.trunc(elapsed % 60)).padStart(2, '0')
    :     Math.trunc(elapsed / 3660) 
        + ':' + ('' + Math.trunc(elapsed / 60 % 60)).padStart(2, '0')
        + ':' + ('' + Math.trunc(elapsed % 60)).padStart(2, '0')
  )
}

export function parseDate(str, timeZone) {
  str = str.trim()

  if (str === 'today' || str === 'yesterday' || str === 'tomorrow') {
    let now = moment().tz(timeZone)
    if (str === 'yesterday')
      now.add(-1, 'day')
    if (str === 'tomorrow')
      now.add(1, 'day')
    return [now.year(), now.month(), now.date()]
  }

  let match = str.match(/^(\d\d\d\d)-(\d\d)-(\d\d)$/)
  if (match !== null)
    return [parseInt(match[1]), parseInt(match[2]) - 1, parseInt(match[3])]

  match = str.match(/^(\d\d\d\d)(\d\d)(\d\d)$/)
  if (match !== null)
    return [parseInt(match[1]), parseInt(match[2]) - 1, parseInt(match[3])]

  return null
}

export function parseDaytime(str) {
  str = str.trim()

  let match = str.match(/^(\d\d?):(\d\d)(?::(\d\d))?$/)
  if (match === null)
    match = str.match(/^(\d\d?)(\d\d)(?:(\d\d))?$/)
  if (match !== null) {
    const h = parseInt(match[1])
    const m = parseInt(match[2])
    const s = match[3] === undefined ? 0 : parseInt(match[3])
    return [h, m, s]
  }

  return null
}

export function parseTime(str, end, timeZone) {
  const parts = str.trim().split(/ +/)

  if (parts.length === 0 || parts.length > 2)
    return null

  let date = parseDate(parts[0], timeZone)
  if (date === null) 
    return null

  if (parts.length === 2) {
    const daytime = parseDaytime(parts[1])
    return daytime === null ? null : moment.tz(date.concat(daytime), timeZone)
  }
  else {
    date = moment.tz(date, timeZone)
    if (end)
      date.add(1, 'days')
    return date
  }
}

/**
 * Parses a time offset and applies it to time.
 * 
 * Understands,
 * - "#d" where # is a number of days.
 * 
 * @param {} str - string to parse
 * @param {*} sign - sign for date offset
 * @param {*} time - time to offset from or now if null
 */
export function parseTimeOffset(str, sign, time) {
  if (!time)
    time = new Date()
  const match = str.match(/^(\d+)(d)$/)
  if (match !== null) {
    if (match[2] === 'd')
      time.setDate(time.getDate() + sign * parseInt(match[1]))
    return time
  }
  return null
}

export function parseTimeOrOffset(str, end, timeZone) {
  let time = parseTime(str, end, timeZone)
  if (time === null)
    time = parseTimeOffset(str, end ? 1 : -1)
  return time
}

