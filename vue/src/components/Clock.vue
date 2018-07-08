<template>
  <span>
    {{ time.toISOString().substr(0, 19) + 'Z' }}
  </span>
</template>

<script>
export default {
  data() {
    return {
      time: new Date(),
    }
  },

  mounted() {
    const tick = () => {
      this.time = new Date()
      window.setTimeout(tick, 1000 - this.time % 1000)
    }
    tick()
  },

}
</script>

<style scoped>
span {
}
</style>

