<template lang="pug">
router-link(
  :to="{ name: 'run', params: { run_id: runId } }"
) {{ runId }}

</template>

<script>
export default {
  props: ['runId'],
}
</script>

<style lang="scss" scoped>
@import '../styles/vars.scss';

a {
  background-color: white;
  color: $apsis-run-color;
  box-sizing: border-box;
  border: 1px solid $apsis-run-color;
  border-radius: 500px;
  padding: 0 0.4rem;
  font-size: 0.875rem;
  align-items: center;
  justify-content: center;
  cursor: default;

  &:hover {
    color: white;
    background-color: $apsis-run-color;
    text-decoration: none;
  }
}

</style>
