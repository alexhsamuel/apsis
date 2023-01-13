// Todo:
// - help buttons for some controls
// - add down arrow to droplists
// - button for showing/hiding controls
// - fix up job view
// - fix up run view
// - get rid of runs filter

<template lang="pug">
div
  div.controls
    template.job-controls
      .label 
        | Keywords:
        HelpButton
          p Syntax: <b>keyword keyword&hellip;</b>
          p Show only runs whose job ID matches at least one <b>keyword</b>.
      WordsInput(
        v-model="query_.keywords"
      )
      .label
        | Labels:
        HelpButton
          p Syntax: <b>label label&hellip;</b>
          p Show only runs with at least one <b>label</b>.
      WordsInput(
        v-model="query_.labels"
      )
      .label Job Path:
      PathNav(
        :path="query_.path"
        @path="query_.path = $event"
      )

    template.run-controls
      .label
        | Run Args:
        HelpButton
          p Syntax: <b>arg=value arg=value&hellip;</b>
          p Show only runs which have all run args <b>arg</b> set to corresponding <b>value</b>.
      WordsInput(
        v-model="query_.args"
      )
      .label States:
      StatesSelect(
        v-model="query_.states"
      )
      .label
        | Repeated:
        HelpButton
          p How to present repeated runs, <i>i.e.</i> runs with the same job ID and run args.
          p <b>Show</b> each run individually.
          p <b>Hide</b> repeated runs, combined by run state:
            ul
              li Hide all completed runs before the latest completed.
              li Hide all scheduled runs after the earliest scheduled.
              li Show all runs in other states.
            | An additional column shows the number of hidden runs.
      div
        button.toggle.left(
          :disabled="!query_.grouping"
          @click="query_.grouping = false"
        ) Show
        button.toggle.left(
          :disabled="query_.grouping"
          @click="query_.grouping = true"
        ) Hide

    template.time-controls(v-if="timeControls")
      //- Number of runs to show.
      .label Show:
      DropList.counts(
        :value="1"
        @input="onShowInput"
      )
        div(
          v-for="count in COUNTS"
        )
          div {{ count }} runs

      //- Show Time and earier / now / later buttons.
      .label
        | Time:
        HelpButton
          p Show the runs nearest this time, immediately before and after.
          p <b>Now</b> tracks the current time.
          p Specify another date and/or time. The arrows page backward or forward.
      div(style="display: flex;")
        button(
          style="padding: 0 4px; border-top-right-radius: 0; border-bottom-right-radius: 0;"
          v-on:click="showTime(groups.earlierTime)"
          :disabled="groups.earlierCount == 0"
        )
          TriangleIcon(
            direction="left"
          )
        TimeInput(
          v-model="query_.time"
        )
        button(
          style="padding: 0 4px; border-top-left-radius: 0; border-bottom-left-radius: 0;"
          v-on:click="showTime(groups.laterTime)"
          :disabled="groups.laterCount == 0"
        )
          TriangleIcon(
            direction="right"
          )

      div
      div

      .label
        | Order:
        HelpButton
          p Show runs in descending or ascending time order.
      div
        button.toggle.left(
          :disabled="query_.asc"
          v-on:click="query_.asc = true"
        ) &nbsp; Time &#8681;
        button.toggle.right(
          :disabled="!query_.asc"
          v-on:click="query_.asc = false"
        ) &nbsp; Time &#8679;

      .label
        | Showing time:
      .label
        | {{ formatTime(groups.earlierTime) }}
        | &mdash;
        | {{ formatTime(groups.laterTime) }}


  table.runlist
    colgroup
      col(v-if="showJob" style="min-width: 10rem")
      template(v-if="argColumnStyle === 'separate'")
        col(v-for="param in params")
      col(v-if="argColumnStyle === 'combined'" style="min-width: 10rem; max-width: 100%;")
      col(style="width: 4rem")
      col(style="width: 4rem")
      col(v-if="query_.grouping" style="width: 5rem")
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
        th.col-group(v-if="query_.grouping") Hidden
        th.col-schedule-time Schedule
        th.col-start-time Start
        th.col-elapsed Elapsed
        th.col-operations Operations

    tbody
      tr(v-if="groups.groups.length == 0")
        td.note(colspan="9") No runs.

      tr(v-if="(query_.asc ? groups.earlierCount : groups.laterCount) > 0")
        td.note(colspan="9")
          | {{ query_.asc ? groups.earlierCount : groups.laterCount }}
          | {{ query_.asc ? 'earlier' : 'later' }} rows not shown
          button(
            v-on:click="showTime(query._asc ? groups.earlierTime : groups.laterTime)"
          ) {{ query_.asc ? 'Earlier' : 'Later' }}

      template(v-for="run, i in groups.groups")
        tr(v-if="i === groups.nowIndex")
          td(colspan="9")
            .timeSeparator
              div.border
              div.now now
              div.border

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
          td.col-group(v-if="query_.grouping")
            | {{ historyCount(run, groups.counts[run.run_id]) }}
          td.col-schedule-time
            Timestamp(:time="run.times.schedule")
          td.col-start-time
            Timestamp(v-if="run.times.running" :time="run.times.running")
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

      tr(v-if="(query_.asc ? groups.laterCount : groups.earlierCount) > 0")
        td.note(colspan="9")
          | {{ query_.asc ? groups.laterCount : groups.earlierCount }}
          | {{ query_.asc ? 'later' : 'earlier' }} rows not shown
          button(
            v-on:click="showTime(query_.asc ? groups.laterTime : groups.earlierTime)"
          ) {{ query_.asc ? 'Later' : 'Earler' }}

