<template lang="pug">
div
  div
    span.title.uk-margin-right
      | Job 
      Job(:job-id="job_id")
    span(v-if="job && job.metadata.labels")
      JobLabel(v-for="label in job.metadata.labels" :key="label" :label="label")

  div.uk-margin-bottom(v-if="job" style="font-size:120%;")
    | Parameters ({{ params }})

  div.error-message(v-if="job === null") This job does not currently exist.  Past runs may be shown.

  div.frame(v-if="job && job.metadata.description")
    div.heading Description
    div.pad(v-html="markdown(job.metadata.description)")

  div.frame
    div.heading Runs
    div.pad
      RunsList(:query="query" :showJob="false" argColumnStyle="separate")

  div.frame
    div.heading Details
    div.pad
      table.fields(v-if="job"): tbody
        tr
          th program
          td.no-padding: Program(:program="job.program")

        tr
          th schedule
          td(v-if="job.schedules.length > 0")
            li(v-for="schedule in job.schedules" :key="schedule.str") {{ schedule.str }}
          td(v-else) No schedules.

        tr
          th conditions
          td(v-if="job.condition.length > 0")
            .condition.code(v-for="cond in job.condition" :key="cond.str") {{ cond.str }}
          td(v-else) No conditions.

        tr
          th actions
          td.no-padding(v-if="job.actions.length > 0")
            .action(v-for="action in job.actions"): table.fields
              tr(v-for="(value, key, i) in action" :key="i")
                th {{ key }}
                td {{ value }}
          td(v-else) No actions.

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

        tr(v-if="Object.keys(metadata).length")
          th metadata
          td.no-padding: table.fields
            tr(
              v-for="(value, key) in metadata" 
              :key="key"
            )
              th {{ key }}
              td {{ value }}

</template>

<script>
import { join, pickBy } from 'lodash'
import Job from '@/components/Job'
import JobLabel from '@/components/JobLabel'
import Program from '@/components/Program'
import RunsList from '@/components/RunsList'
import showdown from 'showdown'
import store from '@/store'

export default {
  props: ['job_id'],

  components: {
    Job,
    JobLabel,
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

    query() {
      // FIXME: Do better here.
      return '"' + this.job_id + '"'
    },

    // Metadata filtered, with keys omitted that are displayed specially.
    metadata() {
      return pickBy(
        this.job.metadata,
        (v, k) => k !== 'description' && k !== 'labels'
      )
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
    markdown(src) { return src.trim() === '' ? '' : (new showdown.Converter()).makeHtml(src) },
  },

}
</script>

<style lang="scss" scoped>
@import '../styles/vars.scss';

// This is rubbish.
.action {
  padding-top: 8px;
  th, td {
    line-height: 1;
  }
}
</style>
