<template lang="pug">
  input(
    v-model="text"
    @change="onChange"
    @keyup.escape="text = ''; onChange()"
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
    }
  },

  methods: {
    onChange() {
      // Emit 'input' and 'change' only if the value is effectively different.
      const value = this.text ? this.text.split(' ').filter(w => w) : null
      if (!isEqual(value, this.value)) {
        this.$emit('input', value)
        this.$emit('change', value)
      }
    },
  },
}
</script>

<style lang="scss" scoped>
input {
  width: 100%;
}
</style>
