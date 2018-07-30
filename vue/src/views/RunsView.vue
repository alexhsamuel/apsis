<template lang="pug">
div
  div.controls
    .control
      label.field-label Job &amp; Args
      span.uk-inline
        span.uk-form-icon(
          uk-icon="icon: search"
          style="pointer-events: auto"
          uk-tooltip="title: Filter by JOB-ID and/or ARG=VALUE"
        )
        input.uk-input(
          v-model="argsInput"
          v-on:change="args = argsInput"
          v-on:keyup.esc="argsInput = ''; args = argsInput"
          style="width: auto;"
        )

    .control
      label.field-label State
      select.uk-select(style="width: auto;")
        option All
        option Scheduled
        option Running
        option Started
        option Problem

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

<style lang="scss" scoped>
.control {
  display: inline-block;
  margin: 1em;
}
.control:first-child {
  margin-left: 0;
}
</style>
