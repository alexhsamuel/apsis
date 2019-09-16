<template lang="pug">
router-link(
  :to="{ name: 'job', params: { job_id: jobId }}"
) {{ label }}

</template>

<script>
export default {
  props: [
    'jobId',
    'name',
  ],

  computed: {
    label() { return this.name || this.jobId },
  },
}
</script>

<style lang="scss" scoped>
@import '../styles/vars.scss';

a {
  color: $apsis-job-color;
  cursor: default;
  white-space: nowrap;

  &:hover {
    color: $apsis-job-color;
    text-decoration: underline;
  }
}

</style>
