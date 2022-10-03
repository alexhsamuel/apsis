<template lang="pug">
span.uk-inline
  span.icon.uk-form-icon
    SearchIcon(color="#999")
  input.uk-input(
    v-model="input"
    v-on:change="search()"
    v-on:keyup.esc="input = ''; search()"
  )

</template>

<script>
import SearchIcon from '@/components/icons/SearchIcon'

export default {
  props: ['value'],

  components: {
    SearchIcon,
  },

  data() {
    return {
      input: this.value,
    }
  },

  methods: {
    search() {
      this.$emit('input', this.input)
    }
  },

  watch: {
    value(value) {
      this.input = value
    },
  },
}
</script>

<style lang="scss" scoped>
.uk-input {
  &:focus {
    border-color: #6b9;  // FIXME: Elsewhere.
  }
}

.icon {
  pointer-events: auto;
}
</style>
