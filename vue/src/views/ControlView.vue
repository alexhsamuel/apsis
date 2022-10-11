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
import ConfirmationModal from '@/components/ConfirmationModal'
import store from '@/store.js'
import Vue from 'vue'

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
      const message = (restart ? 'Restart' : 'Shut down') + ' the Apsis server?'
      console.log(message)

      const fn = () =>
        fetch(url, {method: 'POST', body: '{}'})
          .then((response) => response.json() )
          .then((response) => {
            // FIXME: Do something reasonable here.
            console.log('shut down') 
          })

      const Class = Vue.extend(ConfirmationModal)
      const modal = new Class({propsData: {message, ok: fn}})
      // Mount and add the modal.  The modal destroys and removes itself.
      modal.$mount()
      this.$root.$el.appendChild(modal.$el)
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
