<template lang="pug">
  div(v-if="run")
    br
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
        | {{ arg_str }}

      dl.fields
        dt state
        dd: State(v-bind:state="run.state" name="1" style="margin-left: -1.6rem;")

        template(v-if="run.message")
          dt message
          dd {{ run.message }}

        template(v-if="run.rerun != run.run_id")
          dt rerun of
          dd: Run(:run-id="run.rerun")

        dt times
        dd
          dl
            template(v-for="[name, time] in run_times")
              dt(:key="name") {{ name }}
              dd(:key="'time:' + name"): Timestamp(:time="time")

        template(v-for="(value, key) in run.meta")
          dt(:key="key") {{ key }}
          //- FIXME: Hack!
          dd(:key="'value:' + key") {{ key == "elapsed" ? formatElapsed(value) : value }}

      h5 output
      a(v-if="run !== null && run.output_len !== null && output === null" v-on:click="load_output()")
        | (load {{ run.output_len }} bytes)
      pre.output(v-if="output !== null") {{ output }}
</template>

<script>
import { join, map, sortBy, toPairs } from 'lodash'

import ActionButton from './ActionButton'
import { formatElapsed } from '../format'
import Job from './Job'
import Run from './Run'
import RunsSocket from '../RunsSocket'
import State from './State'
import Timestamp from './Timestamp'

export default {
  props: ['run_id'],
  components: { 
    ActionButton,
    Job,
    Run,
    State,
    Timestamp,
  },

  data() {
    return {
      runs_socket: null,
      run: null,
      output: null,
    }
  },

  computed: {
    arg_str() {
      return join(map(toPairs(this.run.args), ([k, v]) => k + '=' + v), ' ')
    },

    run_times() {
      return sortBy(toPairs(this.run.times), ([k, v]) => v)
    },
  },

  methods: {
    load() {
      const v = this
      this.runs_socket = new RunsSocket(this.run_id, undefined)
      this.runs_socket.open((msg) => { 
        v.run = msg.runs[v.run_id] 
        // Immediately load the output too, unless it's quite large.
        if (v.run.output_len !== null && v.run.output_len < 32768)
          v.load_output()
      })
    },

    load_output() {
      const v = this
      const url = '/api/v1/runs/' + this.run.run_id + '/output'  // FIXME
      fetch(url)
        // FIXME: Handle failure, set error.
        .then((response) => response.text())  // FIXME: Might not be text!
        .then((response) => { v.output = response })
    },

    formatElapsed,
  },

  mounted() { 
    this.load()
  },

  destroyed() {
    this.runs_socket.close()
  },

  watch: {
    '$route'(to, from) {
      this.load()
    },
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

