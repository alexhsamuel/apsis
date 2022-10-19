<template lang="pug">
DropList(v-model="selIdx")
  div.item(v-for="[label, _] in options") {{ label }}

</template>

<script>
import { findIndex } from 'lodash'
import DropList from '@/components/DropList'

export default {
  props: ['value'],

  components: {
    DropList,
  },

  data() {
    const options = [
      ['Last 60 min', '60m'],
      ['Last 6 hours', '6h'],
      ['Last day', '1d'],
      ['Last 7 days', '7d'],
      ['Last 30 days', '30d'],
      ['All', ''],
    ]

    // Convert our model into DropLists's selection index.
    let selIdx = findIndex(options, o => o[1] === this.value)
    // FIXME: No match?  Use 'all'.
    selIdx = selIdx === -1 ? 5 : selIdx

    return {
      options,
      selIdx,
    }
  },

  watch: {
    selIdx(idx) {
      // DropList provides the index of the selection.  Translate into states.
      this.$emit('input', this.options[idx][1])
    },
  },
}
</script>

<style lang="scss" scoped=true>
.item {
  text-transform: uppercase;
  box-sizing: border-box;
  width: 100%;
}
</style>
