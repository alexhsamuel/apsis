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
        th.col-operations Operations

    tbody
      tr(v-if="groups.groups.length == 0")
        td.note(colspan="8") No runs.

      tr(v-if="groups.omitCompleted > 0")
        td.note(colspan="8") {{ groups.omitCompleted }} completed runs not shown

      //- Each group is represented by a single run, groupRun, but may contain
      //- one or more runs, groupRuns.  The group's expand state is keyed by
      //- groupRun.run_id.
      template(v-for="([groupRun, groupRuns]) in groups.groups")
        tr( 
          v-for="(run, index) in getGroupVisibleRuns(groupRun, groupRuns)" 
          :key="run.run_id"
          :class="{ 'run-group-next': index > 0, 'highlight-run': run.run_id === highlightRunId }"
        )
          //- Show job name if enabled by 'showJob' and this is the group run.
          td.col-job(v-if="showJob")
            //- Is this the group run?
            div(v-if="run.run_id === groupRun.run_id")
              Job(:job-id="run.job_id")
              JobLabel(
                v-for="label in run.labels || []"
                :label="label"
                :key="label"
              )
          template(v-if="argColumnStyle === 'separate'")
            td(v-for="param in params") {{ run.args[param] || '' }}
          //- Else all together.
          td.col-args(v-if="argColumnStyle === 'combined'")
            span(v-if="run.run_id === groupRun.run_id")
              RunArgs(:args="run.args")

          td.col-run
            Run(:run-id="run.run_id")
          td.col-state
            State(:state="run.state")
          td.col-reruns
            span(
              v-if="index == 0 && groupRuns.length > 1"
              v-on:click="toggleGroupExpand(groupRun.run_id)"
            )
              | {{ groupRuns.length }}
              TriangleIcon(:direction="getGroupExpand(groupRun.run_id) ? 'up' : 'down'")
          td.col-schedule-time
            Timestamp(:time="run.times.schedule")
          td.col-start-time
            Timestamp(:time="run.times.running")
          td.col-elapsed
            RunElapsed(:run="run")
          td.col-operations
            HamburgerMenu(v-if="run.operations.length > 0")
              OperationButton(
                v-for="operation in run.operations" 
                :key="operation"
                :run_id="run.run_id"
                :operation="operation" 
                :button="true"
              )

      tr(v-if="groups.omitScheduled > 0")
        td.note(colspan="8") {{ groups.omitScheduled }} scheduled runs not shown

</template>

<script>
import { entries, filter, flatten, groupBy, isEqual, keys, map, sortBy, uniq } from 'lodash'

import { formatElapsed } from '../time'
import HamburgerMenu from '@/components/HamburgerMenu'
import Job from '@/components/Job'
import JobLabel from '@/components/JobLabel'
import OperationButton from './OperationButton'
import Run from '@/components/Run'
import RunArgs from '@/components/RunArgs'
import RunElapsed from '@/components/RunElapsed'
import * as runsFilter from '@/runsFilter.js'
import State from '@/components/State'
import StatesSelect from '@/components/StatesSelect'
import store from '@/store.js'
import Timestamp from './Timestamp'
import TriangleIcon from '@/components/icons/TriangleIcon'

function sortTime(run) {
  return run.times.schedule || run.times.running || run.times.error
}

