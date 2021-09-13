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
        .then(async (response) => {
          if (response.ok) {
            const result = await response.json()
            if (result.show_run_id)
              // Got a hint to nav to a new run.
              // FIXME: Encapsulate this part of the API somewhere.
              this.$router.push({ name: 'run', params: { run_id: result.show_run_id } })
          }
        })
    },

  },

}
</script>

<style scoped>
.action {
  text-transform: capitalize;
}

.button {
  background: #f0f6f0;
  padding: 6px 8px 6px 8px;
  margin: 0 3px;
  border-radius: 3px;
  border: 1px solid #aaa;
  font-size: 85%;
  text-transform: uppercase;
  cursor: default;
}

.button:hover {
  background: #90e0a0;
}

</style>

