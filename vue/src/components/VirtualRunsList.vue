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
      tr.run_group-next(v-for="(run, index) in runs" :key="run.run_id")
        td.col-schedule-time
          Timestamp(:time="run.times.schedule")
        td.col-start-time
          Timestamp(:time="run.times.running")
        td.col-reruns
        td.col-state
          State(:state="run.state")
        td.col-job
          Job(:job-id="run.job_id")
        td.col-args
          span {{ arg_str(run.args) }}
        td.col-run
          Run(:run-id="run.run_id")
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
import { filter, join, map, toPairs } from 'lodash'

import ActionButton from './ActionButton'
import { formatElapsed } from '../time'
import Job from './Job'
import Pagination from './Pagination'
import Run from './Run'
import * as runsFilter from '@/runsFilter.js'
import State from './State'
import StatesSelect from '@/components/StatesSelect'
import store from '@/store.js'
import Timestamp from './Timestamp'

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
    State,
    StatesSelect,
    Timestamp,
  },

  data() { 
    return { 
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
      return filter(this.store.state.runs, this.jobPredicate).slice(0, 100)
    },

  },

  methods: {
    // FIXME: Duplicated.
    arg_str(args) {
      return join(map(toPairs(args), ([k, v]) => k + '=' + v), ' ')
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
