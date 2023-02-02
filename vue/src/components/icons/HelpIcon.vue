<template lang="pug">
  svg(viewBox="0 0 24 24")
    circle(cx="12" cy="12" r="10" fill="none" :stroke="color" stroke-width="3")
    path(
      d="M 12 6 a 4 4 0 0 0 -3.5 3.5 1 1 0 0 0 2 0 A 1.5 1.5 0 1 1 12 11 a 1 1 0 0 0 -1 1 v 2 a 1 1 0 0 0 2 0 v -1.2 A 3.5 3.5 0 0 0 12 6 z"
      :fill="color"
      :stroke="color"
      stroke-width="1"
    )
    circle(cx="12" cy="17.5" r="1.7" :fill="color")
</template>

<script>
export default {
  props: {
    color: {
      type: String,
      default: '#ccc',
    },
  }
}
</script>
