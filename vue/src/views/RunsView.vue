<template lang="pug">
div
  .flex-margin
    h3(style="flex: 1;")
      a.undersel(@click="onShowJobs") Jobs
      a.undersel.sel(@click="") Runs

  //- The table of runs.
  RunsList(
    :query="urlToQuery($route.query)"
    :timeControls="true"
  )

</template>

<script>
import RunsList from '@/components/RunsList'
import * as runsFilter from '@/runsFilter.js'
import SearchInput from '@/components/SearchInput'
import StatesSelect from '@/components/StatesSelect'

export default {
  name: 'RunsView',
  components: {
    RunsList,
    SearchInput,
    StatesSelect,
  },

  computed: {
    states() {
      // Extract states from the query.
      return runsFilter.StateTerm.get(this.query)
    },
  },

  watch: {
    // query(query) {
    //   // If the query changed, add it to the URL.
    //   this.setQueryParam('q', query || undefined)
    // },

    // '$route'(to, from) {
    //   // Set the query from the URL query.
    //   this.query = to.query.q || ''
    // },
  },

  methods: {
    // FIXME: Elsewhere.
    /**
     * Sets a query param in the route.
     * @param param - the query param name
     * @param val - the value to set, or null / undefined to remove
     */
    setQueryParam(param, val) {
      if (val)
        val = val.trim()
      if (this.$route.query[param] !== val) {
        // Set only this param, keeping the reqest of the query.
        const query = Object.assign({}, this.$route.query)
        if (val === null || val === undefined)
          delete query[param]
        else
          query[param] = val
        this.$router.push({ query })
      }
    },

    urlToQuery(query) {
      const splitWords = (words) => words ? words.split(',') : null
      return {
        path: query.path,
        keywords: splitWords(query.keywords),
        labels: splitWords(query.labels),
      }
    },

    onSetStates(states) {
      console.log('onSetStates', states)
      this.setQueryParam('states', states === null ? null : states.join(','))
    },

    onShowJobs() {
      this.$router.push({
        name: 'jobs-list',
        params: {
          path: this.path || undefined,
        },
        query: {
          // FIXME
          // q: runsFilter.toJobsQuery(this.query) || undefined,
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
