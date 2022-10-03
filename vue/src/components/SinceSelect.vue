<template lang="pug">
span.since-select
  button(type="button") {{ formatSince(value) }}

  div(uk-dropdown="pos: bottom-left")
    ul.uk-nav.uk-dropdown-nav
      li(v-for="since in ['60m', '6h', '1d', '7d', '30d', '']")
        a(href="#" v-on:click="$emit('input', since)") {{ formatSince(since) }}

</template>

<script>
export default {
  props: ['value'],

  components: {
  },

  computed: {
  },

  methods: {
    formatSince(since) {
      if (since === '')
        return 'All'

      let match = since.match(/^(\d+)m$/)
      if (match)
        return `Last ${parseInt(match[1])} min`

      match = since.match(/^(\d+)h$/)
      if (match)
        return `Last ${parseInt(match[1])} hours`

      match = since.match(/^(\d+)d$/)
      if (match) {
        const days = parseInt(match[1])
        return days === 1 ? 'Last day' : `Last ${days} days`
      }

      return 'Since ' + since
    },
  },
}
</script>

<style lang="scss">
.since-select {
  button {
    width: 100%;
    padding: 0 8px 0 12px;
  }
  li {
    text-transform: uppercase;
    margin-right: 3em;
  }
}
</style>
