<template>
  <div>
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
          <th class="col-actions">Actions</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="rerunGroup in rerun_groups">
          <tr 
              v-for="(run, index) in groupRuns(rerunGroup)" 
              :key="run.run_id"
              v-bind:class="{ 'run-group-next': index > 0 }"
            >
            <td class="col-job"><Job :job-id="run.job_id"></Job></td>
            <td class="col-args"><span>{{ arg_str(run.args) }}</span></td>
            <td class="col-run"><Run :run-id="run.run_id"></Run></td>
            <td class="col-reruns">
              <span v-show="index == 0 && rerunGroup.length > 1">
                {{ rerunGroup.length > 1 ? rerunGroup.length - 1 : "" }}
                <a 
                    v-bind:uk-icon="groupIcon(run.rerun)"
                    v-on:click="setGroupCollapse(run.rerun, !getGroupCollapse(run.rerun))"
                  ></a>
              </span>
            </td>
            <td class="col-state"><State v-bind:state="run.state"></State></td>
            <td class="col-schedule-time"><Timestamp v-bind:time="run.times.schedule"></Timestamp></td>
            <td class="col-start-time"><Timestamp v-bind:time="run.times.running"></Timestamp></td>
            <td class="col-elapsed">{{ run.meta.elapsed === undefined ? "" : formatElapsed(run.meta.elapsed) }}</td>
            <td class="col-actions">
              <div v-if="Object.keys(run.actions).length > 0" class="uk-inline">
                <button class="uk-button uk-button-default uk-button-small actions-button" type="button">
                  <span uk-icon="icon: menu; ratio: 0.75"></span>
                </button>
                <div uk-dropdown="pos: left-center">
                  <ul class="uk-nav uk-dropdown-nav">
                    <li><ActionButton
                        v-for="(url, action) in run.actions" 
                        :key="action"
                        :url="url" 
                        :action="action" 
                        :button="true"
                      ></ActionButton></li>
                  </ul>
                </div>
              </div>
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
import State from './State'
import Timestamp from './Timestamp'

export default { 
  name: 'runs',
  props: ['job_id'],
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
    // FIXME: Duplicated.
    arg_str(args) {
      return join(map(toPairs(args), ([k, v]) => k + '=' + v), ' ')
    },

    getGroupCollapse(runId) {
      let c = this.groupCollapse[runId]
      if (c === undefined)
        this.$set(this.groupCollapse, runId, c = true)
      return c
    },

    setGroupCollapse(runId, collapse) {
      this.$set(this.groupCollapse, runId, collapse)
    },

    groupRuns(group) {
      const rerun = group[0].rerun
      return this.getGroupCollapse(rerun) ? [group[group.length - 1]] : group
    },

    groupIcon(runId) {
      return this.getGroupCollapse(runId) ? 'icon: chevron-down' : 'icon: chevron-up'
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

td.col-reruns {
  text-align: center;
}

.col-state {
  text-align: center;
}

th.col-elapsed {
  text-align: center;
}

td.col-elapsed {
  padding-left: 1em;
  padding-right: 1em;
  text-align: right;
}

.col-actions {
  text-align: center;
}

.actions-button {
  font-size: 80%;
  line-height: 1.4;
}

// FIXME
.uk-dropdown {
  padding: 12px;
  min-width: 0;
}
</style>

