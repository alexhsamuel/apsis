<template lang="pug">
div
  div.controls(style="display: flex")
    div(style="flex: 1;")
      h3
        a.undersel.sel() Jobs
        a.undersel(v-on:click="onShowRuns") Runs
        a.undersel(v-on:click="onShowRuns2") Runs2
        span(v-if="pathStr" style="font-size: 16px; padding: 0 8px;")  
          PathNav(:path="pathStr" v-on:path="setPath($event)")

    SearchInput.search(
      v-model="query"
      style="flex: 0 0 300px;"
    )

  JobsList(
    :dir="pathStr"
    :query="query"
    v-on:dir="setPath($event)"
  )

</template>

<script>
import JobsList from '@/components/JobsList'
import PathNav from '@/components/PathNav'
import SearchInput from '@/components/SearchInput'
import * as jobsFilter from '@/jobsFilter.js'

function toPathStr(path) {
  return (
    !path ? ''
    : Array.isArray(path) ? path.join('/')
    : path
  )
}

function toPathParts(path) {
  return (
    !path ? []
    : Array.isArray(path) ? path
    : path.split('/')
  )
}

export default {
  name: 'JobsView',
  props: [
    // Accept both str and array paths.  vue-router always returns a path
    // string, but if we $router.push a string params, it URL-encodes
    // path seps.  So, we $router.push an array of path parts instead.
    // But then we have to accept both str and array paths.
    'path',
  ],
  components: {
    JobsList,
    PathNav,
    SearchInput,
  },

  data() {
    return {
      query: this.$route.query.q || '',
    }
  },

  computed: {
    pathStr() {
      return toPathStr(this.path)
    },
  },

  methods: {
    onShowRuns() {
      this.$router.push({
        name: 'runs-list',
        query: {
          path: this.pathStr || undefined,
          q: 'since:1d ' + jobsFilter.toRunsQuery(this.query),
        },
      })
    },

    onShowRuns2() {
      this.$router.push({
        name: 'runs-list2',
        query: {
          path: this.pathStr || undefined,
        },
      })
    },

    setPath(path) {
      if (toPathStr(this.$route.params.path) !== path)
        // Push path as an array of path components rather than as a str,
        // since Vue will URL-encode path seps otherwise.  See above.
        this.$router.push({ name: 'jobs-list', params: { path: toPathParts(path) } })
    },
  },

  watch: {
    query(query) {
      // If the query changed, add it to the URL query.
      const q = query || undefined
      if (this.$route.query.q !== q)
        this.$router.push({ query: { q } })
    },
  },
}
</script>

<style lang="scss" scoped>
.controls {
  margin-bottom: 1rem;
}

.search {
  width: 400px;
}
</style>
