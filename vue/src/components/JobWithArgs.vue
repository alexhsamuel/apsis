<template lang="pug">
span.job-with-args
  Job(:job-id="jobId")
  span(v-if="args")
    span.bracket.spaced (
    RunArgs(:args="args")
    span.bracket )
</template>

<script>
import Job from '@/components/Job'
import RunArgs from '@/components/RunArgs'

export default {
  components: {
    Job,
    RunArgs,
  },

  props: [
    'jobId',
    'args',
  ],
}
</script>

<style lang="scss" scoped>
.job-with-args {
  margin: 0 0.5em;

  .bracket {
    color: #aaa;
    margin: 0 0.2em;
  }
}
</style>
