<template lang="pug">
div
  table.fields
    thead(v-if="false")
      tr
        th Time
        th Message

    tbody
      tr(v-for="rec, i in history")
        th: Timestamp(:time="rec.timestamp")
        td {{ rec.message }}

</template>

<script>
import store from '@/store'
import Timestamp from '@/components/Timestamp'

export default {
  props: ['run_id'],
  components: {
    Timestamp,
  },

  data() {
    return {
      history: null,
    }
  },

  created() {
    this.load()
  },

  methods: {
    load() {
      const url = '/api/v1/runs/' + this.run_id + '/history'
      fetch(url)
        .then(async (rsp) => {
          if (rsp.ok)
            this.history = (await rsp.json()).run_history
          else if (rsp.status === 404)
            this.history = null
          else
            store.state.errors.add('fetch ' + url + ' ' + rsp.status + ' ' + await rsp.text())
        })
    },
  },

}
</script>

<style lang="scss" scoped>
table {
  tr {
    td, th {
      border-bottom: 1px solid #eee;
    }
  }
  tr:last-child > {
    > td, > th {
      border-bottom: none;
    }
  }
}
</style>
