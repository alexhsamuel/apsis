<template lang="pug">
span.run-args
  span.run-arg(v-for="[param, arg] in pairs")
    span.param {{ param }}
    span.eq =
    span.arg {{ arg }}
</template>

<script>
import { toPairs } from 'lodash'

export default {
  props: [
    'args',
  ],

  computed: {
    pairs() {
      console.log('this.args', this.args)
      return toPairs(this.args)
    },
  }
}
</script>

<style lang="scss">
span.run-args {
  span.run-arg {
    & + .run-arg {
      margin-left: 6px;
    }
    display: inline-block;

    &:hover {
      text-decoration: underline;
    }

    .param {
      color: #aaa;
    }
    .eq {
      color: #aaa;
    }
    .arg {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}
</style>
