<template lang="pug">
div
  .flex-margin
    h3(style="padding-left: 12px; flex: 1;")
      a.undersel(v-on:click="onShowJobs") Jobs
      a.undersel.sel(v-on:click="") Runs
      span(v-if="path" style="font-size: 16px; padding: 0 8px;")  
        PathNav(:path="path" v-on:path="setPath($event)")

    //- Combo box for selecting the "since" start date of runs to show.
    SinceSelect(
      style="flex: 0 0 150px;"
      :value="since"
      v-on:input="setSince($event)"
    )

    //- Combo box for selecting the run states filter.
    StatesSelect(
      style="flex: 0 0 150px;"
      :value="states"
      v-on:input="setStates($event)"
    )

    //- Input box for the search string.
    SearchInput.search-input.uk-margin-bottom(
      v-model="query"
      style="flex: 0 0 300px;"
    )

  //- The table of runs.
  RunsList.uk-margin-bottom(
    :query="query"
    :path="path"
    v-on:path="setPath($event)"
)

</template>

<script>
import PathNav from '@/components/PathNav'
import RunsList from '@/components/RunsList'
// import RunsList from '@/components/VirtualRunsList'
import * as runsFilter from '@/runsFilter.js'
import SearchInput from '@/components/SearchInput'
import SinceSelect from '@/components/SinceSelect'
import StatesSelect from '@/components/StatesSelect'

export default {
  name: 'RunsView',
  components: {
    PathNav,
    RunsList,
    SearchInput,
    SinceSelect,
    StatesSelect,
  },

  data() {
    return {
      query: this.$route.query.q || '',
    }
  },

  computed: {
    path() {
      return this.$route.query.path
    },

    since() {
      // Extract since from the query.
      return runsFilter.SinceTerm.get(this.query)
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
     * @param val - the value to set, or undefined to remove
     */
    setQueryParam(param, val) {
      val = val.trim()
      if (this.$route.query[param] !== val) {
        // Set only this param, keeping the reqest of the query.
        const query = Object.assign({}, this.$route.query, { [param]: val })
        this.$router.push({ query })
      }
    },

    setSince(since) {
      this.query = runsFilter.SinceTerm.set(this.query, since)
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
  },
}
</script>

<style lang="scss">
// FIXME: Elsewhere
.flex-margin {
  display: flex;
  > * {
    margin-right: 16px;
  }
  > :last-child {
    margin-right: 0;
  }
}
</style>

<style lang="scss" scoped>
.search-input {
  width: 50%;
}
</style>
