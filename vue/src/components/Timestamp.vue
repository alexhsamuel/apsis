<template lang="pug">
span.timestamp {{ str }}
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
  white-space: nowrap;
}
</style>
