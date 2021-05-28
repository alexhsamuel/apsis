<template lang="pug">
div
  table.fields
    tr(v-for="[key, value] in fields" :key="key")
      th {{ key }}
      td(:class="getClass(key)") {{ value }}

</template>

<script>
import { toPairs } from 'lodash'

export default {
  props: ['program'],

  computed: {
    fields() {
      return toPairs(this.program)
        .filter(([key, value]) => key !== 'str')
        .sort((a, b) => a[0] === 'type' ? -1 : b[0] === 'type' ? 1 : 0)
    },
  },

  methods: {
    getClass(key) {
      if (key === 'command')
        return ['code', 'multiline']
      else if (key === 'argv')
        return ['code']
      else
        return ''
    },

  },
}
</script>

<style lang="scss" scoped>
table {
  margin-bottom: 0;
}
.multiline {
  white-space: pre;
}
</style>
