<template lang="pug">
div.frame
  div.heading(v-on:click="open = !open" style="cursor: default")
    | {{ title }}
    span(
      :uk-icon="'ratio: 1.4; icon: ' + (open ? 'triangle-down' : 'triangle-right')"
      style="color: #666; position: relative; top: -1px;"
    )

  div.pad(v-if="open")
    slot

</template>

<script>
export default {
  name: 'Frame',
  props: {
    title: {type: String, default: ''},
    closed: {type: Boolean, default: false},
  },

  data() {
    return {
      open: !this.closed,
    }
  },

}
</script>
