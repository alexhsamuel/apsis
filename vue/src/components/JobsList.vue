<template lang="pug">
div.grid
  div.field-label Job
  div.field-label Program
  div.field-label Schedule

  div.header

  template(
    v-for="job in jobs"
    v-if="!job.ad_hoc"
    v-on:click="$router.push({ name: 'job', params: { job_id: job.job_id } })"
  )
    div
      div.uk-text-nowrap: Job(:job-id="job.job_id")
      div(v-html="markdown(job.metadata.description || ' ')")
    div: Program(:program="job.program")
    div: ul
      li(v-for="(schedule, idx) in job.schedules" :key="idx") {{ schedule.str }}

    div.border

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

<style lang="scss" scoped>
@import '../styles/vars.scss';

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  grid-column-gap: 1.5rem;
  grid-auto-rows: min-content;
  grid-row-gap: 1rem;

  .header {
    grid-column-start: 1;
    grid-column-end: 4;
    border-bottom: 2px solid #eee;
  }

  .border {
    grid-column-start: 1;
    grid-column-end: 4;
    border-bottom: 1px solid $apsis-grid-color;
    align-self: center;
  }
}
</style>

