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
      console.log('input for', this.value)
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
        console.log('set', input, time)
        this.$emit('input', time)
        this.$emit('change', time)
      }
    },
  },
}
</script>

<style lang="scss" scoped>
.top {
  display: flex;
}

input {
  height: 100%;
  border-radius: 0;
}

.button {
  border-radius: 0;
  padding: 0 8px;
}

</style>
