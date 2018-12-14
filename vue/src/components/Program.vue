<template lang="pug">
div
  table.fields
    tr(v-for="(value, key) in program" :key="key")
      th {{ key }}
      td(:class="getClass(key)") {{ value }}

</template>

<script>
export default {
  props: ['program'],

  methods: {
    getClass(key) {
      if (key === 'command')
        return ['code', 'multiline']
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
