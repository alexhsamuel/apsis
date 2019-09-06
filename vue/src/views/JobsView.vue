<template lang="pug">
div
  div(style="display: flex")
    div(style="flex: 1;")
      h3(style="padding-left: 12px;")
        a.undersel.sel() Jobs
        a.undersel(v-on:click="onShowRuns") Runs
        span(v-if="pathStr" style="font-size: 16px; padding: 0 4px;")  
          PathNav(:path="pathStr" v-on:path="setPath($event)")

    div(style="flex: 0 0 300px;")
      SearchInput(v-model="query").search.uk-margin-bottom

  JobsList(
    :dir="pathStr"
    :query="query"
    v-on:dir="setPath($event)"
    ).uk-margin-bottom

</template>

<script>
import JobsList from '@/components/JobsList'
import PathNav from '@/components/PathNav'
import SearchInput from '@/components/SearchInput'

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
          q: 'since:1d',
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

<style lang="scss">
// For "buttons" with underline selection.
.undersel {
  padding: 0 8px 4px 8px;
  color: inherit;
  &:hover {
    text-decoration: none;
    border-bottom: 3px solid #eee;
  }
  &.sel {
    border-bottom: 3px solid black;
  }
}
</style>

<style lang="scss" scoped>
.search {
  width: 400px;
}
</style>
