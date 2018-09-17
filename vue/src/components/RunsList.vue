<template lang="pug">
div
  span(style="width: 10em; display: inline-block").field-label
    | {{ rerunGroups.length }} runs match
  Pagination.field-label(style="display: inline-block" :page.sync="page" :num-pages="numPages")

  table
    colgroup
      col(style="min-width: 10rem; max-width: 12rem;")
      col(style="min-width: 10rem; max-width: 100%;")
      col(style="width: 4rem")
      col(style="width: 4rem")
      col(style="width: 4rem")
      col(style="width: 10rem")
      col(style="width: 10rem")
      col(style="width: 6rem")
      col(style="width: 4rem")

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
import _, { filter, join, map, sortBy, toPairs } from 'lodash'
import moment from 'moment-timezone'

import ActionButton from './ActionButton'
import { formatElapsed } from '../time'
import Job from './Job'
import Pagination from './Pagination'
import Run from './Run'
import { makeJobPredicate, makeStatePredicate, groupReruns } from '../runs'
import State from './State'
import store from '@/store.js'
import Timestamp from './Timestamp'

function minTime(run) {
  return moment(_.min(_.filter([ 
    run.times.schedule,
    run.times.running,
  ])))
}

function maxTime(run) {
  return moment(_.max(_.filter([
    run.times.schedule,
    run.times.running,
    run.times.error,
    run.times.success,
    run.times.failure,
  ])))
}

export default { 
  name: 'runs',
  props: {
    jobFilter: {type: String, default: ''},
    stateFilter: {type: Array, default: () => []},
    startTime: {default: null},
    endTime: {default: null},
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
      store,
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

    timePredicate() {
      const start = this.startTime
      const end = this.endTime
      if (start !== null && end !== null)
        return r => start <= maxTime(r) && minTime(r) < end
      else if (start !== null)
        return r => start <= maxTime(r)
      else if (end !== null)
        return r => minTime(r) < end
      else
        return r => true
    },

    // Array of rerun groups, each an array of runs that are reruns of the
    // same run.  Groups are filtered by current filters, and sorted.
    rerunGroups() {
      // Group runs together by rerun.
      let reruns = groupReruns(this.store.state.runs)

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
            && _.some(_.map(group, this.timePredicate))
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

}
</script>

<style lang="scss" scoped>
@import 'src/styles/base.scss';

table {
  width: 100%;
  margin-top: 1rem;
  border-spacing: 0;
  border-collapse: collapse;
}

th {
  @extend .field-label;
  border-bottom: 2px solid #eee;
  padding-bottom: 0.3rem;
  font-weight: inherit;
}

tbody tr {
  border-top: 1px solid $apsis-grid-color;
}

td {
  padding-top: 0.35rem;
  padding-bottom: 0.2rem;
}

tr.run-group-next {
  border-top: none;
  
  .col-job a,
  .col-args span {
    visibility: hidden;
  }
}

.col-job, .col-args {
  text-align: left;
}

.col-run {
  text-align: center;
}

.col-reruns {
  text-align: center;
}

.col-state {
  text-align: center;
}

.col-schedule-time, .col-start-time {
  text-align: left;
}

.col-elapsed {
  padding-right: 1em;
  text-align: right;
  white-space: nowrap;
}

.col-actions {
  text-align: center;
  button {
    font-size: 80%;
    line-height: 1.4;
  }
}

// FIXME
.uk-dropdown {
  padding: 12px;
  min-width: 0;
}
</style>

