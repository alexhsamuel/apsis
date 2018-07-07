<template>
  <h1>message: {{ msg }}</h1>
</template>

<script>
export default {
  name: 'test',
  props: ['msg'],
}
</script>

<style scoped>
h1 {
  color: green;
}
</style>
