<template lang="pug">
span.uk-inline
  span.uk-form-icon(uk-icon="icon: search")
  input.uk-input(
    v-model="input"
    v-on:change="search()"
    v-on:keyup.esc="input = ''; search()"
  )

</template>

<script>
export default {
  props: ['value'],

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

.uk-form-icon {
  pointer-events: auto;
  color: #999;
}
</style>
