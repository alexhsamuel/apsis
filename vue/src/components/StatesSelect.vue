<template lang="pug">
span.states-select
  DropList(v-model="selIdx")
    div(v-for="[label, states] in options")
      span(style="float: right")
        State(v-for="state in states" :key="state" :state="state")
      span.label {{ label }}       

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
      ['Started', ['running', 'success', 'failure', 'error']],
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

<style lang="scss">
</style>
