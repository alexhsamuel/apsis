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
        v-for="operation in OPERATIONS[run.state]"
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
        :query="{show: 20, grouping: false, job_id: run.job_id, args: run.args || {}}"
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
                      span  is {{ join(cond.states, '|') }}
                    span(v-else) {{ cond.str }}

            tr
              th elapsed
              td
                RunElapsed(:run="run")

    Frame(title="Run Log")
      div
        table.fields.run-log
          tbody
            tr(v-for="rec of runLog" :key="rec.timestamp + rec.message")
              th {{ rec.timestamp }}
              td {{ rec.message }}

    Frame(title="Metadata" closed)
      table.fields
        tbody
          tr(v-for="(value, key) in meta" :key="key")
            th {{ key }}
            td
              tt(v-if="typeof value === 'object'")
                table.fields.subfields
                  tbody
                    tr(v-for="(sv, sk) in value" :key="sk")
                      th {{ sk }}
                      td {{ sv }}
              tt(v-else) {{ value }}

    Frame(title="Output")
      <!-- button( -->
      <!--   v-if="output && output.output_len && !outputData" -->
      <!--   v-on:click="fetchOutputData()" -->
      <!-- ) load {{ output.output_len }} bytes -->
      div.output(v-if="outputMetadata")
        div.head
          span.name {{ outputMetadata.name }}
          span ({{ outputMetadata.content_type }})
          span {{ outputMetadata.length }} bytes
      <!-- pre.output.text.pad(v-if="outputData !== null") {{ outputData }} -->

  div.error-message(v-else)
    div.title
      | {{ run_id }}

    | This run does not currently exist.
    | This may be a run that was previously scheduled but never run.

</template>

<script>
import { join } from 'lodash'

import * as api from '@/api'
import Frame from '@/components/Frame'
import Job from '@/components/Job'
import JobWithArgs from '@/components/JobWithArgs'
import JsonSocket from '@/JsonSocket.js'
import OperationButton from '@/components/OperationButton'
import Program from '@/components/Program'
import Run from '@/components/Run'
import { joinArgs, OPERATIONS } from '@/runs'
import RunArgs from '@/components/RunArgs'
import RunElapsed from '@/components/RunElapsed'
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
    RunsList,
    State,
    Timestamp,
  },

  data() {
    return {
      isCollapsed: {
        runs: this.$route.query.runs !== null,
      },
      OPERATIONS,
      // Start with the run summary from the run state.
      run: store.state.runs.get(this.run_id),
      runLog: null,
      outputMetadata: null,
      // Run metadata.
      meta: null,
      store,
    }
  },

  computed: {
    /**
     * The update sequence of the run summary in the store, for detecting updates.
     */
    updateSeq() {
      const run = store.state.runs.get(this.run_id)
      return run ? run.seq : undefined
    },
  },

  methods: {
    joinArgs,

    fetchRun() {
      // FIXME: Use store.state.runs?  These are only summaries, though.
      const url = api.getRunUrl(this.run_id)
      fetch(url)
        .then(async (response) => {
          if (response.ok) {
            const run = (await response.json()).runs[this.run_id]
            this.run = Object.freeze(run)
          }
          else if (response.status === 404)
            this.run = null
          else
            store.state.errors.add('fetch ' + url + ' ' + response.status + ' ' + await response.text())
        })
    },

    format(key, value) {
      if (key === 'command')
        return '<code>' + value + '</code>'
      else
        return value
    },

    join,

  },

  beforeMount() {
    // Fetch full run info.
    this.fetchRun()

    // Connect to live run updates.
    const url = api.getRunUpdatesUrl(this.run_id)
    this.updates = new JsonSocket(
      url,
      msg => {
        console.log('run msg:', Object.keys(msg).join(' '))
        if (msg.meta)
          this.meta = msg.meta
        if (msg.run_log)
          this.runLog = msg.run_log
        if (msg.run_log_append)
          this.runLog.push(msg.run_log_append)
        if (msg.outputs && msg.outputs['output'])
          this.outputMetadata = msg.outputs['output']
      },
      () => {},
      err => { console.log(err) },
    )
    this.updates.open()
  },

  beforeDestroy() {
    // Disconnect live run updates.
    this.updates.close()
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

    // When the update sequence number changes, reload the whole run.
    updateSeq(seq, previous) {
      if (!this.run || this.run.seq !== seq) {
        this.fetchRun()
        if (this.output) {
          this.outputRequested = false
          this.fetchOutputMetadata()
        }
      }
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
  .head span {
    display: inline-block;
    padding-right: 0.5em;
    &.name {
      font-weight: bold;
    }
  }
  &.text {
    font-family: "Roboto mono", monospaced;
  }
}

.state {
  font-weight: bold;
  margin-right: 2ex;
}

.subfields {
  font-size: 85%;

  th {
    font-size: 85%;
    min-width: 24ex;
  }

  th, td {
    line-height: 1.1rem;
    padding-top: 0;
    padding-bottom: 0;
  }
}

.run-log {
  margin-top: 0.75rem;
  margin-bottom: 0.75rem;
  th, td {
    line-height: 1.5rem;
    padding-top: 0.1rem;
    padding-bottom: 0.1rem;
  }
}
</style>

