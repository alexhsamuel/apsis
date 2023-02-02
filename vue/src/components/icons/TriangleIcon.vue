<template lang="pug">
  svg(viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" style="width: 1rem;")
    path(
      d="M 200 500 L 1600 500 L 900 1500 L 200 500"
      stroke="none"
      :transform="rotation"
      :fill="color"
    )
</template>

<script>
export default {
  props: {
    color: {
      type: String,
      default: '#555',
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
