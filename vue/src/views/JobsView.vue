<template lang="pug">
div
  SearchInput(v-model="search").search.uk-margin-bottom
  JobsList(:search="search").uk-margin-bottom
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
      search: this.$route.query.s || '',
    }
  },

  watch: {
    search(search) {
      // If the serch term changed, add it to the URL query.
      const s = search || undefined
      if (this.$route.query.s !== s)
        this.$router.push({ query: { s } })
    },

    '$route'(to, from) {
      // Set the search term from the URL query.
      this.search = to.query.s || ''
    },

  },
}
</script>

<style lang="scss" scoped>
.search {
  width: 400px;
}
</style>
