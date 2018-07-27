<template lang="pug">
div
  span {{ formatTime(store.state.time, store.state.timeZone, TIME_FORMAT) }}

</template>

<script>
import { formatTime } from '../format'
import store from '../store'

export default {
  data() {
    return {
      store,
      TIME_FORMAT: 'YYYY-MM-DD HH:mm:ss Z',
    }
  },

  methods: {
    formatTime,
  },
}
</script>

<style scoped>
</style>

