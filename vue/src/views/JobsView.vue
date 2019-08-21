<template lang="pug">
div
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

  watch: {
    query(query) {
      // If the query changed, add it to the URL query.
      const q = query || undefined
      if (this.$route.query.q !== q)
        this.$router.push({ query: { q, d: this.dir } })
    },

    dir(dir) {
      // If the dir changed, add it to the URL query.
      const d = dir || undefined
      if (this.$route.query.d !== d)
        this.$router.push({ dir: { q: this.query, d } })
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
