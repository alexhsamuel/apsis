<template lang="pug">
div
  div
    div.field-label Server log
    pre.log {{ log }}

  div.buttons
    p.uk-margin
      button.uk-button.uk-button-danger(v-on:click="shutDown()") Shut Down

</template>

<script>
import _ from 'lodash'
import uikit from 'uikit'

import LiveLog from '@/LiveLog.js'

export default {
  props: [],

  data() {
    return {
      liveLog: null,
      logLines: [],
      MAX_LOG_LINES: 1000,
    }
  },

  computed: {
    log() { return _.join(this.logLines, '\n') + '\n' },
  },

  methods: {
    shutDown() {
      const url = '/api/control/shut_down'
      uikit.modal.confirm('Shut down the Apsis server?').then(
        () => { 
          fetch(url, {method: 'POST', body: '{}'})
            .then((response) => response.json() )
            .then((response) => {
              // FIXME: Do something reasonable here.
              console.log('shut down') 
            })
        }, 
        () => null)
    },

    join: _.join,
  },

  created() {
    const t = this
    this.liveLog = new LiveLog()
    console.log(this.liveLog)
    try {
      this.liveLog.open((line) => { 
        t.logLines.push(line)
        if (t.logLines.length > t.MAX_LOG_LINES)
          t.logLines.splice(0, 1)
      })
    } catch (exc) {
      console.log('error opening log socket:', exc)
    }
  },
}
</script>

<style lang="scss" scoped>
.log {
  height: 32em;
  overflow-x: hidden;
  overflow-y: scroll;
}
</style>
