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
