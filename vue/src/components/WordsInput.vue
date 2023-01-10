<template lang="pug">
  input(
    :value="text"
    @input="onInput"
    @change="$emit('change')"
  )
</template>

<script>
import { isEqual } from 'lodash'

export default { 
  name: 'WordsInput',
  props: {
    value: {type: Array, default: null},
  },

  computed: {
    text() {
      return this.value ? this.value.join(' ') : ''
    },
  },

  methods: {
    onInput(ev) {
      const text = ev.target.value.trim()
      const value = text ? text.split(' ') : null
      if (!isEqual(value, this.value))
        this.$emit('input', value)
    },
  },
}
</script>
