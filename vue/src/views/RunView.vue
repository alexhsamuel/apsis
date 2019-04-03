<template lang="pug">
div
  span.title {{ run_id }}
    //- FIXME: Use navbar or similar to organize.
  span(v-if="run")
    ActionButton(
        v-for="(url, action) in run.actions" 
        :key="action"
        :url="url" 
        :action="action" 
        :button="true"
      )

  div.error-message(v-if="run === null") 
    | This run does not currently exist. 
    | This may be a run that was previously scheduled but never run.

  div(v-if="run")
    div
      Job(:job-id="run.job_id")
      |
      | {{ arg_str }}

    table.fields
      tbody
        tr
          th state
          td: State(:state="run.state" name)

        tr(v-if="run.message")
          th message
          td {{ run.message }}

        tr(v-if="run.program")
          th program
          td.no-padding: Program(:program="run.program")

        tr(v-if="run.rerun != run.run_id")
          th rerun of
          td: Run(:run-id="run.rerun")

        tr
          th times
          td.no-padding: table.fields: tbody
            tr(v-for="[name, time] in run_times" :key="name")
              th {{ name }}
              td: Timestamp(:time="time")

        tr
          th history
          td.no-padding: RunHistory(:run_id="run_id")

        tr(
          v-if="run.meta && Object.keys(run.meta).length"
          v-on:click="metadataCollapsed = !metadataCollapsed"
        )
          th: div(style="white-space: nowrap;")
            | metadata 
          td(v-if="metadataCollapsed")
            div(uk-icon="chevron-right")
          td.no-padding(v-else)
            table.fields: tbody
              tr(v-for="(value, key) in run.meta" :key="key")
                th {{ key }}
                td(v-html="format(key, value)")

    .field-label output
    button.uk-button(
      v-if="output && output.output_len && !outputData"
      v-on:click="fetchOutputData(output.output_url)"
    ) load {{ output.output_len }} bytes
    pre.output(v-if="outputData !== null") {{ outputData }}

</template>

<script>
import { forEach, join, map, sortBy, toPairs } from 'lodash'

import ActionButton from '@/components/ActionButton'
import { formatElapsed } from '../time'
import Job from '@/components/Job'
import Program from '@/components/Program'
import Run from '@/components/Run'
import RunHistory from '@/components/RunHistory'
import State from '@/components/State'
import store from '@/store'
import Timestamp from '@/components/Timestamp'

export default {
  props: ['run_id'],
  components: { 
    ActionButton,
    Job,
    Program,
    Run,
    RunHistory,
    State,
    Timestamp,
  },

  data() {
    return {
      metadataCollapsed: true,
      output: null,
      outputRequested: false,  // FIXME: Remove?
      outputData: null,
      // Start with the run summary from the run state.
      run: store.state.runs[this.run_id],
      store,
    }
  },

  computed: {
    arg_str() {
      return join(map(toPairs(this.run.args), ([k, v]) => k + '=' + v), ' ')
    },

    run_times() {
      return sortBy(toPairs(this.run.times), ([k, v]) => v)
    },

    /**
     * The state of the run summary in the store, for detecting updates.
     */
    storeState() {
      return store.state.runs[this.run_id].state
    }
  },

  methods: {
    fetchRun() {
      const url = '/api/v1/runs/' + this.run_id  // FIXME
      fetch(url)
        .then(async (response) => {
          if (response.ok)
            this.run = (await response.json()).runs[this.run_id]
          else if (response.status === 404)
            this.run = null
          else
            store.state.errors.add('fetch ' + url + ' ' + response.status + ' ' + await response.text())
        })
    },

    fetchOutputMetadata(run) {
      if (run && run.output_url)
        fetch(run.output_url)
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
      if (key === 'elapsed')
        return formatElapsed(value)
      else if (key === 'command')
        return '<code>' + value + '</code>'
      else 
        return value
    },

  },

  mounted() {
    // Fetch full run info.
    this.fetchRun()
    // Fetch output metadata immediately.
    this.fetchOutputMetadata(this.run)
  },

  watch: {
    // Reset state on nav from one run to another.
    '$route'(to, from) {
      this.run = store.state.runs[this.run_id]
      this.output = null
      this.outputData = null
      this.outputRequested = false
      this.fetchRun()
      this.fetchOutputMetadata()
    },

    storeState(to, from) {
      // The run summary state has changed, so reload the whole run.
      this.fetchRun()
    }
  },

}
</script>

<style lang="scss" scoped>
.output {
  border: 1px solid #c0c0c0;
  padding: 0.5rem;
  font-family: "Roboto mono", monospaced;
}
</style>

