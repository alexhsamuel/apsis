<template lang="pug">
div
  .flex-margin
    SearchInput(v-model="query" style="flex-grow: 1;").search-input.uk-margin-bottom

    SinceSelect(
      style="flex-basis: 240px; flex-grow 0;"
      :value="since"
      v-on:input="setSince($event)"
    )

    StatesSelect(
      style="flex-basis: 240px; flex-grow 0;"
      :value="states"
      v-on:input="setStates($event)"
    )

  RunsList.uk-margin-bottom(
    :start-time="startTime"
    :end-time="endTime"
    :p="+this.$route.query.p - 1 || 0"
    v-on:p="setPage($event)"
    :query="query"
  )

</template>

<script>
import RunsList from '@/components/RunsList'
import * as runsFilter from '@/runsFilter.js'
import SearchInput from '@/components/SearchInput'
import SinceSelect from '@/components/SinceSelect'
import StatesSelect from '@/components/StatesSelect'
import State from '@/components/State'

export default {
  name: 'RunsView',
  components: {
    RunsList,
    SearchInput,
    SinceSelect,
    State,
    StatesSelect,
  },

  data() {
    return {
      query: this.$route.query.q || '',
    }
  },

  computed: {
    // startTime() { return parseTime('yesterday', false, store.state.timeZone) },
    startTime() { return null },
    // endTime() { return parseTime('', true, store.state.timeZone) },
    endTime() { return null },
    sinceError() { return this.sinceInput !== '' && this.startTime === null },
    untilError() { return this.untilInput !== '' && this.endTime === null },

    since() {
      // Extract since from the query.
      return runsFilter.SinceTerm.get(this.query)
    },

    states() {
      // Extract states from the query.
      return runsFilter.StateTerm.get(this.query)
    },
  },

  watch: {
    query(query) {
      // If the query changed, add it to the URL.
      this.setQueryParam('q', query || undefined)
    },

    '$route'(to, from) {
      // Set the query from the URL query.
      this.query = to.query.q || ''
    },
  },

  methods: {
    // FIXME: Elsewhere.
    /**
     * Sets a query param in the route.
     * @param param - the query param name
     * @param val - the value to set, or undefined to remove
     */
    setQueryParam(param, val) {
      if (this.$route.query[param] !== val) {
        // Set only this param, keeping the reqest of the query.
        const query = Object.assign({}, this.$route.query, { [param]: val })
        this.$router.push({ query })
      }
    },

    setPage(p) {
      // If the page has changed, add it to the URL.
      this.setQueryParam('p', p === 0 ? undefined : p + 1)
    },

    setSince(since) {
      this.query = runsFilter.SinceTerm.set(this.query, since)
    },

    setStates(states) {
      this.query = runsFilter.StateTerm.set(this.query, states)
    },
  },
}
</script>

<style lang="scss">
// FIXME: Elsewhere
.flex-margin {
  display: flex;
  > * {
    margin-right: 16px;
  }
  > :last-child {
    margin-right: 0;
  }
}
</style>

<style lang="scss" scoped>
.search-input {
  width: 50%;
}
</style>
