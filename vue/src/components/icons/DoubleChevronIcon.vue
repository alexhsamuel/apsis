<template lang="pug">
  svg(viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" style="width: 1rem;")
    path(
      d="M 1600 200 L 900 900 L 200 200 M 1600 900 L 900 1600 L 200 900"
      :stroke="color"
      stroke-width="150"
      :transform="rotation"
      fill="none"
    )
</template>

<script>
export default {
  props: {
    color: {
      type: String,
      default: '#111',
    },
    direction: {
      type: String,
      default: 'up',
    }
  },
  computed: {
    rotation() {
      const angle = {
        'up': 180,
        'right': 270,
        'down': 0,
        'left': 90,
      }[this.direction]
      return 'rotate(' + angle + ', 900, 900)'
    },
  },
}
</script>
