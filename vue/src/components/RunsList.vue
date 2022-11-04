<template lang="pug">
div
  div.time-controls(
    v-if="timeControls"
  )
    DropList.counts(
      style="grid-row: 2; grid-column: 1;"
      :value="1"
      v-on:input="maxRuns = COUNTS[$event] / 2"
    )
      div(
        v-for="count in COUNTS"
      )
        div {{ count }} runs

    div(style="grid-row: 1; grid-column: 1;") Show:

    div.field(:style="{'grid-row': asc ? 1 : 3, 'grid-column': 2}")
      | {{ formatTime(groups.earlierTime, store.state.timeZone) }}
    div.field(:style="{'grid-row': asc ? 3 : 1, 'grid-column': 2}")
      | {{ formatTime(groups.laterTime, store.state.timeZone) }}

    button(
      :style="{'grid-row': asc ? 1 : 3, 'grid-column': 3}"
      v-on:click="showTime(groups.earlierTime)"
      :disabled="groups.earlierCount == 0"
    ) Earlier
    button(
      style="grid-row: 2; grid-column: 3;"
      v-on:click="showTime('now')"
      :disabled="time === 'now'"
    ) Now
    button(
      :style="{'grid-row': asc ? 3 : 1, 'grid-column': 3}"
      v-on:click="showTime(groups.laterTime)"
      :disabled="groups.laterCount == 0"
    ) Later

    div(style="grid-row: 2; grid-column: 2")
      button.toggle.left(
        :disabled="asc"
        v-on:click="asc = true"
      ) &nbsp; Fwd &#8595;
      button.toggle.right(
        :disabled="!asc"
        v-on:click="asc = false"
      ) &nbsp; Bwd &#8593;

  table.runlist
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
      tr(v-if="groups.groups.length == 0")
        td.note(colspan="9") No runs.

      tr(v-if="(asc ? groups.earlierCount : groups.laterCount) > 0")
        td.note(colspan="9")
          | {{ asc ? groups.earlierCount : groups.laterCount }}
          | {{ asc ? 'earlier' : 'later' }} rows not shown
          button(
            v-on:click="showTime(asc ? groups.earlierTime : groups.laterTime)"
          ) Show {{ asc ? 'Earlier' : 'Later' }}

      //- Each group is represented by a single run, groupRun, but may contain
      //- one or more runs, groupRuns.  The group's expand state is keyed by
      //- groupRun.run_id.
      template(v-for="run, i in groups.groups")
        tr(v-if="i === groups.nowIndex")
          td.timeSeparator(colspan="9")
            div

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
            | {{ historyCount(groups.counts[run.run_id]) }}
          td.col-schedule-time
            .tooltip
              Timestamp(:time="run.times.schedule")
              span.tooltiptext(v-if="run.state == 'scheduled'") in {{ startTime(run) }}
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

      tr(v-if="(asc ? groups.laterCount : groups.earlierCount) > 0")
        td.note(colspan="9")
          | {{ asc ? groups.laterCount : groups.earlierCount }}
          | {{ asc ? 'later' : 'earlier' }} rows not shown
          button(
            v-on:click="showTime(asc ? groups.laterTime : groups.earlierTime)"
          ) Show {{ asc ? 'Later' : 'Earler' }}

</template>

<script>
import { entries, filter, flatten, groupBy, isEqual, keys, map, sortBy, sortedIndexBy, uniq } from 'lodash'

