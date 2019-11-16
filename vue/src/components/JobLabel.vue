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
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  color: #aaa;
  padding: 2px 8px;

  &+ span.job-label {
    margin-left: 4px;
  }
}

</style>
