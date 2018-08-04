<template lang="pug">
span {{ formatTime(time, store.state.timeZone) }}
</template>

<script>
import { formatTime } from '../time'
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
  white-space: nowrap;
}
</style>
