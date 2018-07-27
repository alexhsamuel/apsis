<template lang="pug">
div
  input.uk-input(v-model="argsInput" v-on:change="args = argsInput")
  RunsList(:args="args")
</template>

<script>
import RunsList from '@/components/RunsList'

export default {
  name: 'RunsView',
  components: {
    RunsList,
  },

  data() {
    return {
      args: '',
      argsInput: '',
    }
  }
}
</script>

<style lang="scss">
</style>
