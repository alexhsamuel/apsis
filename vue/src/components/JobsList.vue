<template lang="pug">
  div
    table.uk-table.uk-table-small.uk-table-divider
      thead
        tr
          th Job ID
          th Description
          th Program
          th Schedule

      tbody
        tr(
          v-for="job in jobs"
          v-if="!job.ad_hoc"
          :key="job.job_id"
          v-on:click="$router.push({ name: 'job', params: { job_id: job.job_id } })"
        )
          td.uk-text-nowrap: Job(:job-id="job.job_id")
          td(v-html="markdown(job.metadata.description || ' ')")
          td: Program(:program="job.program")
          td: ul
            li(v-for="(schedule, idx) in job.schedules" :key="idx") {{ schedule.str }}

</template>

<script>
import Job from './Job'
import MarkdownIt from 'markdown-it'
import Program from './Program'

const markdownit = new MarkdownIt()

export default { 
  data() {
    return {
      jobs: [],
    }
  },

  components: {
    Job,
    Program,
  },

  created() {
    const v = this
    const url = '/api/v1/jobs'
    fetch(url)
      .then((response) => response.json())
      .then((response) => response.forEach((j) => v.jobs.push(j)))
  },

  methods: {
    markdown(src) { return markdownit.renderInline(src) },
  },
}
</script>

<style scoped>
</style>

