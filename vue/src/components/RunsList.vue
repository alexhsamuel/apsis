<template lang="pug">
div
  span(style="width: 10em; display: inline-block").field-label
    | {{ rerunGroups.length }} runs match
  Pagination.field-label(style="display: inline-block" :page.sync="page" :num-pages="numPages")

  table.uk-table.uk-table-divider.uk-table-hover.uk-table-small.uk-table-justify
    thead
      tr
        th.col-job Job
        th.col-args Args
        th.col-run Run
        th.col-reruns Reruns
        th.col-state State
        th.col-schedule-time Schedule
        th.col-start-time Start
        th.col-elapsed Elapsed
        th.col-actions Actions

    tbody
      template(v-for="rerunGroup in pageRuns")
        tr( 
          v-for="(run, index) in groupRuns(rerunGroup)" 
          :key="run.run_id"
          :class="{ 'run-group-next': index > 0 }"
        )
          td.col-job
            Job(:job-id="run.job_id")
          td.col-args
            span {{ arg_str(run.args) }}
          td.col-run
            Run(:run-id="run.run_id")
          td.col-reruns
            span(v-show="index == 0 && rerunGroup.length > 1")
              | {{ rerunGroup.length > 1 ? rerunGroup.length - 1 : "" }}
              a(
                v-bind:uk-icon="groupIcon(run.rerun)"
                v-on:click="setGroupCollapse(run.rerun, !getGroupCollapse(run.rerun))"
              )
          td.col-state
            State(:state="run.state")
          td.col-schedule-time
            Timestamp(:time="run.times.schedule")
          td.col-start-time
            Timestamp(:time="run.times.running")
          td.col-elapsed
            | {{ run.meta.elapsed === undefined ? "" : formatElapsed(run.meta.elapsed) }}
          td.col-actions
            div.uk-inline(v-if="Object.keys(run.actions).length > 0")
              button.uk-button.uk-button-default.uk-button-small.actions-button(type="button")
                span(uk-icon="icon: menu; ratio: 0.75")
              div(uk-dropdown="pos: left-center")
                ul.uk-nav.uk-dropdown-nav
                  li: ActionButton(
                    v-for="(url, action) in run.actions" 
                    :key="action"
                    :url="url" 
                    :action="action" 
                    :button="true"
                  )

</template>

<script>
import { filter, join, map, sortBy, toPairs } from 'lodash'

import ActionButton from './ActionButton'
import { formatElapsed } from '../format'
import Job from './Job'
import Pagination from './Pagination'
import Run from './Run'
import { makeJobPredicate, makeStatePredicate, groupReruns } from '../runs'
import RunsSocket from '../RunsSocket'
import State from './State'
import Timestamp from './Timestamp'

export default { 
  name: 'runs',
  props: {
    job_id: String,
    jobFilter: String,
    stateFilter: Array,
    pageSize: {type: Number, default: 20},
  },

  components: {
    ActionButton,
    Job,
    Pagination,
    Run,
    State,
    Timestamp,
  },

  data() { 
    return { 
      groupCollapse: {},
      page: 0,
      runs_socket: null,
      runs: {},
    } 
  },

  watch: {
    // When filters change, go back to page 0.
    jobFilter() { this.page = 0 },
    stateFilter() { this.page = 0 },
  },

  computed: {
    jobPredicate() {
      return makeJobPredicate(this.jobFilter)
    },

    statePredicate() {
      return makeStatePredicate(this.stateFilter)
    },

    // Array of rerun groups, each an array of runs that are reruns of the
    // same run.  Groups are filtered by current filters, and sorted.
    rerunGroups() {
      // Group runs together by rerun.
      let reruns = groupReruns(this.runs)

      // Filter groups.
      reruns = filter(
        reruns,
        group => {
          // Filter by the latest run in the group.
          const latest = group[group.length - 1]
          // Apply state and job/arg filters.
          return (
            this.statePredicate(latest) 
            && this.jobPredicate(latest)
          )
        }
      )

      // Sort original runs.
      return sortBy(reruns, rr => {
        const r = rr[0]
        return r.times.schedule || r.times.error || r.times.running
      })
    },

    numPages() { return Math.ceil(this.rerunGroups.length / this.pageSize) },
    pageStart() { return this.page * this.pageSize },
    pageEnd() { return Math.min(this.pageStart + this.pageSize, this.rerunGroups.length) },
    pageRuns() { return this.rerunGroups.slice(this.pageStart, this.pageEnd) },

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

