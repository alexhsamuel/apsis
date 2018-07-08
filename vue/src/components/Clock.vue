<template>
  <span>
    {{ formatTime(time) }}
  </span>
</template>

<script>
import moment from 'moment-timezone'

const TIME_FORMAT = 'YYYY-MM-DD HH:mm:ss'
let tz = 'UTC'

function formatTime(date) {
  return moment(date).tz(tz).format(TIME_FORMAT)
}

export default {
  data() {
    return {
      time: new Date(),
    }
  },

  methods: {
    formatTime
  },

  mounted() {
    const tick = () => {
      this.time = new Date()
      window.setTimeout(tick, 1000 - this.time % 1000)
    }
    tick()
  },

}
</script>

<style scoped>
span {
}
</style>