</template>

<script>
import { entries, filter, flatten, groupBy, includes, keys, map, sortBy, sortedIndexBy, uniq } from 'lodash'

import { formatDuration, formatElapsed, formatTime, parseTime } from '../time'
import DropList from '@/components/DropList'
import HamburgerMenu from '@/components/HamburgerMenu'
import HelpButton from '@/components/HelpButton'
import Job from '@/components/Job'
import JobLabel from '@/components/JobLabel'
import OperationButton from '@/components/OperationButton'
import PathNav from '@/components/PathNav'
import Run from '@/components/Run'
import RunArgs from '@/components/RunArgs'
import RunElapsed from '@/components/RunElapsed'
import State from '@/components/State'
import StatesSelect from '@/components/StatesSelect'
import store from '@/store.js'
import TimeInput from '@/components/TimeInput'
import Timestamp from '@/components/Timestamp'
import TriangleIcon from '@/components/icons/TriangleIcon'
import WordsInput from '@/components/WordsInput'

const COUNTS = [20, 50, 100, 200, 500, 1000]

function includesAny(arr0, arr1) {
  for (const el of arr0)
    if (arr1.includes(el))
      return true
  return false
}

/**
 * Constructs a predicate fn for matching runs with `args`.
 * 
 * `args` is an array of "param=value" or "param" strings.  The former requires
 * the given param have the cooresponding arg value.  The latter requires that
 * it have any arg value at all.  The result is the conjunction of these.
 * 
 * For example, the `args` array ["fruit=mango", "color"] produced a predicate
 * that matches all runs that both have a "fruit" param with arg value "mango",
 * and also have any value at all ofr the "color" param.
 */
function getArgPredicate(args) {
  const argObj = {}
  for (const arg of args) {
    const i = arg.indexOf('=')
    if (i === -1)
      argObj[arg] = null
    else
      argObj[arg.slice(0, i)] = arg.slice(i + 1)
  }

  return run => {
    for (const param in argObj) {
      const value = run.args[param]
      if (value === undefined)
        // Not present.
        return false
      const ref = argObj[param]
      if (ref !== null && value !== ref)
        // Wrong arg value.
        return false
    }
    return true
  }
}

