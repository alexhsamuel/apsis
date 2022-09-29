<template lang="pug">
  span(
    class="operation"
    :class="{ button: button }"
    v-on:click="doOperation()"
  ) {{ operation }}
</template>

<script>
import { capitalize } from 'lodash'
import UIkit from 'uikit'

import { getUrlForOperation } from '@/api.js'

function titleCapitalize(string) {
  return string.split(' ').map(capitalize).join(' ')
}

export default {
  name: 'OperationButton',
  props: ['operation', 'run_id', 'button'],

  methods: {
    doOperation() {
      const url = getUrlForOperation(this.operation, this.run_id)
      UIkit.modal.confirm(
        titleCapitalize(this.operation) + ' ' + this.run_id + '?'
      ).then(() =>
        fetch(url, { method: 'POST' })
          .then(async (response) => {
            if (response.ok) {
              const result = await response.json()
              if (result.show_run_id)
                // Got a hint to nav to a new run.
                // FIXME: Don't nav; users don't like it.  Show the new run instead.
                this.$router.push({ name: 'run', params: { run_id: result.show_run_id } })
            }
          })
      )
    },

  },

}
</script>

<style scoped>
.operation {
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

