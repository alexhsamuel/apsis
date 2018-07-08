<template>
  <div>
    <span>
      {{ formatTime(store.state.time, store.state.timeZone) }}
    </span>
    <select id="timeZone" v-model="timeZone" v-on:change="onTimeZoneChange">
      <option v-for="tz in timeZones" v-bind:value="tz">{{ shortTimeZone(tz) }}</option>
    </select>
  </div>
</template>

<script>
import moment from 'moment-timezone'

import store from '../store'

const TIME_FORMAT = 'YYYY-MM-DD HH:mm:ss'

function formatTime(date, tz) {
  return moment(date).tz(tz).format(TIME_FORMAT)
}

export default {
  data() {
    return {
      store,
      timeZone: store.state.timeZone,
      timeZones: [
        Intl.DateTimeFormat().resolvedOptions().timeZone,
        'UTC',
        'Asia/Tokyo',
        'Europe/London',
        'America/New_York',
      ],
    }
  },

  methods: {
    formatTime,

    shortTimeZone(tz) {
      const parts = tz.split('/')
      return parts[parts.length - 1].replace('_', ' ')
    },

    onTimeZoneChange(event) {
      const tz = event.target.value
      this.store.setTimeZone(tz)
    }
  },

}
</script>

<style scoped>
#timeZone {
  border: 1px solid #e0e0e0;
  height: 3.5ex;
  font-weight: 400;
}
</style>

