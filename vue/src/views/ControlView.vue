<template lang="pug">
div
  div.log-box
    div.field-label Server log
    pre.log {{ log }}

  div.buttons
    button.button-danger(v-on:click="shutDown(true)") Restart
    button.button-danger(v-on:click="shutDown(false)") Shut Down

</template>

<script>
import _ from 'lodash'
import uikit from 'uikit'

import store from '@/store.js'

export default {
  props: [],

  data() {
    return {
      store,
    }
  },

  computed: {
    log() { return _.join(this.store.state.logLines, '\n') + '\n' },
  },

  methods: {
    shutDown(restart) {
      const url = '/api/control/shut_down' + (restart ? '?restart' : '')
      const msg = (restart ? 'Restart' : 'Shut down') + ' the Apsis server?'
      uikit.modal.confirm(msg).then(
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
  },

}
</script>

<style lang="scss" scoped>
.log-box {
  border: 1px solid #ddd;
  padding: 1em 2ex;
}

.log {
  height: 32em;
  overflow-x: hidden;
  overflow-y: scroll;
  -moz-scrollbars-vertical: scroll;
}

.buttons {
  margin-top: 1.5em;
  button {
    margin: 0 8px;
  }
  button:first-child {
    margin-left: 0;
  }
  button:last-child {
    margin-right: 0;
  }
}
</style>
