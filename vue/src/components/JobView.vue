<template lang="pug">
  div.uk-margin-top
    h1 {{ job_id }}

    table.fields(v-if="job"): tbody
      tr
        th parameters
        td {{ params }}

      tr
        th program
        td: code {{ job.program.str }}

      tr(v-for="schedule in job.schedules" :key="schedule.str")
        th schedule
        td {{ schedule.str }}

    RunsList(:job_id="job_id")

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

