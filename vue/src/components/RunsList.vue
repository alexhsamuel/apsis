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
        th.col-reruns History
        th.col-schedule-time Schedule
        th.col-start-time Start
        th.col-elapsed Elapsed
        th.col-operations Operations

    tbody
      tr(v-if="trimmedGroups.groups.length == 0")
        td.note(colspan="9") No runs.

      tr(v-if="trimmedGroups.earlierCount > 0")
        td.note(colspan="9")
          | {{ trimmedGroups.earlierCount }} earlier rows not shown

      //- Each group is represented by a single run, groupRun, but may contain
      //- one or more runs, groupRuns.  The group's expand state is keyed by
      //- groupRun.run_id.
      template(v-for="run, i in trimmedGroups.groups")
        tr(v-if="i === trimmedGroups.timeIndex")
          td.timeSeparator(colspan="9")

        tr(:key="run.run_id")
          //- Show job name if enabled by 'showJob' and this is the group run.
          td.col-job(v-if="showJob")
            //- Is this the group run?
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
            RunArgs(:args="run.args")

          td.col-run
            Run(:run-id="run.run_id")
          td.col-state
            State(:state="run.state")
          //- FIXME: Click to run with history expanded.
          td.col-reruns
            | {{ historyCount(trimmedGroups.counts[run.run_id]) }}
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

      tr(v-if="trimmedGroups.laterCount > 0")
        td.note(colspan="9")
          | {{ trimmedGroups.laterCount }} later rows not shown

</template>

<script>
import { entries, filter, flatten, groupBy, isEqual, keys, map, sortBy, sortedIndexBy, uniq } from 'lodash'

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

    time: {type: Date, default: null},
    maxEarlierRuns: {type: Number, default: 100},
    maxLaterRuns: {type: Number, default: 100},
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
      let t0 = new Date()
      let t1

      let runs = Array.from(this.store.state.runs.values())
      t1 = new Date()
      console.log('runs-values', (t1 - t0) * 0.001)
      t0 = t1

      if (this.path) {
        const predicate = (new runsFilter.JobIdPathPrefix(this.path)).predicate
        runs = filter(runs, predicate)
        t1 = new Date()
        console.log('runs-path-prefix', (t1 - t0) * 0.001)
        t0 = t1
      }
      if (this.args) {
        runs = filter(runs, run => isEqual(run.args, this.args))
        t1 = new Date()
        console.log('runs-args-filter', (t1 - t0) * 0.001)
        t0 = t1
      }
      if (this.jobPredicate) {
        runs = filter(runs, this.jobPredicate)
        t1 = new Date()
        console.log('runs-job-predicate', (t1 - t0) * 0.001)
        t0 = t1
      }

      // Sort by time.
      t1 = new Date()
      console.log('runs-before-sort', (t1 - t0) * 0.001)
      t0 = t1

      runs = sortBy(runs, r => r.time_key)

      t1 = new Date()
      console.log('runs-end', (t1 - t0) * 0.001)
      t0 = t1
      return runs
    },
  
    params() {
      return uniq(flatten(map(this.runs, run => keys(run.args))))
    },

    // Array of rerun groups, each an array of runs that are reruns of the
    // same run.  Groups are filtered by current filters, and sorted.
    groups() {
      let t0 = new Date()
      let t1

      let groups
      let counts = {}
      if (this.groupRuns) {
        const runs = this.runs
        t1 = new Date()
        console.log('groups-runs', (t1 - t0) * 0.001)
        t0 = t1

        // For each group, select the principal run for the group to show.
        groups = map(entries(groupBy(runs, r => r.group_key)), ([key, runs]) => {
          // Select the principal run for this group.
          // - new/scheduled: the earliest run
          // - blocked, running: not grouped
          // - completed: the latest run
          const sgrp = key[0]
          const run = runs[sgrp === 'C' ? runs.length - 1 : 0]

          counts[run.run_id] = runs.length
          return run
        })

        t1 = new Date()
        console.log('groups-groupBy', (t1 - t0) * 0.001)
        t0 = t1
      }

      else {
        groups = this.runs
        groups.forEach(r => { counts[r.run_id] = 1 })
      }

      // Sort groups by time.
      groups = sortBy(groups, r => r.time_key)

      t1 = new Date()
      console.log('groups-end', (t1 - t0) * 0.001)
      t0 = t1

      return {
        groups,
        counts,
      }
    },

    trimmedGroups() {
      let start = new Date()
      const groups = this.groups
      let runs = groups.groups  // FIXME: !!
      const time = (this.time || new Date()).toISOString()
      let timeIndex = sortedIndexBy(runs, { time_key: time }, r => r.time_key)

      let earlierTime
      let earlierCount
      if (this.maxEarlierRuns < timeIndex) {
        // Don't truncate in the middle of a timestamp.
        earlierCount = timeIndex - this.maxEarlierRuns
        earlierTime = runs[earlierCount].time_key
        runs = runs.slice(earlierCount)
        timeIndex -= earlierCount
      }
      else {
        earlierTime = null
        earlierCount = 0
      }

      let laterTime
      let laterCount
      if (this.maxLaterRuns < runs.length - timeIndex) {
        // Don't truncate in the middle of a timestamp.
        laterCount = runs.length - (timeIndex + this.maxLaterRuns)
        laterTime = runs[runs.length - laterCount].time_key
        runs = runs.slice(0, runs.length - laterCount)
      }
      else {
        laterTime = null
        laterCount = 0
      }

      console.log('runs:', this.store.state.runs.size, 'filtered:', this.runs.length, 'groups:', runs.length, 'earlier:', earlierCount, 'later:', laterCount, 'in:', (new Date() - start) * 0.001)
      return {
        groups: runs,
        counts: groups.counts,
        timeIndex,
        earlierTime,
        earlierCount,
        laterTime,
        laterCount,
      }
    },
  },

  methods: {
    formatElapsed,

    historyCount(count) {
      return count === 1 ? '' : count === 2 ? '+1 run\u00a0\u00a0' : '+' + (count - 1) + ' runs'
    }
  },

}
</script>

<style lang="scss">
table.runlist {
  .note {
    height: 24px;
  }

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

  .timeSeparator {
    border-top: 1px solid #eee;
    padding: 0;
  }
}
</style>

