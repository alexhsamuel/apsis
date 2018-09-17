<template lang="pug">
  #app
    navbar
    .uk-container.uk-container-expand.uk-margin-top
      router-view
</template>

<script>
import navbar from '@/components/navbar'
import LiveLog from '@/LiveLog.js'
import RunsSocket from '@/RunsSocket'
import store from '@/store.js'

export default {
  name: 'App',
  components: {
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
      this.store.state.runs = Object.assign({}, this.store.state.runs, msg.runs)
      console.log('got', Object.keys(msg.runs).length, 'runs')
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

