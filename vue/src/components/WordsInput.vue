<template lang="pug">
  input(
    v-model="text"
    @input="onInput"
    @change="onChange"
  )
</template>

<script>
import { isEqual } from 'lodash'

export default { 
  name: 'WordsInput',
  props: {
    value: {type: Array, default: null},
  },

  data() {
    return {
      text: this.value ? this.value.join(' ') : '',
      lastInputValue: this.value,
    }
  },

  computed: {
    inputValue() {
      return this.text ? this.text.split(' ').filter(w => w) : null
    },
  },

  methods: {
    onChange() {
      // Emit 'change' only if the value has effectively changed.
      if (!isEqual(this.inputValue, this.lastInputValue)) {
        this.$emit('change', this.inputValue)
        this.lastInputValue = this.inputValue
      }
    },

    onInput() {
      // Emit 'input' only if the value is effectively different.
      if (!isEqual(this.inputValue, this.value))
        this.$emit('input', this.inputValue)
    },
  },
}
</script>
