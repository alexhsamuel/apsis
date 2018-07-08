<template>
  <span>
    {{ formatTime(time, store.state.timeZone) }}
  </span>
</template>

<script>
import { formatTime } from '../format'
import store from '../store'

export default {
  name: 'Timestamp',
  props: ['time'],

  data() {
    return {
      store,
    }
  },

  methods: {
    formatTime,
  },
}
</script>

<style scoped>
span {
  font-size: 90%;
}
</style>
