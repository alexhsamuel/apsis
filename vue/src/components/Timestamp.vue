<template lang="pug">
span.timestamp(:class="{ past: str < store.state.timeStr }") {{ str }}
</template>

<script>
import { formatTime } from '../time'
import store from '../store'

export default {
  name: 'Timestamp',
  props: ['time'],

  data() {
    return {
      store
    }
  },

  computed: {
    str() {
      return formatTime(this.time, store.state.timeZone)
    },
  },
}
</script>

<style lang="scss">
.timestamp {
  font-size: 90%;
  white-space: nowrap;

  &.past {
    color: #888;
  }
}
</style>
