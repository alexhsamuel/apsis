<template lang="pug">
div
  RecycleScroller.scroller(
    :items="runs" 
    :item-size="32"
    key-field="run_id"
  ).runlist
    //- template#before

    //-   tr
    //-     td(colspan=2 style="padding-left: 14px;")
    //-       | {{ runs.length }} Runs
    //-     td(colspan=2)
    //-       Pagination.pagination(v-if="pageSize" style="display: inline-block" :page.sync="page" :num-pages="numPages")
    //-     td(colspan=5)

    template(v-slot="{ item }")
      .row.run-group-next
        .col-schedule-time(style="height: 32px")
          Timestamp(:time="item.times.schedule")
        .col-start-time
          Timestamp(:time="item.times.running")
        .col-reruns
        .col-state
          State(:state="item.state")
        .col-job
          Job(:job-id="item.job_id")
        .col-args
          span {{ arg_str(item.args) }}
        .col-run
          Run(:run-id="item.run_id")
        .col-elapsed
          | {{ item.meta.elapsed === undefined ? "" : formatElapsed(item.meta.elapsed) }}
        .col-actions
          div.uk-inline(v-if="Object.keys(item.actions).length > 0")
            button.uk-button.uk-button-default.uk-button-small.actions-button(type="button")
              span(uk-icon="icon: menu; ratio: 0.75")
            div(uk-dropdown="pos: left-center")
              ul.uk-nav.uk-dropdown-nav
                li: ActionButton(
                  v-for="(url, action) in item.actions" 
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

import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'

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
      return filter(this.store.state.runs, this.jobPredicate) // .slice(0, 100)
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
.runlist {
  width: 100%;
  height: 800px;
  border: 1px solid red;

  .row {
    height: 12px;

    display: flex;
    border: 1px sold green;

    //-     th.col-schedule-time Schedule
    //-     th.col-start-time Start
    //-     th.col-reruns Runs
    //-     th.col-state State
    //-     th.col-job Job
    //-     th.col-args Args
    //-     th.col-run Run
    //-     th.col-elapsed Elapsed
    //-     th.col-actions Actions

    &:first-child {
      padding-left: 12px;
    }
    &:last-child {
      padding-right: 12px;
    }

    .col-schedule-time, .col-start-time {
      flex: 0 0 10rem;
      text-align: left;
    }
    
    .col-reruns {
      flex: 0 0 4rem;
      text-align: right;
      font-size: 90%;
    }

    .col-state {
      flex: 0 0 4rem;
      text-align: center;
    }

    .col-job {
      flex: 0 0 12rem;
      text-align: left;
    }

    .col-args {
      flex: 1 0 12rem;
      text-align: left;
    }

    .col-run {
      flex: 0 0 4rem;
      text-align: center;
    }

    .col-elapsed {
      flex: 0 0 6rem;
      padding-right: 1em;
      text-align: right;
      white-space: nowrap;
    }

    .col-actions {
      flex: 0 0 4rem;
      text-align: center;
      button {
        font-size: 80%;
        line-height: 1.4;
      }
    }
  }
}

table.runlist {
  width: 100%;

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

}
</style>

<style lang="scss" scoped>
// FIXME
.uk-dropdown {
  padding: 12px;
  min-width: 0;
}
</style>

