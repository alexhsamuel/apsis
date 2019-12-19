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
  margin-left: 4px;
  border: 1px solid #ddd;
  border-radius: 12px;
  background: #ccc;
  color: white;
  padding: 1px 8px;
}

</style>
