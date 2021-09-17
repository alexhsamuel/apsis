<template lang="pug">
div
  table.widetable.runlist
    colgroup
      col(v-if="showJob" style="min-width: 10rem")
      template(v-if="argColumnStyle === 'separate'")
        col(v-for="param in params")
      col(v-if="argColumnStyle === 'combined'" style="min-width: 10rem; max-width: 100%;")
      col(style="width: 4rem")
      col(style="width: 4rem")
      col(style="width: 5rem")
      col(style="width: 10rem")
      col(style="width: 10rem")
      col(style="width: 6rem")
      col(style="width: 4rem")

    thead
      tr
        th.col-job(v-if="showJob") Job
        template(v-if="argColumnStyle === 'separate'")
          th.col-arg(v-for="param in params") {{ param }}
        th.col-args(v-if="argColumnStyle == 'combined'") Args
        th.col-run Run
        th.col-state State
        th.col-reruns Runs
        th.col-schedule-time Schedule
        th.col-start-time Start
        th.col-elapsed Elapsed
        th.col-actions Actions

    tbody
      tr(v-if="groups.length == 0")
        td(colspan="8") No runs.

      template(v-for="group in groups")
        tr( 
          v-for="(run, index) in group.visible(getGroupCollapse(group.id))" 
          :key="run.run_id"
          :class="{ 'run-group-next': index > 0 }"
        )
          // Show job name if enabled by 'showJob'.
          td.col-job(v-if="showJob")
            div(v-if="run.run_id === group.id")
              Job(:job-id="run.job_id")
              JobLabel(
                v-for="label in run.labels || []"
                :label="label"
                :key="label"
              )
          template(v-if="argColumnStyle === 'separate'")
            td(v-for="param in params") {{ run.args[param] || '' }}
          // Else all together.
          td.col-args(v-if="argColumnStyle === 'combined'")
            span(v-if="run.run_id === group.id")
              RunArgs(:args="run.args")

          td.col-run
            Run(:run-id="run.run_id")
          td.col-state
            State(:state="run.state")
          td.col-reruns
            span(v-show="index == 0 && group.length > 1")
              | {{ group.length > 1 ? group.length : "" }}
              a(
                v-bind:uk-icon="groupIcon(group.id)"
                v-on:click="toggleGroupCollapse(group.id)"
              )
          td.col-schedule-time
            Timestamp(:time="run.times.schedule")
          td.col-start-time
            Timestamp(:time="run.times.running")
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
import { entries, filter, flatten, groupBy, isEqual, keys, map, sortBy, uniq } from 'lodash'

import ActionButton from './ActionButton'
import { formatElapsed } from '../time'
import Job from '@/components/Job'
import JobLabel from '@/components/JobLabel'
import Pagination from './Pagination'
import Run from '@/components/Run'
import RunArgs from '@/components/RunArgs'
import RunElapsed from '@/components/RunElapsed'
import * as runsFilter from '@/runsFilter.js'
import State from '@/components/State'
import StatesSelect from '@/components/StatesSelect'
import store from '@/store.js'
import Timestamp from './Timestamp'

function sortTime(run) {
  return run.times.schedule || run.times.running || run.times.error
}

export default { 
  name: 'RunsList',
  props: {
    query: {type: String, default: ''},
    // Either a job ID path prefix; can be a full job ID.
    // FIXME: Rename to jobIdPrefix.
    path: {type: String, default: null},
    // Args to match.  If not null, shows only runs with exact args match.
    args: {type: Object, default: null},
    showJob: {type: Boolean, default: true},
    // How to indicate args:
    // - 'combined' for a single args column
    // - 'separate' for one column per param, suitable for runs of a single job
    // - 'none' for no args at all, suitable for runs of a single (job, args)
    argColumnStyle : {type: String, default: 'combined'},
  },

  components: {
    ActionButton,
    Job,
    JobLabel,
    Pagination,
    Run,
    RunArgs,
    RunElapsed,
    State,
    StatesSelect,
    Timestamp,
  },

  data() {
    return { 
      groupCollapse: {},
      store,
    } 
  },

  computed: {
    jobPredicate() {
      // FIXME: Maybe the parent should provide a predicate directly?
      return runsFilter.makePredicate(this.query)
    },

    /** Runs, after filtering.  */
    runs() {
      let runs = this.store.state.runs

      if (this.path)
        runs = filter(runs, run => run.job_id.startsWith(this.path))
      if (this.args)
        runs = filter(runs, run => isEqual(run.args, this.args))

      return filter(runs, this.jobPredicate)
    },
  
    params() {
      return uniq(flatten(map(this.runs, run => keys(run.args))))
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

      function instanceKey(run) {
        // Assume args are in order.
        return run.job_id + '\0' + Object.values(run.args).join('\0')
      }

      function groupKey(run) {
        const sgrp = RUN_STATE_GROUPS[run.state]
        return sgrp + (
          // Blocked and running runs are never grouped.
          (sgrp === 'B' || sgrp === 'R') ? run.run_id
          // Runs in other state are grouped by instance.
          : instanceKey(run)
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

      return groups
    },

  },

  methods: {
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
  .col-job, .col-args, .col-arg, .col-schedule-time, .col-start-time {
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

