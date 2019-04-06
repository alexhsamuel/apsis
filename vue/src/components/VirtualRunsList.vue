<template lang="pug">
div.runlist
  .row.head
    div
      | {{ runs.length }} Runs

  .row.head
    .col-schedule-time Schedule
    .col-start-time Start
    .col-state State
    .col-job Job
    .col-args Args
    .col-run Run
    .col-elapsed Elapsed
    .col-actions Actions

  //- tr
  //-   td(colspan=2 style="padding-left: 14px;")
  //-     | {{ runs.length }} Runs
  //-   td(colspan=2)
  //-     Pagination.pagination(v-if="pageSize" style="display: inline-block" :page.sync="page" :num-pages="numPages")
  //-   td(colspan=5)

  RecycleScroller.scroller(
    :items="runs" 
    :item-size="28"
    :buffer="1000"
    key-field="run_id"
  )
    template(v-slot="{ item }")
      .row.run-group-next
        .col-schedule-time
          Timestamp(:time="item.times.schedule")
        .col-start-time
          Timestamp(:time="item.times.running")
        .col-state
          State(:state="item.state")
        .col-job
          Job(:job-id="item.job_id")
        .col-args
          span {{ arg_str(item.args) }}
        .col-run
          Run(:run-id="item.run_id")
        .col-elapsed
          RunElapsed(:run="item")
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
import { filter, join, map, sortBy, toPairs } from 'lodash'
import { RecycleScroller } from 'vue-virtual-scroller'

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

import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'

// FIXME: Deduplicate.
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
    RecycleScroller,
    Run,
    RunElapsed,
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
      return sortBy(filter(this.store.state.runs, this.jobPredicate), sortTime)
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
  border: 1px solid #e1e8e4;

  .scroller {
    height: calc(100vh - 280px);
  }

  .row {
    height: 28px;
    display: flex;
    padding-bottom: 0px;

    > :first-child {
      padding-left: 12px;
    }
    > :last-child {
      padding-right: 12px;
    }

    &.head {
      background-color: #f6faf8;
      > div {
        box-sizing: border-box;
        font-weight: normal;
        text-align: left;
        padding: 12px;
        &:last-child {
          padding-right: 12px;
        }
      }
      height: 48px;
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
      flex: 1 1 12rem;
      text-align: left;
      overflow: hidden;  // FIXME
    }

    .col-run {
      flex: 0 0 6rem;
      text-align: right;
      font-size: 90%;
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

  .row:hover {
    background-color: #fafafa;
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

