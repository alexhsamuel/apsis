<template lang="pug">
div
  div.error(v-for="err in Object.values(errors.errors)" :key="err.errorId")
    span(uk-icon="close" v-on:click="close(err.errorId)").close 
    | ERROR:
    | 
    tt {{ err.message }}
</template>

<script>
import store from '@/store'

export default {
  props: [],

  data() {
    return {
      errors: store.state.errors,
    }
  },

  methods: {
    close(errorId) {
      console.log('close', errorId)
      store.state.errors.clear(errorId)
    },
  }
}
</script>

<style lang="scss" scoped>
.error {
  border-top: 1px solid #fee;
  color: #800;
  background: #fcc;
  padding: 12px 40px;
  margin: 0;
}

.close {
  margin-right: 12px;
}
</style>
