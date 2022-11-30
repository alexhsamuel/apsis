<template lang="pug">
div
  .flex-margin
    h3(style="flex: 1;")
      a.undersel(v-on:click="onShowJobs") Jobs
      a.undersel(v-on:click="onShowRuns") Runs
      a.undersel.sel(v-on:click="") Runs2
      span(v-if="path" style="font-size: 16px; padding: 0 8px;")  
        PathNav(:path="path" v-on:path="setPath($event)")

    //- Combo box for selecting the run states filter.
    StatesSelect(
      style="flex: 0 0 180px;"
      :value="states"
      v-on:input="setStates($event)"
    )

    //- Input box for the search string.
    SearchInput.search-input(
      v-model="query"
      style="flex: 0 0 300px;"
    )

  //- The table of runs.
  RunsList(
    :query="query"
    :path="path"
    v-on:path="setPath($event)"
    :timeControls="true"
    :showNumRuns="showNumRuns"
    v-on:showNumRuns="showNumRuns = $event"
    :timeAsc="timeAsc"
    v-on:timeAsc="timeAsc = $event"
    :groupRuns="groupRuns"
    v-on:groupRuns="groupRuns = $event"
  )

</template>

<script>
import * as jobsFilter from '@/jobsFilter.js'
import PathNav from '@/components/PathNav'
import RunsList from '@/components/RunsList'
import * as runsFilter from '@/runsFilter.js'
import SearchInput from '@/components/SearchInput'
import StatesSelect from '@/components/StatesSelect'

const SHOWNUMRUNS_DEFAULT = 50

export default {
  name: 'RunsView',
  components: {
    PathNav,
    RunsList,
    SearchInput,
    StatesSelect,
  },

  data() {
    return {
      query: this.$route.query.q || '',
      showNumRuns: parseInt(this.$route.query['num'] || SHOWNUMRUNS_DEFAULT),
      timeAsc: !('desc' in this.$route.query),
      groupRuns: !('nogroup' in this.$route.query),
    }
  },

  computed: {
    path() {
      return this.$route.query.path
    },

    states() {
      // Extract states from the query.
      return runsFilter.StateTerm.get(this.query)
    },
  },

  watch: {
    query(query) {
      // If the query changed, add it to the URL.
      this.setQueryParam('q', query || undefined)
    },

    showNumRuns(showNumRuns) {
      this.setQueryParam('num', showNumRuns === SHOWNUMRUNS_DEFAULT ? undefined : showNumRuns)
    },

    timeAsc(timeAsc) {
      this.setQueryParam('desc', timeAsc ? undefined : null)
    },

    groupRuns(groupRuns) {
      this.setQueryParam('nogroup', groupRuns ? undefined : null)
    },

    '$route'(to, from) {
      // Set the query from the URL query.
      this.query = to.query.q || ''
    },
  },

  methods: {
    // FIXME: Elsewhere.
    /**
     * Sets a query param in the route.
     * @param param - the query param name
     * @param val - the value to set, null for no value, or undefined to remove
     */
    setQueryParam(param, val) {
      if (val !== undefined && val !== null)
        val = val.toString().trim()

      if (this.$route.query[param] !== val) {
        const query = Object.assign({}, this.$route.query)
        if (val === undefined)
          delete query[param]
        else
          query[param] = val
        this.$router.push({ query })
      }
    },

    setStates(states) {
      this.query = runsFilter.StateTerm.set(this.query, states)
    },

    setPath(path) {
      this.setQueryParam('path', path)
    },

    onShowJobs() {
      this.$router.push({
        name: 'jobs-list',
        params: {
          path: this.path || undefined,
        },
        query: {
          q: runsFilter.toJobsQuery(this.query) || undefined,
        },
      })
    },

    onShowRuns() {
      this.$router.push({
        name: 'runs-list',
        query: {
          path: this.path || undefined,
          q: 'since:1d ' + jobsFilter.toRunsQuery(this.query),
        },
      })
    },
  },
}
</script>

<style lang="scss">
h3 {
  margin: 0;
  margin-bottom: 1ex;
}

// FIXME: Elsewhere
.flex-margin {
  display: flex;
  gap: 16px;
}
</style>

<style lang="scss" scoped>
.search-input {
  width: 50%;
}
</style>
