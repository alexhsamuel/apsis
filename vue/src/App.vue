<template>
  <div id="app">
    <navbar/>
    <div class="uk-container uk-container-expand">
      <router-view/>
    </div>
  </div>
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

/* Global style stuff */
dt {
  padding: 0 1em 0 0;
  margin: 0;
  float: left;
  font-weight: 700;
}

dd {
  margin: 0 0 0 10rem;
}

.job-link {
  color: #00a050;
  cursor: default;

  &:hover {
    text-decoration: underline;
  }
}

.run-link {
  color: #007030;
  cursor: default;

  &:hover {
    text-decoration: underline;
  }
}

</style>

