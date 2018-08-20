<template lang="pug">
  #app
    navbar
    .uk-container.uk-container-expand.uk-margin-top
      router-view
</template>

<script>
import navbar from '@/components/navbar'
import LiveLog from '@/LiveLog.js'
import store from '@/store.js'

export default {
  name: 'App',
  components: {
    navbar,
  },

  data() {
    return {
      liveLog: null,
      store,
    }
  },

  created() {
    this.liveLog = new LiveLog(this.store.state.logLines, 1000)
  },

  destroyed() {
    this.liveLog.close()
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

