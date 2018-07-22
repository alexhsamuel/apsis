<template lang="pug">
  span(
    class="action"
    :class="{ button: button }"
    v-on:click="do_action(url)"
  ) {{ action }}
</template>

<script>
export default {
  name: 'ActionButton',
  props: ['action', 'url', 'button'],

  methods: {
    do_action(url) {
      fetch(url, { method: 'POST' })
    },

  },

}
</script>

<style scoped>
.action {
  text-transform: capitalize;
}

.button {
  background: #e0f0e0;
  padding: 2px 6px 2px 8px;
  margin: 0 3px;
  border-radius: 3px;
  font-size: 85%;
  text-transform: uppercase;
  cursor: default;
}

.button:hover {
  background: #90e0a0;
}

</style>

