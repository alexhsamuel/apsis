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
        <dt v-bind:key="'label:' + schedule.str">Schedule</dt>
        <dd v-bind:key="schedule.str">{{ schedule.str }}</dd>
      </template>
    </dl>

    <RunsList v-bind:job_id="job_id"></RunsList>
  </div>
</template>

<script>
import { join } from 'lodash'
import RunsList from './RunsList'

export default {
  props: ['job_id'],

  components: {
    RunsList,
  },

  data() {
    return {
      job: null,
    }
  },

  computed: {
    params() {
      return join(this.job.params, ', ')
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

