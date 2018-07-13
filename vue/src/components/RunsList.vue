<template>
  <div>
   <br>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>State</th>
          <th>Schedule</th>
          <th>Start</th>
          <th>Elapsed</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="rerun_group in rerun_groups">
          <tr class="group">
            <td colspan="6">
              <span class="job-link" v-on:click="$router.push({ name: 'job', params: { job_id: rerun_group[0].job_id } })">{{ rerun_group[0].job_id }}</span>
              {{ arg_str(rerun_group[0].args) }}
            </td>
          </tr>
          <tr v-for="run in rerun_group" :key="run.run_id" class="run">
            <td class="run-link" v-on:click="$router.push({ name: 'run', params: { run_id: run.run_id } })">{{ run.run_id }}</td>
            <td>{{ run.state }}</td>
            <td><Timestamp v-bind:time="run.times.schedule"></Timestamp></td>
            <td><Timestamp v-bind:time="run.times.running"></Timestamp></td>
            <td class="rt">{{ run.meta.elapsed === undefined ? "" : formatElapsed(run.meta.elapsed) }}</td>
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
import RunsSocket from '../RunsSocket'
import Timestamp from './Timestamp'

export default { 
  name: 'runs',
  props: ['job_id'],
  components: {
    ActionButton,
    Timestamp,
  },

  data() { 
    return { 
      runs_socket: null,
      runs: {},
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

<style scoped>
table {
  width: 100%;
}

tbody tr.run:hover {
  background: #f0fff8;
}

th,
td {
  padding: 0.1rem;
}

td {
  border: none;
}

.group td {
  spacing-top: 1cm;
  padding-top: 0.5rem;
  border-top: 1px solid #e0e0e0;
}

tbody td {
  max-width: 48rem;
}

.args {
  font-size: 75%;
}

</style>

