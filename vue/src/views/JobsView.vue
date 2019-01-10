<template lang="pug">
div
  SearchInput(v-model="query").search.uk-margin-bottom
  JobsList(:query="query").uk-margin-bottom
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
      query: this.$route.query.q || '',
    }
  },

  watch: {
    query(query) {
      // If the query changed, add it to the URL query.
      const q = query || undefined
      if (this.$route.query.q !== q)
        this.$router.push({ query: { q } })
    },

    '$route'(to, from) {
      // Set the query from the URL query.
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
