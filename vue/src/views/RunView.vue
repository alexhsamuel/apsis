<template lang="pug">
div(v-if="run")
  div
    span.title {{ run_id }}
    //- FIXME: Use navbar or similar to organize.
    span
      ActionButton(
          v-for="(url, action) in run.actions" 
          :key="action"
          :url="url" 
          :action="action" 
          :button="true"
        )
  div
    div
      Job(v-bind:job-id="run.job_id")
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

        tr(
          v-if="Object.keys(run.meta).length"
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

    h5 output
    a(v-if="run !== null && run.output_len && output === null" v-on:click="load_output()")
      | (load {{ run.output_len }} bytes)
    pre.output(v-if="output !== null") {{ output }}

</template>

<script>
import { join, map, sortBy, toPairs } from 'lodash'

import ActionButton from '@/components/ActionButton'
import { formatElapsed } from '../time'
import Job from '@/components/Job'
import Program from '@/components/Program'
import Run from '@/components/Run'
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
    State,
    Timestamp,
  },

  data() {
    return {
      metadataCollapsed: true,
      output: null,
      store,
    }
  },

  computed: {
    run() {
      const run = this.store.state.runs[this.run_id]

      // Immediately load the output too, unless it's quite large.
      if (this.output === null && run.output_len !== null && run.output_len < 65536)
        this.load_output(run)

      return run
    },

    arg_str() {
      return join(map(toPairs(this.run.args), ([k, v]) => k + '=' + v), ' ')
    },

    run_times() {
      return sortBy(toPairs(this.run.times), ([k, v]) => v)
    },
  },

  methods: {
    load_output(run) {
      const v = this
      const url = this.run.output_url
      fetch(url)
        // FIXME: Handle failure, set error.
        // FIXME: Might not be text!
        // FIXME: Don't murder the browser with huge output or long lines.
        .then((response) => response.text())
        .then((response) => { v.output = response })
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

  watch: {
    // '$route'(to, from) {
    //   this.load()
    // },
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

