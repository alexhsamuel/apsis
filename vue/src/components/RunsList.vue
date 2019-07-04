<template lang="pug">
div
  table.runlist
    colgroup
      col(style="width: 10rem")
      col(style="width: 10rem")
      col(style="width: 4rem")
      col(style="width: 4rem")
      col(style="min-width: 10rem; max-width: 12rem;")
      col(style="min-width: 10rem; max-width: 100%;")
      col(style="width: 4rem")
      col(style="width: 6rem")
      col(style="width: 4rem")

    thead
      tr
        td(colspan=2 style="padding-left: 14px;")
          | {{ runs.length }} Runs
        td(colspan=2)
          Pagination.pagination(v-if="pageSize" style="display: inline-block" :page.sync="page" :num-pages="numPages")
        td(colspan=5)

      tr
        th.col-schedule-time Schedule
        th.col-start-time Start
        th.col-reruns Runs
        th.col-state State
        th.col-job Job
        th.col-args Args
        th.col-run Run
        th.col-elapsed Elapsed
        th.col-actions Actions

    tbody
      template(v-for="group in pageGroups")
        tr( 
          v-for="(run, index) in group.visible(getGroupCollapse(group.id))" 
          :key="run.run_id"
          :class="{ 'run-group-next': index > 0 }"
        )
          td.col-schedule-time
            Timestamp(:time="run.times.schedule")
          td.col-start-time
            Timestamp(:time="run.times.running")
          td.col-reruns
            span(v-show="index == 0 && group.length > 1")
              | {{ group.length > 1 ? group.length : "" }}
              a(
                v-bind:uk-icon="groupIcon(group.id)"
                v-on:click="toggleGroupCollapse(group.id)"
              )
          td.col-state
            State(:state="run.state")
          td.col-job
            Job(v-if="run.run_id === group.id" :job-id="run.job_id")
          td.col-args
            span(v-if="run.run_id === group.id" ) {{ arg_str(run.args) }}
          td.col-run
            Run(:run-id="run.run_id")
          td.col-elapsed
            RunElapsed(:run="run")
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
import { entries, filter, groupBy, join, map, sortBy, toPairs } from 'lodash'

import ActionButton from './ActionButton'
import { formatElapsed } from '../time'
import Job from './Job'
import Pagination from './Pagination'
import Run from './Run'
import RunElapsed from '@/components/RunElapsed'
import * as runsFilter from '@/runsFilter.js'
import State from './State'
import StatesSelect from '@/components/StatesSelect'
import store from '@/store.js'
import Timestamp from './Timestamp'

function sortTime(run) {
  return run.times.schedule || run.times.running || run.times.error
}

export default { 
  name: 'RunsList',
  props: {
    p: {type: Number, default: 0},
    query: {type: String, default: ''},
    pageSize: {type: Number, default: null},
  },

  components: {
    ActionButton,
    Job,
    Pagination,
    Run,
    RunElapsed,
    State,
    StatesSelect,
    Timestamp,
  },

  data() { 
    return { 
      groupCollapse: {},
      page: this.p,
      store,
    } 
  },

  watch: {
    query(query) { 
      // When filters change, go back to page 0.
      this.page = 0
    },

    page(page) {
      // Let the parent know the page has changed.
      this.$emit('p', page)
    }
  },

  computed: {
    jobPredicate() {
      // FIXME: Maybe the parent should provide a predicate directly?
      return runsFilter.makePredicate(this.query)
    },

    runs() {
      return filter(this.store.state.runs, this.jobPredicate)
    },

    // Array of rerun groups, each an array of runs that are reruns of the
    // same run.  Groups are filtered by current filters, and sorted.
    groups() {
      const RUN_STATE_GROUPS = {
          // Scheduled (and new) runs together.
          'new': 'S',
          'scheduled': 'S',
          // Blocked runs.
          'blocked': 'B',
          // Running runs.
          'running': 'R',
          // Completed runs together.
          'success': 'C',
          'failure': 'C',
          'error': 'C',
      }

      function key(run) {
        return run.run_group
          || (run.job_id + '\0' + Object.values(run.args).join('\0'))
      }

      function groupKey(run) {
        const sgrp = RUN_STATE_GROUPS[run.state]
        return sgrp + (
          // Blocked and running runs are never grouped.
          (sgrp === 'B' || sgrp === 'R') ? run.run_id
          // Runs in other state are grouped by instance.
          : key(run)
        )
      }

      let groups = entries(groupBy(this.runs, groupKey))

      // For each group, select the principal run for the group.  This is the
      // run that is shown when the group is collapsed.
      groups = map(groups, ([key, runs]) => {
        // Sort runs within each group.
        runs = sortBy(runs, sortTime)

        // Select the principal run for this group.
        // - new/scheduled: the earliest run
        // - blocked, running: not grouped
        // - completed: the latest run
        const sgrp = key[0]
        const run = runs[sgrp === 'C' ? runs.length - 1 : 0]

        // Build a convience structure for the group.
        return {
          id: run.run_id,
          length: runs.length,
          run: run,
          runs: runs,
          visible: collapsed => collapsed ? [run] : runs,
        }
      })

      // Sort groups by time of the principal run.
      groups = sortBy(groups, g => sortTime(g.run))
      console.log('num groups:', groups.length)

      return groups
    },

    numPages() { return Math.ceil(this.groups.length / this.pageSize) },
    pageStart() { return this.page * this.pageSize },
    pageEnd() { return Math.min(this.pageStart + this.pageSize, this.groups.length) },

    pageGroups() { 
      return this.pageSize ? this.groups.slice(this.pageStart, this.pageEnd) : this.groups
    },

  },

  methods: {
    // FIXME: Duplicated.
    arg_str(args) {
      return join(map(toPairs(args), ([k, v]) => k + '=' + v), ' ')
    },

    getGroupCollapse(id) {
      let c = this.groupCollapse[id]
      if (c === undefined)
        this.$set(this.groupCollapse, id, c = true)
      return c
    },

    toggleGroupCollapse(id) {
      this.$set(this.groupCollapse, id, !this.getGroupCollapse(id))
    },

    getVisibleRunsInGroup(principal, runs) {
      return this.getGroupCollapse(principal.run_id) ? [principal] : runs
    },

    groupIcon(runId) {
      return this.getGroupCollapse(runId) ? 'icon: chevron-down' : 'icon: chevron-up'
    },

    formatElapsed,
  },

}
</script>

<style lang="scss">
table.runlist {
  width: 100%;
  border-spacing: 0;
  border-collapse: collapse;

  th, td {
    &:first-child {
      padding-left: 12px;
    }
    &:last-child {
      padding-right: 12px;
    }
  }

  thead {
    background-color: #f6faf8;
    tr {
      border: 1px solid #e1e8e4;
    }
    td, th {
      font-weight: normal;
      padding: 12px 4px;
    }
  }

  tbody tr {
    border: 1px solid #e1e8e4;
    &:not(:last-child) {
      border-bottom: none;
    }
    border-radius: 3px;
    overflow: auto;
    &.run-group-next {
      border-top: none;
    }
    &:hover {
      background-color: #fafafa;
    }
    td {
      padding: 4px 4px 5px 4px;
    }
  }

  .col-job, .col-args, .col-schedule-time, .col-start-time {
    text-align: left;
  }

  .col-run, .col-state {
    text-align: center;
  }

  .col-reruns {
    text-align: right;
    font-size: 90%;
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
}
</style>

<style lang="scss" scoped>
// FIXME
.uk-dropdown {
  padding: 12px;
  min-width: 0;
}
</style>

