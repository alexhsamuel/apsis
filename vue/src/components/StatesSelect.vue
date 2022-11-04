<template lang="pug">
DropList(v-model="selIdx")
  div.row-centered(v-for="[label, states] in options")
    div.label {{ label }}       
    div.states
      State(v-for="state in states" :key="state" :state="state")

</template>

<script>
import { findIndex, isEqual } from 'lodash'
import DropList from '@/components/DropList'
import State from './State'

export default {
  name: 'StatesSelect',
  props: ['value'],

  components: {
    DropList,
    State,
  },

  data() {
    const options = [
      ['All States', []],
      ['Scheduled', ['scheduled']],
      ['Waiting', ['waiting']],
      ['Held', ['scheduled', 'waiting']],
      ['Running', ['starting', 'running']],
      ['Successful', ['success']],
      ['Unsuccessful', ['failure', 'error']],
      ['Started', ['running', 'success', 'failure', 'error', 'skipped']],
    ]

    // Convert our model, a list of states, to DropList's model, a selection idx.
    let selIdx = findIndex(options, o => isEqual(o[1], this.value))
    // FIXME: No match?  Show the "all states" option.
    selIdx = selIdx === -1 ? 0 : selIdx

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

<style lang="scss" scoped>
.label {
  margin-right: 1em;
  flex-basis: 100%;
}

.states {
  white-space: nowrap;
}
</style>
