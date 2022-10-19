<template lang="pug">
   svg(viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px" style="position: relative; top: 4px")
      path(
        d="M 400 700 L 1400 700 L 900 1300 L 400 700"
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
      default: '#333',
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
