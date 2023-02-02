<template lang="pug">
  div.top
    input(
      placeholder="now"
      :value="input"
      @change="set($event.target.value)"
    )
    div.button(
      @click="set('')"
      :disabled="value === 'now'"
    ) Now
</template>

<script>
import store from '@/store.js'
import { formatTime, parseTime } from '../time'

export default { 
  name: 'TimeInput',
  props: {
    value: {type: String, default: ''},
  },

  computed: {
    input() {
      return (
        this.value === 'now' ? '' 
        : formatTime(new Date(this.value), store.state.timeZone)
      )
    },
  },

  methods: {
    inputToTime(input) {
      return (
        input === '' || input === 'now' ? 'now'
        : parseTime(input, false, store.state.timeZone).tz('UTC').format()
      )
    },

    set(input) {
      const time = this.inputToTime(input.trim())
      if (time !== this.value) {
        this.$emit('input', time)
        this.$emit('change', time)
      }
    },
  },
}
</script>

<style lang="scss" scoped>
@import '@/styles/index.scss';

.top {
  display: flex;
  flex-direction: row;
}

input {
  height: 100%;
  border-radius: 0;
  background-color: $global-background;
}

.button {
  border-radius: 0;
  padding: 0 8px;
}

</style>
