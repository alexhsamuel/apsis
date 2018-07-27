<template lang="pug">
div
  h1 {{ job_id }}

  table.fields(v-if="job"): tbody
    tr
      th parameters
      td {{ params }}

    tr
      th program
      td.no-padding: Program(:program="job.program")

    tr
      th schedule
      td: li(v-for="schedule in job.schedules" :key="schedule.str") {{ schedule.str }}

  RunsList(:job_id="job_id")

</template>

<script>
import { join } from 'lodash'
import Program from '@/components/Program'
import RunsList from '@/components/RunsList'

export default {
  props: ['job_id'],

  components: {
    Program,
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

