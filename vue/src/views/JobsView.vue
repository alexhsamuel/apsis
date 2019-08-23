<template lang="pug">
div
  div(style="display: flex")
    div(style="flex: 1 0 auto")
      h3
        a.dirnav(v-on:click="dir = null") Jobs
        span(v-for="[subdir, name] in dirPrefixes")
          span(uk-icon="icon: chevron-right" ratio="1.5") 
          a.dirnav(v-on:click="dir = subdir") {{ name }}

    div(style="flex: 0 auto; padding: 0 8px")
      button.uk-button(
        type="button"
        v-on:click="navShowRuns"
        ) Show Runs

    div(style="flex: 0 auto")
      SearchInput(v-model="query").search.uk-margin-bottom

  JobsList(
    :dir="dir"
    :query="query"
    v-on:dir="dir = $event"
    ).uk-margin-bottom

</template>

<script>
import JobsList from '@/components/JobsList'
import SearchInput from '@/components/SearchInput'

export default {
  name: 'JobsView',
  components: {
    JobsList,
    SearchInput,
  },

  data() {
    return {
      dir: this.$route.query.d,
      query: this.$route.query.q || '',
    }
  },

  computed: {
    dirPrefixes() {
      return this.dir ? Array.from(
        function*(parts) {
          for (var i = 0; i < parts.length; ++i)
            yield [parts.slice(0, i + 1).join('/'), parts[i]]
        }(this.dir.split('/'))
      ) : []
    },

  },

  methods: {
    navShowRuns() {
      this.$router.push({
        name: 'runs-list',
        query: { q: '/' + this.dir }
      })
    },
  },

  watch: {
    query(query) {
      // If the query changed, add it to the URL query.
      const q = query || undefined
      if (this.$route.query.q !== q)
        this.$router.push({ query: { q, d: this.dir } })
    },

    dir(dir) {
      console.log('dir changed', dir)
      // If the dir changed, add it to the URL query.
      const d = dir || undefined
      if (this.$route.query.d !== d)
        this.$router.push({ query: { q: this.query, d } })
    },

    '$route'(to, from) {
      // Set the dir and query from the URL query.
      this.dir = to.query.d
      this.query = to.query.q || ''
    },

  },
}
</script>

<style lang="scss" scoped>
.search {
  width: 400px;
}
</style>
