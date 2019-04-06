<!--
  Shows elapsed time for a run, live if it's running.
-->

<template lang="pug">
span
  //- Treat running specially; otherwise we don't need to be watching the current time.
  template(v-if="run.state === 'running'") {{ running }}
  template(v-else) {{ notRunning }}
</template>

<script>
import moment from 'moment-timezone'

import store from '@/store'
import { formatDuration } from '@/time.js'

export default {
  props: ['run'],
  data() {
    return {
      store,
    }
  },

  computed: {
    notRunning() {
      if (this.run.times.running) {
        const start = moment(this.run.times.running)
        const end = moment(this.run.times[this.run.state])
        return formatDuration(end.diff(start) * 1e-3)
      }
      else
        return ''
    },

    running() {
      const start = moment(this.run.times.running)
      const end = moment(this.store.state.time)
      return formatDuration(end.diff(start) * 1e-3)
    },
  },

}
</script>
