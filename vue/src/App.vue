<template>
  <div id="app">
    <navbar/>
    <router-view/>
  </div>
</template>

<script>
import navbar from './components/navbar.vue'
export default {
  name: 'App',
  components: {
    navbar,
  }
}
</script>

<style>
#app {
  width: 90%;
  max-width: none;
  margin-left: auto;
  margin-right: auto;
  font-family: "Roboto", "HelveticaNeue", "Helvetica Neue", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}
</style>

