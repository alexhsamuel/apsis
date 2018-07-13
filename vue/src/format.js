import moment from 'moment-timezone'

const TIME_FORMAT = 'YYYY-MM-DD HH:mm:ss'

export function formatTime(time, tz, format) {
  if (time)
    return moment(time).tz(tz).format(format || TIME_FORMAT)
  else
    return ''
}

export function formatElapsed(elapsed) {
  return (
      elapsed < 1e-5 ? (elapsed * 1e6).toPrecision(2) + ' µs'
    : elapsed < 1e-3 ? (elapsed * 1e6).toPrecision(3) + ' µs'
    : elapsed < 1e-2 ? (elapsed * 1e3).toPrecision(2) + ' ms'
    : elapsed < 1e+0 ? (elapsed * 1e3).toPrecision(3) + ' ms'
    : elapsed < 1e+1 ? (elapsed      ).toPrecision(2) + ' s'
    : elapsed < 60   ? (elapsed      ).toPrecision(3) + ' s'
    : elapsed < 3600 ? 
          Math.trunc(elapsed / 60) 
        + ':' + Math.trunc(elapsed % 60).padStart(2, '0')
    :     Math.trunc(elapsed / 3660) 
        + ':' + Math.trunc(elapsed / 60 % 60).padStart(2, '0')
        + ':' + Math.trunc(elapsed % 60).padStart(2, '0')
  )
}

