<template lang="pug">
  span(class="tooltip")
    span( 
      v-bind:style="'color: ' + color"
      v-bind:uk-icon="'icon: ' + icon + '; ratio: 1.0'"
    )
    span(
      v-if="name"
      class="name"
      v-bind:style="'color: ' + color"
    ) {{ state }}
    span(class="tooltiptext") {{ state.toUpperCase() }}
</template>

<script>
const ICONS = {
  'new'            : ['#000000', 'tag'],
  'scheduled'      : ['#a0a0a0', 'future'],
  'waiting'        : ['#808080', 'sign-in'],  // ban?
  'starting'       : ['#80b000', 'play'],
  'running'        : ['#a0a000', 'play-circle'],
  'error'          : ['#a00060', 'warning'],
  'success'        : ['#00a000', 'check'],
  'failure'        : ['#a00000', 'close'],
}

export default {
  name: 'State',
  props: ['state', 'name'],

  computed: {
    color() { return ICONS[this.state][0] },
    icon() { return ICONS[this.state][1] },
  }
}
</script>

<style lang="scss" scoped>
.name {
  margin-left: 0.3em;
  text-transform: uppercase;
  font-size: 85%;
}
</style>
