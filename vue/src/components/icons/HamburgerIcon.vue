<template lang="pug">
   svg(viewBox="0 000 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
      path(
        d="M 300 500 H 1500 M 300 900 H 1500 M 300 1300 H 1500"
        :stroke="color"
        stroke-width="100"
        stroke-linecap="round"
        fill="none"
      )
</template>

<script>
export default {
  // name: 'HamburgerIcon',
  props: {
    color: {
      type: String,
      default: '#333',
    }
  },
}
</script>
