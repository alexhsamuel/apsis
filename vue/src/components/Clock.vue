<template>
  <span>
    {{ formatTime(store.state.time, store.state.timeZone) }}
  </span>
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
    }
  },

  methods: {
    formatTime
  },

}
</script>

<style scoped>
span {
}
</style>

