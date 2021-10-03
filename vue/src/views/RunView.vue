<template lang="pug">
div
  span(v-if="run")
    div.uk-margin-bottom
      span.title
        | {{ run_id }}
        JobWithArgs(:job-id="run.job_id" :args="run.args").spaced

    div.uk-margin-bottom
      State(:state="run.state" name).uk-text-bold.uk-margin-right
      ActionButton(
        v-for="(url, action) in run.actions" 
        :key="action"
        :url="url" 
        :action="action" 
        :button="true"
      )

    Frame(title="Run History" closed)
      RunsList(
        :path="run.job_id"
        :args="run.args || {}"
        :group-runs="false"
        :show-job="false"
        :max-completed-runs="12"
        :max-scheduled-runs="12"
        arg-column-style="separate"
        :highlight-run-id="run.run_id"
        style="max-height: 28rem; overflow-y: auto;"
      )

    Frame(title="Details")
      div.pad
        table.fields
          tbody
            tr(v-if="run.message")
              th message
              td {{ run.message }}

            tr(v-if="run.program")
              th program
              td.no-padding: Program(:program="run.program")

            //- FIXME: Do better here.
            tr
              th conditions
              td.no-padding: table.fields: tbody
                tr(v-for="cond in run.conds" :key="cond.str")
                  td(style="padding-left: 0")
                    span(v-if="cond.type === 'dependency'")
                      span dependency:
                      JobWithArgs(:job-id="cond.job_id" :args="cond.args")
                      span &rarr; {{ join(cond.states, ' ') }}
                    span(v-else) {{ cond.str }}

            tr
              th elapsed
              td
                RunElapsed(:run="run")

            tr
              th log
              td.no-padding: RunLog(:run_id="run_id")

    Frame(v-if="run.meta && Object.keys(run.meta).length" title="Metadata" closed)
      table.fields
        tbody
          tr(v-for="(value, key) in run.meta" :key="key")
            th {{ key }}
            td
              tt {{ value }}

    Frame(title="Output")
      button.uk-button(
        v-if="output && output.output_len && !outputData"
        v-on:click="fetchOutputData(output.output_url)"
      ) load {{ output.output_len }} bytes
      pre.output.pad(v-if="outputData !== null") {{ outputData }}

  div.error-message(v-else)
    div.title
      | {{ run_id }}

    | This run does not currently exist. 
    | This may be a run that was previously scheduled but never run.

</template>

<script>
import { forEach, join, sortBy, toPairs } from 'lodash'

import ActionButton from '@/components/ActionButton'
import Frame from '@/components/Frame'
import Job from '@/components/Job'
import JobWithArgs from '@/components/JobWithArgs'
import Program from '@/components/Program'
import Run from '@/components/Run'
import { joinArgs } from '@/runs'
import RunArgs from '@/components/RunArgs'
import RunElapsed from '@/components/RunElapsed'
import RunLog from '@/components/RunLog'
import RunsList from '@/components/RunsList'
import State from '@/components/State'
import store from '@/store'
import Timestamp from '@/components/Timestamp'

export default {
  props: ['run_id'],
  components: { 
    ActionButton,
    Frame,
    Job,
    JobWithArgs,
    Program,
    Run,
    RunArgs,
    RunElapsed,
    RunLog,
    RunsList,
    State,
    Timestamp,
  },

  data() {
    return {
      isCollapsed: {
        runs: true,
        metadata: true,
      },
      output: null,
      outputRequested: false,  // FIXME: Remove?
      outputData: null,
      // Start with the run summary from the run state.
      run: store.state.runs[this.run_id],
      store,
    }
  },

  computed: {
    run_times() {
      return sortBy(toPairs(this.run.times), ([k, v]) => v)
    },

    /**
     * The state of the run summary in the store, for detecting updates.
     */
    storeState() {
      const run = store.state.runs[this.run_id]
      return run ? run.state : undefined
    },
  },

  methods: {
    joinArgs,

    fetchRun() {
      const url = '/api/v1/runs/' + this.run_id  // FIXME
      fetch(url)
        .then(async (response) => {
          if (response.ok) {
            const run = (await response.json()).runs[this.run_id]
            this.run = Object.freeze(run)
            console.log(this.run)
            this.fetchOutputMetadata()
          }
          else if (response.status === 404)
            this.run = null
          else
            store.state.errors.add('fetch ' + url + ' ' + response.status + ' ' + await response.text())
        })
    },

    fetchOutputMetadata() {
      if (this.run && this.run.output_url)
        fetch(this.run.output_url)
          .then(async rsp => {
            const outputs = await rsp.json()

            // FIXME: For now we only show output_id = 'output'.
            forEach(outputs, output => {
              if (output.output_id === 'output')
                this.output = output

                // If the output isn't too big, fetch it immediately.
                if (this.output.output_len <= 65536)
                  this.fetchOutputData(this.output.output_url)
            })
          })
          // FIXME: Handle error.
          .catch(err => { console.log(err) })
    },

    fetchOutputData(url) {
      // Don't request output more than once.
      if (this.outputRequested)
        return
      this.outputRequested = true

      fetch(url)
        // FIXME: Might not be text!
        // FIXME: Don't murder the browser with huge output or long lines.
        .then(async rsp => {
          this.outputData = await rsp.text()
        })
        // FIXME: Handle error.
        .catch(err => { console.log(err) })
    },

    format(key, value) {
      if (key === 'command')
        return '<code>' + value + '</code>'
      else 
        return value
    },

    join,

  },

  mounted() {
    // Fetch full run info.
    this.fetchRun()
  },

  watch: {
    // Reset state on nav from one run to another.
    '$route'(to, from) {
      this.run = store.state.runs[this.run_id]
      this.output = null
      this.outputData = null
      this.outputRequested = false
      this.fetchRun()
    },

    storeState(state, previous) {
      if (!this.run || this.run.state !== state)
        // The run summary state has changed, so reload the whole run.
        this.fetchRun()
    }
  },

}
</script>

<style lang="scss" scoped>
.output {
  font-family: "Roboto mono", monospaced;
}
</style>

