<template lang="pug">
div
  div(v-if="groups")
    h1 Groups

    div.groups
      div.group(v-for="(conns, group_id) in groups" :key="group_id")
        div.name()
          div.group_id {{ group_id }}
          div.count {{ conns.length }} connection{{ conns.length == 1 ? '' : 's' }}

        div.conns
          div.conn(v-for="conn in conns")
            div.basics
              label Connection ID
              span {{ conn.info.conn.conn_id }}
              label Host
              span {{ conn.info.proc.hostname }}
              label User:Group
              span {{ conn.info.proc.username }}:{{ conn.info.proc.groupname }}
              label PID
              span {{ conn.info.proc.pid }}
            div.stats
              template(v-for="(value, name) in conn.info.stats")
                label {{ name }}
                div {{ value }}

        div.rule

</template>

<script>
import store from '@/store.js'

export default {
  props: [],

  data() {
    return {
      store,
      groups: undefined,
    }
  },

  mounted() {
    this.fetchGroups()
  },

  methods: {
    fetchGroups() {
      const url = '/api/procstar/groups'
      fetch(url).then(async (rsp) => {
          if (rsp.ok)
            this.groups = Object.freeze(await rsp.json())
          // FIXME: Handle error, e.g. no procstar server.
      })
    },
  },

}
</script>

<style lang="scss" scoped>
@import 'src/styles/vars.scss';

groups {
  font-size: 100%;
}

.group_id {
  font-size: 120%;
  font-weight: bold;
}

.groups {
  display: flex;
  row-gap: 32px;

  .group {
    display: grid;
    grid-template-columns: 24ex 1fr;
  }

  .name {
    padding: 8px 16px 8px 0;
  }

  .rule {
    width: 100%;
    height: 1px;
    grid-column-start: 1;
    grid-column-end: 3;
    margin-top: 8px;
    margin-bottom: 8px;
    background: $apsis-frame-color;
  }
}

.conns {
  display: flex;
  flex-direction: column;
  row-gap: 4px;

  .conn {
    border: 1px solid $apsis-frame-color;

    display: flex;
    white-space: nowrap;

    > *:first-child {
      border-right: 1px solid $apsis-frame-color;
    }
    > * {
      padding: 8px 16px;
    }

    .basics {
      display: grid;
      grid-template-columns: 16ex 1fr;

      label {
        font-weight: bold;
      }

      .conn_id {
        font-family: $base-code-font-family;
      }
    }

    .stats {
      font-family: $base-code-font-family;
      font-size: 85%;
      display: grid;
      grid-template-columns: 1fr 1fr;

      label {
      }
    }
  }
}
</style>
