<template lang="pug">
div
  div.buttons
    p.uk-margin
      button.uk-button.uk-button-danger(v-on:click="shutDown()") Shut Down

</template>

<script>
import uikit from 'uikit'

export default {
  props: [],

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
</style>
