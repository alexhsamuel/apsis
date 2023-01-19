<template lang="pug">
div
  div.runs(v-if="run")
    div.title
      | Run {{ run_id }}
    div.subhead
      JobWithArgs(:job-id="run.job_id" :args="run.args")

    div.buttons.row-centered
      State.state(:state="run.state" name)
      OperationButton(
        v-for="operation in run.operations"
        :key="operation"
        :run_id="run_id"
        :operation="operation" 
        :button="true"
      )

    Frame(
      title="Run History"
      :closed="isCollapsed.runs"
    )
      RunsList(
        :show-job="false"
        :max-completed-runs="12"
        :max-scheduled-runs="12"
        arg-column-style="separate"
        :highlight-run-id="run.run_id"
        :job-controls="false"
        :run-controls="false"
        :time-controls="true"
        :query="{show: 20, path: run.job_id, args: run.args || {}}"
        style="max-height: 60rem; overflow-y: auto;"
      )

    Frame(title="Details")
      div
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
      button(
        v-if="output && output.output_len && !outputData"
        v-on:click="fetchOutputData()"
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

import * as api from '@/api'
import Frame from '@/components/Frame'
import Job from '@/components/Job'
import JobWithArgs from '@/components/JobWithArgs'
import OperationButton from '@/components/OperationButton'
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
    OperationButton,
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
        runs: this.$route.query.runs !== null,
      },
      output: null,
      outputRequested: false,  // FIXME: Remove?
      outputData: null,
      // Start with the run summary from the run state.
      run: store.state.runs.get(this.run_id),
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
      const run = store.state.runs.get(this.run_id)
      return run ? run.state : undefined
    },
  },

  methods: {
    joinArgs,

    fetchRun() {
      const url = api.getRunUrl(this.run_id)
      fetch(url)
        .then(async (response) => {
          if (response.ok) {
            const run = (await response.json()).runs[this.run_id]
            this.run = Object.freeze(run)
            this.fetchOutputMetadata()
          }
          else if (response.status === 404)
            this.run = null
          else
            store.state.errors.add('fetch ' + url + ' ' + response.status + ' ' + await response.text())
        })
    },

    fetchOutputMetadata() {
      if (this.run)
        fetch(api.getOutputUrl(this.run.run_id))
          .then(async rsp => {
            const outputs = await rsp.json()

            // FIXME: For now we only show output_id = 'output'.
            forEach(outputs, output => {
              if (output.output_id === 'output')
                this.output = output

                // If the output isn't too big, fetch it immediately.
                if (this.output.output_len <= 65536)
                  this.fetchOutputData()
            })
          })
          // FIXME: Handle error.
          .catch(err => { console.log(err) })
    },

    fetchOutputData() {
      const url = api.getOutputDataUrl(this.run.run_id, this.output.output_id)

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
      this.run = store.state.runs.get(this.run_id)
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
.title {
  margin-bottom: 0.5rem;
}

.subhead {
  margin-bottom: 1rem;
  font-size: 130%;
}

.buttons {
  margin-bottom: 1.5rem;
}

.output {
  font-family: "Roboto mono", monospaced;
}

.state {
  font-weight: bold;
  margin-right: 2ex;
}
</style>

