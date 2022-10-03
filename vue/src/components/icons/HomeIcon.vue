<template lang="pug">
   svg(viewBox="0 000 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      path(
        d="M 400 1500 L 400 900 L 200 900 L 900 200 L 1600 900 L 1400 900 L 1400 1500 L 400 1500"
        :stroke="color"
        stroke-width="100"
        stroke-linecap="round"
        fill="none"
      )
</template>

<script>
export default {
  props: {
    color: {
      type: String,
      default: '#333',
    }
  },
}
</script>