export default { 
  name: 'RunsList',
  props: {
    query: {type: String, default: ''},
    // Either a job ID path prefix; can be a full job ID.
    path: {type: String, default: null},

    // Args to match.  If not null, shows only runs with exact args match.
    args: {type: Object, default: null},

    // If true, show the job ID column.
    showJob: {type: Boolean, default: true},

    // If true, group together related runs.
    groupRuns: {type: Boolean, default: true},

    // If not null, highlight the run with this run ID.
    highlightRunId: {type: String, default: null},

    // How to indicate args:
    // - 'combined' for a single args column
    // - 'separate' for one column per param, suitable for runs of a single job
    // - 'none' for no args at all, suitable for runs of a single (job, args)
    argColumnStyle : {type: String, default: 'combined'},

    // Max number of runs to show.  If negative, show all runs.
    maxScheduledRuns: {type: Number, default: -1},
    maxCompletedRuns: {type: Number, default: -1},
  },

  components: {
    HamburgerMenu,
    Job,
    JobLabel,
    OperationButton,
    Run,
    RunArgs,
    RunElapsed,
    State,
    StatesSelect,
    Timestamp,
    TriangleIcon,
  },

  data() {
    return { 
      groupExpand: {},
      store,
    } 
  },

  computed: {
    jobPredicate() {
      // FIXME: Maybe the parent should provide a predicate directly?
      return this.query ? runsFilter.makePredicate(this.query) : null
    },

    /** Runs, after filtering.  */
    runs() {
      let runs = this.store.state.runs

      if (this.path)
        runs = filter(runs, (new runsFilter.JobIdPathPrefix(this.path)).predicate)
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
          'starting': 'R',
          'running': 'R',
          // Completed runs together.
          'success': 'C',
          'failure': 'C',
          'error': 'C',
          'skipped': 'C',
      }

      // Select run to show.
      let runs = this.runs
      let omitC = 0
      let omitS = 0
      if (this.maxScheduledRuns >= 0 || this.maxCompletedRuns >= 0) {
        // Count up runs by run state group.
        const counts = {}
        for (const run of runs) {
          let grp = RUN_STATE_GROUPS[run.state]
          counts[grp] = (counts[grp] | 0) + 1
        }

        const S = counts['S'] | 0
        if (this.maxScheduledRuns < S)
          omitS = S - this.maxScheduledRuns

        const C = counts['C'] | 0
        if (this.maxCompletedRuns < C)
          omitC = C - this.maxCompletedRuns

        // Now actually omit them.
        if (omitC > 0 || omitS > 0) {
          let c = 0
          let s = S - omitS
          runs = filter(runs, run => {
            const grp = RUN_STATE_GROUPS[run.state]
            return grp === 'C' ? omitC <= c++
                 : grp === 'S' ? s-- > 0
                 : true
          })
        }
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

      let groups = entries(groupBy(runs, this.groupRuns ? groupKey : r => r.run_id))

      // For each group, select the principal run for the group.  This is the
      // run that is shown when the group is collapsed (i.e. not expanded).
      groups = map(groups, ([key, runs]) => {
        // Sort runs within each group.
        runs = sortBy(runs, sortTime)

        // Select the principal run for this group.
        // - new/scheduled: the earliest run
        // - blocked, running: not grouped
        // - completed: the latest run
        const sgrp = key[0]
        const run = runs[sgrp === 'C' ? runs.length - 1 : 0]

        // Return the single run representing the group, and all runs in the group.
        return [run, runs]
      })

      // Sort groups by time of the principal run.
      groups = sortBy(groups, ([run, _]) => sortTime(run))

      return {
        groups,
        omitCompleted: omitC,
        omitScheduled: omitS,
      }
    },

  },

  methods: {
    getGroupExpand(id) {
      return !!this.groupExpand[id]
    },

    toggleGroupExpand(id) {
      this.$set(this.groupExpand, id, !this.groupExpand[id])
    },

    getGroupVisibleRuns(groupRun, groupRuns) {
      return this.getGroupExpand(groupRun.run_id) ? groupRuns : [groupRun]
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

  .col-run, .col-state, .col-operations {
    text-align: center;
  }

  .col-reruns {
    text-align: right;
    white-space: nowrap;

    & > span {
      // Absolutely no idea why this is necessary.
      position: relative;
      top: -4px;
    }
  }

  .col-elapsed {
    padding-right: 1em;
    text-align: right;
    white-space: nowrap;
  }

  .highlight-run {
    background: #f6faf8;
  }
}
</style>

