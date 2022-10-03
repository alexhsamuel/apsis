<template lang="pug">
span.inline
  span.icon
    SearchIcon(color="#999")
  input(
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
.inline {
  display: inline-block;
  position: relative;
  max-width: 100%;
}

.icon {
  pointer-events: auto;
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 40px;
  display: inline-flex;
  justify-content: center;
  align-items: center;
}

input {
  padding-left: 40px;
}
</style>
