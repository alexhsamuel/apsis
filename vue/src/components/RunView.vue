<template>
  <div>
    <br>
    <div class="title">{{ run_id }}</div>
    <div v-if="run">
      <div>
        <Job v-bind:job-id="run.job_id"></Job>
        {{ arg_str }}
      </div>
      <dl>
        <dt>state</dt>
        <dd><State v-bind:state="run.state" name="1"></State></dd>

        <template v-if="run.message">
          <dt>message</dt>
          <dd>{{ run.message }}</dd>
        </template>

        <template v-if="run.rerun != run.run_id">
          <dt>rerun of</dt>
          <dd><Run v-bind:run-id="run.rerun"></Run></dd>
        </template>

        <dt>times</dt>
        <dd>
          <dl>
            <template v-for="[name, time] in run_times">
              <dt>{{ name }}</dt>
              <dd><Timestamp v-bind:time="time"></Timestamp></dd>
            </template>
          </dl>
        </dd>

        <template v-for="(value, key) in run.meta">
          <dt>{{ key }}</dt>
          <dd>{{ key == "elapsed" ? formatElapsed(value) : value }}</dd>  <!-- FIXME: Hack! -->
        </template>
      </dl>
      <h5>output</h5>
      <a v-if="run !== null && run.output_len !== null && output === null" v-on:click="load_output()">
        (load {{ run.output_len }} bytes)
      </a>
      <pre class="output" v-if="output !== null">{{ output }}</pre>
    </div>
  </div>
</template>

<script>
import { join, map, sortBy, toPairs } from 'lodash'

import { formatElapsed } from '../format'
import Job from './Job'
import Run from './Run'
import RunsSocket from '../RunsSocket'
import State from './State'
import Timestamp from './Timestamp'

export default {
  props: ['run_id'],
  components: { 
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

<style scoped>
.output {
  border: 1px solid #c0c0c0;
  padding: 0.5rem;
  font-family: "Roboto mono", monospaced;
}
</style>

