<template>
  <span class="uk-badge run-badge" v-on:click="go()">
    {{ runId }}
  </span>
</template>

<script>
export default {
  props: ['runId'],

  methods: {
    go() {
      this.$router.push({ name: 'run', params: { run_id: this.runId } })
    }
  }
}
</script>

<style lang="scss" scoped>
@import '../styles/index.scss';

.run-badge {
  background-color: white;
  color: $apsis-run-color;
  border: 2px solid $apsis-run-color;
  font-weight: 600;
  padding: 0 0.4rem;
  cursor: default;

  &:hover {
    color: white;
    background-color: $apsis-run-color;
  }
}

</style>