import { formatElapsed, formatTime } from '../time'
import DropList from '@/components/DropList'
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

    timeControls: {type: Boolean, default: false},
  },

  components: {
    DropList,
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
      time: 'now',
      maxRuns: 50,
      COUNTS: [20, 50, 100, 200, 500, 1000],
      asc: true,
    } 
  },

  computed: {
    jobPredicate() {
      // FIXME: Maybe the parent should provide a predicate directly?
      return this.query ? runsFilter.makePredicate(this.query) : null
    },

    earlierRow() { return this.asc ? 1 : 3 },
    laterRow() { return this.asc ? 3 : 1 },

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
    allGroups() {
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

    groups() {
      let start = new Date()
      const groups = this.allGroups
      let runs = groups.groups   // FIXME
      let now = (new Date()).toISOString()
      const time = this.time === 'now' ? now : this.time
      let timeIndex = sortedIndexBy(runs, { time_key: time }, r => r.time_key)

      let earlierTime
      let earlierCount
      if (this.timeControls && this.maxRuns < timeIndex) {
        // Don't truncate in the middle of a timestamp.
        earlierCount = timeIndex - this.maxRuns
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
      if (this.timeControls && this.maxRuns < runs.length - timeIndex) {
        // Don't truncate in the middle of a timestamp.
        laterCount = runs.length - (timeIndex + this.maxRuns)
        laterTime = runs[runs.length - laterCount].time_key
        runs = runs.slice(0, runs.length - laterCount)
      }
      else {
        laterTime = null
        laterCount = 0
      }

      let nowIndex
      if (runs.length > 0 && runs[0].time_key < now && now < runs[runs.length - 1].time_key)
        nowIndex = sortedIndexBy(runs, { time_key: now }, r => r.time_key)

      if (!this.asc)
        runs.reverse()

      console.log('runs:', this.store.state.runs.size, 'filtered:', this.runs.length, 'groups:', runs.length, 'earlier:', earlierCount, 'later:', laterCount, 'in:', (new Date() - start) * 0.001)
      return {
        groups: runs,
        counts: groups.counts,
        nowIndex,
        time,
        earlierTime,
        earlierCount,
        laterTime,
        laterCount,
      }
    },
  },

  methods: {
    formatElapsed,
    formatTime,

    historyCount(count) {
      return count === 1 ? '' : count === 2 ? '+1 run\u00a0\u00a0' : '+' + (count - 1) + ' runs'
    },

    showTime(time) {
      this.time = 
        Math.abs(new Date(time) - new Date()) < 60000 ? 'now'
        : time
    },

    startTime(run) {
      if (run.times.schedule) {
        const now = this.store.state.time
        const schedule = new Date(run.times.schedule)
        return formatElapsed((schedule - now) * 1e-3)
      }
      else
        return ''
    }
  },

}
</script>

<style lang="scss" scoped>
@import '@/styles/index.scss';

.time-controls {
  display: inline-grid;
  grid-template-columns: repeat(3, auto);
  grid-template-rows:  repeat(3, 1fr);
  gap: 4px 12px;
  justify-items: center;
  align-items: baseline;

  white-space: nowrap;
  // text-transform: uppercase;

  line-height: 28px;
  
  > * {
    width: 100%;
    box-sizing: border-box;
  }

  .counts {
    width: 7em;
    height: 32px;
    text-align: right;
  }

  .field {
    width: 100%;
    border: 1px solid $apsis-frame-color;
    text-align: center;
    background: #fcfcfc;
  }

  .toggle {
    &[disabled] {
      color: black;
      background: #f0f0f0;
    }
    &.left:not(:hover) {
      border-right-color: transparent;
    }
    &.right:not(:hover) {
      border-left-color: transparent;
    }
  }

  button {
    line-height: 28px;
    height: 30px;
    vertical-align: baseline;
  }
}

table {
  @extend .widetable;

  .note {
    height: 24px;

    button {
      margin-left: 8px;
      padding: 0 12px;
      line-height: 20px;
      height: 24px;
    }
  }

  .col-job, .col-args, .col-arg {
    text-align: left;
  }

  .col-run, .col-state, .col-operations {
    text-align: center;
  }

  .col-schedule-time, .col-start-time {
    text-align: right;
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
    div {
      border-top: 4px solid #f8f8f8;
    }
    padding: 10px 12px 10px 0;
  }
}
</style>
