<template>
  <div>
   <br>
    <table class="uk-table uk-table-divider uk-table-hover uk-table-small uk-table-justify">
      <thead>
        <tr>
          <th class="col-job">Job</th>
          <th class="col-args">Args</th>
          <th class="col-run">Run</th>
          <th class="col-reruns">Reruns</th>
          <th class="col-state">State</th>
          <th class="col-schedule-time">Schedule</th>
          <th class="col-start-time">Start</th>
          <th class="col-elapsed">Elapsed</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="rerun_group in rerun_groups">
          <!--
          <tr class="group" v-bind:key="rerun_group[0].job_id">
            <td colspan="6">
              <Job v-bind:job-id="rerun_group[0].job_id"></Job>
              {{ arg_str(rerun_group[0].args) }}
            </td>
          </tr>
          -->
          <tr 
              v-for="(run, index) in rerun_group" 
              :key="run.run_id"
              v-bind:class="{ 'run-group-next': index > 0 }"
            >
            <td class="col-job"><Job v-bind:job-id="run.job_id"></Job></td>
            <td class="col-args"><span>{{ arg_str(run.args) }}</span></td>
            <td class="col-run"><Run v-bind:run-id="run.run_id"></Run></td>
            <td class="col-reruns">
              <span>{{ rerun_group.length }}</span>
              <span v-if="index == 0 && rerun_group.length > 1">
                <a 
                    v-if="getGroupCollapse(run.run_id)"
                    uk-icon="icon: chevron-left"
                    href="#" 
                    v-on:click="setGroupCollapse(run.run_id, false)"
                  ></a>
                <a 
                    v-else
                    uk-icon="icon: chevron-down"
                    href="#" 
                    v-on:click="setGroupCollapse(run.run_id, true)"
                  ></a>
              </span>
            </td>
            <td class="col-state">
              <span 
                v-bind:style="'color: ' + color(run.state)" 
                v-bind:uk-icon="'icon: ' + icon(run.state) + '; ratio: 1.0'"
                >
              </span>
            </td>
            <td class="col-schedule-time"><Timestamp v-bind:time="run.times.schedule"></Timestamp></td>
            <td class="col-start-time"><Timestamp v-bind:time="run.times.running"></Timestamp></td>
            <td class="col-elapsed">{{ run.meta.elapsed === undefined ? "" : formatElapsed(run.meta.elapsed) }}</td>
            <td>
              <ActionButton
                v-for="(url, action) in run.actions" :url="url" :action="action" :key="action">
              </ActionButton>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<script>
import { each, join, map, sortBy, toPairs, values } from 'lodash'

import ActionButton from './ActionButton'
import { formatElapsed } from '../format'
import Job from './Job'
import Run from './Run'
import RunsSocket from '../RunsSocket'
import Timestamp from './Timestamp'

const icons = {
  'new'            : ['#000000', 'tag'],
  'scheduled'      : ['#a0a0a0', 'clock'],
  'running'        : ['#a0a000', 'play-circle'],
  'error'          : ['#a00060', 'warning'],
  'success'        : ['#00a000', 'check'],
  'failure'        : ['#a00000', 'close'],
}

export default { 
  name: 'runs',
  props: ['job_id'],
  components: {
    ActionButton,
    Job,
    Run,
    Timestamp,
  },

  data() { 
    return { 
      runs_socket: null,
      runs: {},
      groupCollapse: {},
    } 
  },

  computed: {
    // Organizes runs by rerun group.
    rerun_groups() {
      const runs = this.runs
      // Collect reruns of the same run into an object keyed by run ID.
      const reruns = {}
      each(values(runs), r => {
        if (r.rerun)
          (reruns[r.rerun] || (reruns[r.rerun] = [])).push(r)
        else 
          (reruns[r.run_id] || (reruns[r.run_id] = [])).splice(0, 0, r)
      })
      // Sort original runs.
      return sortBy(values(reruns), rr => {
        const r = rr[0]
        return r.times.schedule || r.times.error || r.times.running
      })
    },

  },

  methods: {
    icon(state) {
      return icons[state][1]
    },

    color(state) {
      return icons[state][0]
    },

    // FIXME: Duplicated.
    arg_str(args) {
      return join(map(toPairs(args), ([k, v]) => k + '=' + v), ' ')
    },

    getGroupCollapse(runId) {
      let c = this.groupCollapse[runId]
      if (c === undefined)
        c = this.groupCollapse[runId] = true
      return c
    },

    setGroupCollapse(runId, collapse) {
      console.log('setGroupCollapse', runId, collapse)
      this.groupCollapse[runId] = collapse
    },

    formatElapsed,
  },

  created() {
    const v = this
    this.runs_socket = new RunsSocket(undefined, this.job_id)
    this.runs_socket.open(
      (msg) => { v.runs = Object.assign({}, v.runs, msg.runs) })
  },

  destroyed() {
    this.runs_socket.close()
  },
}
</script>

<style lang="scss" scoped>

table {
  width: 100%;
}

th,
td {
  padding: 0.1rem;
}

td {
  border: none;
}

tbody td {
  max-width: 48rem;
}

.args {
  font-size: 75%;
}

tr.run-group-next {
  border-top: none;
  
  .col-job a,
  .col-args span {
    visibility: hidden;
  }
}

.col-run {
  text-align: center;
}

.col-state {
  text-align: center;
}
</style>

