<template>
  <div class="hello">
    <test msg="Hello, world."></test>
    <h1>{{ msg }}</h1>
  </div>
</template>

<script>
import test from './test.vue'

export default {
  name: 'HelloWorld',
  props: ['message'],
  data() {
    return {
      msg: 'Welcome to Your Vue.js App'
    }
  },
  components: {
    test
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
h1, h2 {
  font-weight: normal;
}
ul {
  list-style-type: none;
  padding: 0;
}
li {
  display: inline-block;
  margin: 0 10px;
}
a {
  color: #42b983;
}
</style>
