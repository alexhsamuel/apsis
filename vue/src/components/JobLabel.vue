<template lang="pug">
  span.job-label {{ label }}
</template>

<script>
export default {
  props: [
    'label',
  ],
}
</script>

<style lang="scss">
span.job-label {
  margin: 0 4px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: white;
  color: #bbb;
  padding: 2px 8px;
}
</style>
