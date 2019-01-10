<template lang="pug">
div
  SearchInput(v-model="query").search-input.uk-margin-bottom
  RunsList.uk-margin-bottom(
    :start-time="startTime"
    :end-time="endTime"
    :p="+this.$route.query.p - 1 || 0"
    v-on:p="setPage($event)"
    :query="query"
    v-on:query="query = $event"
  )

</template>

<script>
import RunsList from '@/components/RunsList'
import SearchInput from '@/components/SearchInput'
import State from '@/components/State'
import store from '@/store'
import { parseTime } from '@/time'

export default {
  name: 'RunsView',
  components: {
    RunsList,
    SearchInput,
    State,
  },

  data() {
    return {
      query: this.$route.query.q || '',
    }
  },

  computed: {
    startTime() { return parseTime('yesterday', false, store.state.timeZone) },
    endTime() { return parseTime('', true, store.state.timeZone) },
    sinceError() { return this.sinceInput !== '' && this.startTime === null },
    untilError() { return this.untilInput !== '' && this.endTime === null },
  },

  watch: {
    query(query) {
      // If the query changed, add it to the URL.
      const q = query || undefined
      if (this.$route.query.q !== q)
        this.$router.push({ query: { q } })
    },

    '$route'(to, from) {
      // Set the query from the URL query.
      this.query = to.query.q || ''
    },
  },

  methods: {
    setPage(p) {
      // If the page has changed, add it to the URL.
      if (this.$route.query.p !== p - 1)
        this.$router.push({ query: { p: p === 0 ? undefined : p + 1 } })
    },
  },
}
</script>

<style lang="scss" scoped>
.search-input {
  width: 50%;
}
</style>
