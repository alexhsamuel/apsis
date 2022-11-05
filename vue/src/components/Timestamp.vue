<template lang="pug">
span.timestamp.tooltip
  | {{ str }}
  span.tooltiptext {{ elapsed() }}
</template>

<script>
import { formatDuration, formatTime } from '../time'
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

  methods: {
    elapsed() {
      console.log('elapsed')
      const elapsed = (new Date(this.store.state.time) - new Date(this.time)) * 0.001
      return (
        elapsed > 0 ? formatDuration(elapsed) + ' ago'
        : 'in ' + formatDuration(-elapsed)
      )
    },
  },
}
</script>

<style lang="scss">
.timestamp {
  white-space: nowrap;
}
</style>
