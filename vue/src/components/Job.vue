<template lang="pug">
a.job-link(v-on:click="go()") {{ jobId }}

</template>

<script>
export default {
  props: ['jobId'],

  methods: {
    go() {
      this.$router.push({ name: 'job', params: { job_id: this.jobId } })
    }
  }
}
</script>

<style lang="scss" scoped>
@import '../styles/vars.scss';

.job-link {
  color: $apsis-job-color;
  cursor: default;

  &:hover {
    color: $apsis-job-color;
    text-decoration: underline;
  }
}

</style>
