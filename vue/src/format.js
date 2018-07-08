import moment from 'moment-timezone'

const TIME_FORMAT = 'YYYY-MM-DD HH:mm:ss'

export function formatTime(time, tz) {
  if (time)
    return moment(time).tz(tz).format(TIME_FORMAT)
  else
    return ''
}

