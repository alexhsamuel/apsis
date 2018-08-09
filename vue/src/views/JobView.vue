<template lang="pug">
div
  h1 {{ job_id }}

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

  RunsList(:job_id="job_id")

</template>

<script>
import { join } from 'lodash'
import MarkdownIt from 'markdown-it'
import Program from '@/components/Program'
import RunsList from '@/components/RunsList'

const markdownit = new MarkdownIt()

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
      return this.job.params
        ? '(' + join(this.job.params, ', ') + ')'
        : ''
    },
  },

  created() {
    const v = this
    const url = '/api/v1/jobs/' + this.job_id  // FIXME
    fetch(url)
      .then((response) => response.json())
      .then((response) => { v.job = response })
  },

  methods: {
    markdown(src) { return markdownit.render(src) },
  },

}
</script>

<style scoped>
</style>
