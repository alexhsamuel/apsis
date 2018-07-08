import moment from 'moment-timezone'

const TIME_FORMAT = 'YYYY-MM-DD HH:mm:ss'

export function formatTime(time, tz, format) {
  if (time)
    return moment(time).tz(tz).format(format || TIME_FORMAT)
  else
    return ''
}

