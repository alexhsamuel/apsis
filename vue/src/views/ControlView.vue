<template lang="pug">
div
  div.buttons
    p.uk-margin
      button.uk-button.uk-button-danger(v-on:click="shutDown()") Shut Down

</template>

<script>
export default {
  props: [],

  methods: {
    shutDown() {
      const url = '/control/shut_down'
      fetch(url, {method: 'POST', body: '{}'})
        .then((response) => response.json() )
        .then((response) => { console.log('response!') })
    },
  },
}
</script>

<style lang="scss" scoped>
</style>
