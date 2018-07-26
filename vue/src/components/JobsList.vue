<template lang="pug">
  div
    table.uk-table.uk-table-small.uk-table-divider
      thead
        tr
          th Job ID
          th Program
          th Schedule

      tbody
        tr(
          v-for="job in jobs" 
          :key="job.job_id"
          v-on:click="$router.push({ name: 'job', params: { job_id: job.job_id } })"
        )
          td.uk-text-nowrap: Job(:job-id="job.job_id")
          td: code {{ job.program.str || "" }}
          td: ul
            li(v-for="(schedule, idx) in job.schedules" :key="idx") {{ schedule.str }}

</template>

<script>
import Job from './Job'

export default { 
  data() {
    return {
      jobs: [],
    }
  },

  components: {
    Job,
  },

  created() {
    const v = this
    const url = '/api/v1/jobs'
    fetch(url)
      .then((response) => response.json())
      .then((response) => response.forEach((j) => v.jobs.push(j)))
  },
}
</script>

<style scoped>
</style>

