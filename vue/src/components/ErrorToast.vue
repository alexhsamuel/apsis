<template lang="pug">
div
  div.error(v-for="err in Object.values(errors.errors)" :key="err.errorId")
    button.close(v-on:click="close(err.errorId)")
      CloseIcon
    | ERROR:
    | 
    tt {{ err.message }}
</template>

<script>
import CloseIcon from '@/components/icons/CloseIcon'
import store from '@/store'

export default {
  props: [],

  components: {
    CloseIcon,
  },

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
  width: 28px;
  height: 28px;
  padding: 2px;
  margin-right: 12px;
  border: 1px solid transparent;

  &:hover {
    border: 1px solid #888;
  }

  & > svg {
    position: relative;
    top: -4px;
  }
}
</style>
