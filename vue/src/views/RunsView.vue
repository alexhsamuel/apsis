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

/** Strips off all occurrences of `suffix` at the end of `string`.  */
function rstrip(string, suffix) {
  const len = suffix.length
  while (len <= string.length && string.slice(-len) === suffix)
    string = string.slice(0, -len)
  return string
}

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
    /** Updates the route URL query from the runs query.  */
    updateUrl() {
      const joinWords = (words) => words ? words.join(',') : null

      const oldQuery = this.$route.query
      var query = {...oldQuery}
      var changed = false
      // Set a param, and marks changes.  If val is undefined, sets the param
      // without value.  If val is null, removes the param.  Note that in
      // the URL query object, a _null_ value indicates set without value.
      function set(param, val) {
        if (val)
          val = val.trim()

        if (val === null && oldQuery[param] !== undefined) {
          // Remove.
          delete query[param]
          changed = true
        }
        else if (val === undefined && oldQuery[param] !== null) {
          // Set without value.
          query[param] = null
          changed = true
        }
        else if (oldQuery[param] !== val) {
          // Add.
          query[param] = val === undefined ? null : val
          changed = true
        }
      } 

      set('path', this.query.path || null)
      set('keywords', joinWords(this.query.keywords))
      set('labels', joinWords(this.query.labels))
      set('states', joinWords(this.query.states))
      set('args', joinWords(this.query.args))
      set('grouping', this.query.grouping ? undefined : null)
 
      if (changed) {
        console.log('push', query)
        this.$router.push({ query })
      }
    },

    urlToQuery(url) {
      const splitWords = (param) => param ? param.split(',') : null
      return {
        path: url.path ? rstrip(url.path, '/') : null,
        keywords: splitWords(url.keywords),
        labels: splitWords(url.labels),
        states: splitWords(url.states),
        args: splitWords(url.args),
        grouping: url.grouping === null,
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
