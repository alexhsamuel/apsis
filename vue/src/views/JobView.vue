<template lang="pug">
div
  h1 {{ job_id }}

  div.error-message(v-if="job === null") This job does not currently exist.  Past runs may be shown.
  p(v-if="job && job.metadata.description" v-html="markdown(job.metadata.description)")

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

    tr(v-if="job.reruns")
      th reruns
      td.no-padding: table.fields
        tr(
          v-for="(value, key) in job.reruns" 
          v-if="key !== 'description'" 
          :key="key"
        )
          th {{ key }}
          td {{ value }}

    tr
      th metadata
      td.no-padding: table.fields
        tr(
          v-for="(value, key) in job.metadata" 
          v-if="key !== 'description'" 
          :key="key"
        )
          th {{ key }}
          td {{ value }}

  RunsList(:jobFilter="job_id")

</template>

<script>
import { join } from 'lodash'
import MarkdownIt from 'markdown-it'
import Program from '@/components/Program'
import RunsList from '@/components/RunsList'
import store from '@/store'

const markdownit = new MarkdownIt()

export default {
  props: ['job_id'],

  components: {
    Program,
    RunsList,
  },

  data() {
    return {
      // Undefined before the job has loaded; null if the job doesn't exist.
      job: undefined,
    }
  },

  computed: {
    params() {
      return join(this.job.params, ', ')
    },
  },

  created() {
    const url = '/api/v1/jobs/' + this.job_id  // FIXME
    fetch(url)
      .then(async (response) => {
        if (response.ok)
          this.job = await response.json()
        else if (response.status === 404)
          this.job = null
        else
          store.state.errors.add('fetch ' + url + ' ' + response.status + ' ' + await response.text())
      })
  },

  methods: {
    markdown(src) { return markdownit.render(src) },
  },

}
</script>

<style lang="scss" scoped>
@import '../styles/vars.scss';

h1 {
  color: $apsis-job-color;
}
</style>
