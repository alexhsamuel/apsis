<template lang="pug">
  .app
    navbar.navbar
    ErrorToast
    router-view.view
</template>

<script>
import * as api from '@/api'
import ErrorToast from '@/components/ErrorToast'
import navbar from '@/components/navbar'
import JsonSocket from '@/JsonSocket.js'
import LiveLog from '@/LiveLog.js'
import store from '@/store.js'
import { processMsgs } from '@/runs.js'

export default {
  name: 'App',
  components: {
    ErrorToast,
    navbar,
  },

  data() {
    return {
      liveLog: null,
      summarySocket: null,
      store,
    }
  },

  created() {
    this.liveLog = new LiveLog(this.store.state.logLines, 1000)
    const store = this.store

    console.log('creating summary socket', api.getSummaryUrl())
    this.summarySocket = new JsonSocket(
      api.getSummaryUrl(true),
      msgs => processMsgs(msgs, store.state),
      () => store.state.errors.pop('connection error'),
      this.showToastError,
    )
    this.summarySocket.open()
  },

  destroyed() {
    this.liveLog.close()
    this.summarySocket.close()
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

