<template>
  <div>
    <br>
    <h4>{{ job_id }}</h4>

    <dl v-if="job">
      <dt>Parameters</dt>
      <dd>{{ params }}</dd>

      <dt>Program</dt>
      <dd>{{ job.program.str }}</dd>

      <template v-for="schedule in job.schedules">
        <dt>Schedule</dt>
        <dd>{{ schedule.str }}</dd>
      </template>
    </dl>

    <runs v-bind:job_id="job_id"></runs>
  </div>
</template>

<script>
import { join } from 'lodash'

export default {
  props: ['job_id'],

  data() {
    return {
      job: null,
    }
  },

  computed: {
    params(job) {
      return join(job.params, ', ')
    },
  },

  created() {
    const v = this
    const url = '/api/v1/jobs/' + this.job_id  // FIXME
    fetch(url)
      .then((response) => response.json())
      .then((response) => { v.job = response })
  },

}
</script>

<style scoped>
</style>

