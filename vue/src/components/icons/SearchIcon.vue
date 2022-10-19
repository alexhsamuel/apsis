<template lang="pug">
   svg(viewBox="100 100 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      circle(
        cx="900" cy="900" r="600"
        :stroke="color"
        stroke-width="100"
        fill="none"
      )
      path(
        d="M 1325 1325 L 1700 1700"
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
