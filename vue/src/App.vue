<template lang="pug">
  .app
    navbar.navbar
    ErrorToast
    router-view.view
</template>

<script>
import ErrorToast from '@/components/ErrorToast'
import navbar from '@/components/navbar'
import LiveLog from '@/LiveLog.js'
import RunsSocket from '@/RunsSocket'
import store from '@/store.js'
import { updateRuns } from '@/runs.js'

export default {
  name: 'App',
  components: {
    ErrorToast,
    navbar,
  },

  data() {
    return {
      liveLog: null,
      runsSocket: null,
      store,
    }
  },

  created() {
    this.liveLog = new LiveLog(this.store.state.logLines, 1000)
    const store = this.store
    this.runsSocket = new RunsSocket(
      msg => updateRuns(msg, store.state),
      () => store.state.errors.pop('connection error'),
      this.showToastError,
    )
  },

  destroyed() {
    this.liveLog.close()
    this.runsSocket.close()
  },

  methods: {
    showToastError(event) {
      store.state.errors.push('connection error')
    }
  },

}
</script>

<style lang="scss" scoped>
.app {
  max-width: none;
  margin-left: auto;
  margin-right: auto;
  font-family: "Roboto", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}

.view {
  margin-top: 1.5rem;
  max-width: none;
  padding-left: 40px;
  padding-right: 40px;
}
</style>