export default { 
  name: 'RunsList',
  props: {
    query: {type: Object, default: null},
    
    // If true, show the job ID column.
    showJob: {type: Boolean, default: true},

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
    HelpButton,
    Job,
    JobLabel,
    OperationButton,
    PathNav,
    Run,
    RunArgs,
    RunElapsed,
    State,
    StatesSelect,
    TimeInput,
    Timestamp,
    TriangleIcon,
    WordsInput,
  },

  data() {
    return { 
      store,
      time: 'now',
      inputTime: '',
      // If true, show profiling on console.log.
      profile: false,
      query_: {...this.query},

      COUNTS,
    } 
  },

  computed: {
    /** Runs, after filtering.  */
    runs() {
      let runs = Array.from(this.store.state.runs.values())

      // Apply query filters in the order that seems most likely to put
      // the cheapest and most selective filters first.
      if (this.query_.path) {
        const path = this.query_.path
        const prefix = path + '/'
        runs = filter(runs, run => run.job_id === path || run.job_id.startsWith(prefix))
      }
      if (this.query_.states)
        runs = filter(runs, run => includes(this.query_.states, run.state))
      if (this.query_.labels)
        runs = filter(runs, run => includesAny(this.query_.labels, run.labels))
      if (this.query_.args) 
        runs = filter(runs, getArgPredicate(this.query_.args))
      if (this.query_.keywords) {
        const re = new RegExp(this.query_.keywords.join('|'))
        runs = filter(runs, run => run.job_id.search(re) !== -1)
      }

      return sortBy(runs, r => r.time_key)
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
      if (this.query_.grouping) {
        const runs = this.runs
        if (this.profile) {
          t1 = new Date()
          console.log('groups-runs', (t1 - t0) * 0.001)
          t0 = t1
        }

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

        if (this.profile) {
          t1 = new Date()
          console.log('groups-groupBy', (t1 - t0) * 0.001)
          t0 = t1
        }
      }

      else {
        groups = this.runs
        groups.forEach(r => { counts[r.run_id] = 1 })
      }

      // Sort groups by time.
      groups = sortBy(groups, r => r.time_key)

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
    
      // Determine the time to center around.
      const time = this.query_.time === 'now' ? now : this.query_.time
      // Find the index corresponding to the center time.
      let timeIndex = sortedIndexBy(runs, { time_key: time }, r => r.time_key)

      // Time cutoff and count of earlier runs not shown.
      let earlierTime = null
      let earlierCount = 0
      // Time cutoff and count of later runs not shown.
      let laterTime = null
      let laterCount = 0
      const show = this.query_.show
      if (this.timeControls && show < runs.length) {
        // There are more runs than fit in the view.  Decide how many runs to
        // show before and after the center time.
        var r0 = timeIndex
        var r1 = runs.length - timeIndex
        if (r0 < show / 2)
          r1 = show - r0
        else if (r1 < show / 2)
          r0 = show - r1
        else
          r0 = r1 = show / 2

        if (r0 < timeIndex) {
          // Don't show some runs and omit others with identical timestamp.
          while (
            0 < timeIndex && timeIndex < runs.length
            && runs[timeIndex - 1].time_key === runs[timeIndex].time_key
          )
            timeIndex--
          // Number of earlier runs omitted.
          earlierCount = timeIndex - r0
          // Time cutoff of earlier runs omitted.
          earlierTime = runs[earlierCount].time_key
          // Omit the runs.
          runs = runs.slice(earlierCount)
          // Adjust the center time index accordingly.
          timeIndex -= earlierCount
        }

        if (r1 < runs.length - timeIndex) {
          // Don't show some runs and omit others with identical timestamp.
          while (
            0 < timeIndex && timeIndex < runs.length - 1
            && runs[timeIndex - 1].time_key === runs[timeIndex].time_key
          )
            timeIndex++
          // Number of later runs omitted.
          laterCount = runs.length - (timeIndex + r1)
          // Time cutoff of later runs omitted.
          laterTime = runs[runs.length - laterCount].time_key
          // Omit the runs.
          runs = runs.slice(0, runs.length - laterCount)
        }
      }

      let nowIndex
      if (runs.length > 0 && runs[0].time_key < now && now < runs[runs.length - 1].time_key)
        nowIndex = sortedIndexBy(runs, { time_key: now }, r => r.time_key)

      if (!this.query_.asc)
        runs.reverse()

      if (this.profile)
        console.log(
          'runs:', this.store.state.runs.size, 'filtered:', this.runs.length, 'groups:', runs.length, 
          'earlier:', earlierCount, earlierTime,
          'later:', laterCount, laterTime,
          'in:', (new Date() - start) * 0.001
        )

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
  
  watch: {
    // Whenever any parts of our query change, inform the parent.
    query_: {
      deep: true,
      handler: function (query) {
        this.$emit('query', query)
      }
    },
  },

  methods: {
    formatElapsed,

    historyCount(run, count) {
      return (
        count === 1 ? '' 
        : '+' + (count - 1) + ' ' + (
          run.group_key.startsWith('S') ? 'scheduled'
          : 'completed'
        )
      )
    },

    formatTime(time) {
      return time ? formatTime(time, this.store.state.timeZone) : '\u00a0'
    },

    /**
     * Show runs around `time`.
     */
    showTime(time) {
      this.query_.time = time
      this.inputTime = ''
    },

    startTime(run) {
      if (run.times.schedule) {
        const now = this.store.state.time
        const schedule = new Date(run.times.schedule)
        return formatDuration(Math.round((schedule - now) * 1e-3))
      }
      else
        return ''
    },

    /**
     * Handle explicit user time input by showing runs around the specified time.
     */
    onTimeChange() {
      // Parse the input time, in the current time zone.
      const tz = store.state.timeZone
      const time = parseTime(this.inputTime, false, tz).tz('UTC')
      // Show runs around this time.
      this.query_.time = time.format()
      // Replace the input field with the full canonicalized time.
      this.inputTime = formatTime(time, tz)
    },

    onShowInput(ev) {
      this.$set(this.query_, 'show', COUNTS[ev])
    },

  },

}
</script>

<style lang="scss" scoped>
@import '@/styles/index.scss';

.controls {
  display: grid;
  max-width: 80rem;
  grid-template-columns: repeat(3, 0fr 1fr);

  gap: 4px 12px;
  justify-items: left;
  align-items: baseline;
  white-space: nowrap;
  line-height: 28px;
  margin-bottom: 21px;
  
  > * {
    height: 30px;
  }

  > input {
    width: 100%;
  }

  .label {
    text-align: right;
    white-space: nowrap;
  }

  .field {
    display: inline-block;
    border: 1px solid $apsis-frame-color;
    text-align: center;
    padding: 0 12px;
    &.disabled {
      border: none;
    }
  }

  .toggle {
    padding: 0 12px;
    &:disabled {
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
    text-align: center;
    height: 100%;
  }

  input[type="checkbox"] {
    width: 16px;
    height: 16px;
  }

  .counts {
    width: 100%;
    height: 32px;
    text-align: right;
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

  .col-state {
    vertical-align: bottom;
  }

  .col-schedule-time, .col-start-time {
    font-size: 90%;
    color: #888;
    text-align: right;
  }

  .col-group {
    text-align: right;
    white-space: nowrap;
    color: #888;
    font-size: 90%;

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
    width: 100%;
    display: flex;

    .border {
      flex-basis: 50%;
      border-bottom: 2px dotted $global-frame-color;
      margin-bottom: 0.5em;
      line-height: 50%;
    }

    .now {
      margin: 0 8px;
      color: $global-frame-color;
    }
  }
}
</style>
