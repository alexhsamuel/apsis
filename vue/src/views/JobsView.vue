<template lang="pug">
div
  div(style="display: flex")
    div(style="flex: 1 0 auto")
      h3
        a.dirnav(v-on:click="setPath(null)" style="padding-left: 12px;") Jobs
        span(style="font-size: 16px; padding: 0 4px;")  in 
        span(v-for="[subdir, name] in dirPrefixes")
          a.dirnav(v-on:click="setPath(subdir)") {{ name }}
          |  / 

    div(style="flex: 0 auto; padding: 0 8px")
      button.uk-button(
        type="button"
        v-on:click="onShowRuns"
        ) Show Runs

    div(style="flex: 0 auto")
      SearchInput(v-model="query").search.uk-margin-bottom

  JobsList(
    :dir="toPathStr(path)"
    :query="query"
    v-on:dir="setPath($event)"
    ).uk-margin-bottom

</template>

<script>
import JobsList from '@/components/JobsList'
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
    SearchInput,
  },

  data() {
    return {
      query: this.$route.query.q || '',
    }
  },

  computed: {
    dirPrefixes() {
      return Array.from(
        function*(parts) {
          for (var i = 0; i < parts.length; ++i)
            yield [parts.slice(0, i + 1).join('/'), parts[i]]
        }(toPathParts(this.path))
      )
    },
  },

  methods: {
    toPathStr,

    onShowRuns() {
      this.$router.push({
        name: 'runs-list',
        query: { path: toPathStr(this.path) || undefined },
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
.search {
  width: 400px;
}
</style>
