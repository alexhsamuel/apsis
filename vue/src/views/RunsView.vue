<template lang="pug">
div
  .flex-margin
    h3(style="flex: 1;")
      a.undersel(@click="onShowJobs") Jobs
      a.undersel.sel(@click="") Runs

  //- The table of runs.
  RunsList(
    :query="query"
    @query="updateUrl"
    :timeControls="true"
  )

</template>

<script>
import RunsList from '@/components/RunsList'

export default {
  name: 'RunsView',
  components: {
    RunsList,
  },

  data() {
    return {
      query: this.urlToQuery(this.$route.query),
    }
  },

  watch: {
    // When the route changes due to the browser's forward/back buttons,
    // trigger an update to the query.
    '$route'(to, from) {
      this.$set(this, 'query', this.urlToQuery(to.query))
    }
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

    /** Updates the route URL query from the runs query.  */
    updateUrl() {
      const joinWords = (words) => words ? words.join(',') : null
      this.setQueryParam('path', this.query.path || null)
      this.setQueryParam('keywords', joinWords(this.query.keywords))
      this.setQueryParam('labels', joinWords(this.query.labels))
      this.setQueryParam('states', joinWords(this.query.states))
    },

    urlToQuery(url) {
      const splitWords = (param) => param ? param.split(',') : null
      return {
        path: url.path || null,
        keywords: splitWords(url.keywords),
        labels: splitWords(url.labels),
        states: splitWords(url.states),
      }
    },

    onShowJobs() {
      this.$router.push({
        name: 'jobs-list',
        params: {
          path: this.path || undefined,
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
