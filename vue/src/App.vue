<template lang="pug">
  #app
    navbar
    ErrorToast
    .uk-container.uk-container-expand.uk-margin-top
      router-view
</template>

<script>
import ErrorToast from '@/components/ErrorToast'
import navbar from '@/components/navbar'
import LiveLog from '@/LiveLog.js'
import RunsSocket from '@/RunsSocket'
import store from '@/store.js'

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
    this.runsSocket = new RunsSocket((msg) => {
      const runs = this.store.state.runs
      for (const runId in msg.runs)
        // We never change the runs, so freeze them to avoid reactivity.
        this.$set(runs, runId, Object.freeze(msg.runs[runId]))
      console.log('got', Object.keys(msg.runs).length)
    })
  },

  destroyed() {
    this.liveLog.close()
    this.runsSocket.close()
  },

}
</script>

<style lang="scss">
#app {
  max-width: none;
  margin-left: auto;
  margin-right: auto;
  font-family: "Roboto", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}
</style>

