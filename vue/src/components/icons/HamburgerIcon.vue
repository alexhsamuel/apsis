<template lang="pug">
   svg(viewBox="0 000 1800 1800", xmlns="http://www.w3.org/2000/svg" style="width: 1rem;")
      path(
        d="M 300 700 H 1500 M 300 1100 H 1500 M 300 1500 H 1500"
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
