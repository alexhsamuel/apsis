<template lang="pug">
  #app
    navbar
    .uk-container.uk-container-expand.uk-margin-top
      router-view
</template>

<script>
import navbar from './components/navbar'

export default {
  name: 'App',
  components: {
    navbar,
  }
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

