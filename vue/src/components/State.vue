<template lang="pug">
  span.tooltip
    svg(v-if="state === 'new'" viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      circle(cx="900" cy="900" r="800" fill="#c0c0c0")

    svg(v-else-if="state === 'scheduled'" viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      circle(cx="900" cy="900" r="800" fill="#a0a0a0")
      path(d="M 900 400 L 900 900 L 1150 1100" stroke="#ffffff" stroke-width="200" stroke-linecap="round")

    svg(v-else-if="state === 'waiting'" viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      circle(cx="900" cy="900" r="800" fill="#a0a0a0")
      path(d="M 400 900 H 1400" stroke="#ffffff" stroke-width="200" stroke-linecap="round")

    svg(v-else-if="state === 'starting'" viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      circle(cx="900" cy="900" r="800" fill="#a0b090")
      path(d="M 450 1150 H 1350 L 900 450 L 450 1150" fill="#ffffff")

    svg(v-else-if="state === 'running'" viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      circle(cx="900" cy="900" r="800" fill="#a0b040")
      path(d="M 650 450 V 1350 L 1350 900 L 650 450" fill="#ffffff")

    svg(v-else-if="state === 'stopping'" viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      circle(cx="900" cy="900" r="800" fill="#b07040")
      path(d="M 450 650 H 1350 L 900 1350 L 450 650" fill="#ffffff")

    svg(v-else-if="state === 'error'" viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      circle(cx="900" cy="900" r="800" fill="#ff0060")
      path(d="M 900 400 V 1050 M 900 1350 V 1400" stroke="#ffffff" stroke-width="200" stroke-linecap="round" fill="transparent")

    svg(v-else-if="state === 'success'" viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      circle(cx="900" cy="900" r="800" fill="#40a060")
      path(d="M 500 900 L 750 1200 L 1300 600" stroke="#ffffff" stroke-width="200" stroke-linecap="round" fill="transparent")

    svg(v-else-if="state === 'failure'" viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      circle(cx="900" cy="900" r="800" fill="#a05050")
      path(d="M 600 600 L 1200 1200 M 600 1200 L 1200 600" stroke="#ffffff" stroke-width="200" stroke-linecap="round" fill="transparent")

    svg(v-else-if="state === 'skipped'" viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      circle(cx="900" cy="900" r="800" fill="#d0d0d0")
      path(d="M 0 0 L 1800 1800" stroke="#ffffff" stroke-width="200")

    div(
      v-if="name"
      class="name"
      :style="style"
    ) {{ state }}
    span.tooltiptext(v-if="! name") {{ state.toUpperCase() }}
</template>

<script>
const COLORS = {
  'new'            : '#000000',
  'scheduled'      : '#a0a0a0',
  'waiting'        : '#808080',
  'starting'       : '#80b000',
  'running'        : '#a0a000',
  'error'          : '#ff0060',
  'success'        : '#00a000',
  'failure'        : '#a00000',
  'skipped'        : '#606060',
}

export default {
  name: 'State',
  props: ['state', 'name'],

  computed: {
    style() {
      return { color: COLORS[this.state] } 
    },
  }
}
</script>

<style lang="scss" scoped>
span {
  display: inline-flex !important;
  flex-direction: row;
  align-items: center;
  gap: 2px;
}
.name {
  margin-left: 0.3em;
  text-transform: uppercase;
  font-size: 85%;
}
</style>
