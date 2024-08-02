<template lang="pug">
div
  div(v-if="groups")
    div.controls
      button(@click="fetchGroups()") Refresh

      div
        input(type="checkbox" v-model="showDisconnected")
        label Show disconnected

    h1 Groups

    div.groups
      div.group(v-for="(conns, group_id) in filteredGroups" :key="group_id")
        div.name()
          div.group_id {{ group_id }}
          div.count {{ conns.filter(c => c.shutdown_state === 'active').length }} active connections
          div.count {{ conns.length }} connections

        div.conns
          div.conn(v-for="conn in conns" :class="{ connected: conn.info.stats.connected }")
            div.basics
              label State
              span(:class="['shutdown-' + conn.shutdown_state]") {{ conn.shutdown_state }}
              label Host
              span {{ conn.info.proc.hostname }}
              label User &amp; Group
              span {{ conn.info.proc.username }}:{{ conn.info.proc.groupname }}
              label PID
              span {{ conn.info.proc.pid }}
              label Connection ID
              span {{ conn.info.conn.conn_id }}
              label Restricted Exe
              span
                tt {{ conn.info.conn.restricted_exe }}
            div.stats
              template(v-for="(value, name) in conn.info.stats")
                label {{ name.replaceAll('_', ' ') }}
                div {{ value }}

</template>

<script>
import { filter, mapValues } from 'lodash'

import store from '@/store.js'

export default {
  props: [],

  data() {
    return {
      store,
      groups: undefined,
      timerId: undefined,
      showDisconnected: true,
    }
  },

  mounted() {
    this.fetchGroups()
  },

  methods: {
    fetchGroups() {
      if (self.timerId)
        clearTimeout(self.timerId)

      const url = '/api/procstar/groups'
      fetch(url).then(async (rsp) => {
          if (rsp.ok)
            this.groups = await rsp.json()
          // FIXME: Handle error, e.g. no procstar server.
      })

      // Load again in a minute.
      self.timerId = setTimeout(this.fetchGroups, 60 * 1000)
    },
  },

  computed: {
    filteredGroups() {
      let groups = this.groups
      if (groups) {
        if (!this.showDisconnected)
          // Hide disconnected connections.
          groups = mapValues(groups, g => filter(g, c => c.info.stats.connected))
        // Sort connections in each group by hostname.
        mapValues(groups, g => g.sort(c => c.info.proc.hostname))
      }
      return groups
    },
  },
}
</script>

<style lang="scss" scoped>
@import 'src/styles/vars.scss';

$gray: #e8e8e8;

.controls {
  margin-bottom: 32px;

  display: flex;
  align-items: center;
  column-gap: 24px;

  button {
    height: 28px;
  }
}

groups {
  font-size: 100%;
}

.group_id {
  font-size: 120%;
  font-weight: bold;
}

.groups {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  row-gap: 24px;

  .group {
    border: 1px solid $gray;
    border-radius: 4px;

    display: grid;
    grid-template-columns: 24ex 1fr;
  }

  .name {
    padding: 8px 16px;
    background: $gray;
  }
}

.conns {
  display: flex;
  flex-direction: column;

  .conn {
    &:not(.connected) {
      color: #a0a0a0;
    }

    border-left: 1px solid $gray;
    border-bottom: 1px solid $gray;
    &:last-child {
      border-bottom: none;
    }

    display: grid;
    grid-template-columns: 1fr 1fr;
    white-space: nowrap;

    > * {
      padding: 8px 16px;
    }

    .basics {
      align-self: start;

      display: grid;
      grid-template-columns: 16ex 1fr;
      row-gap: 4px;

      label {
        font-weight: bold;
      }
    }

    .shutdown-active {
      color: green;
    }
    .shutdown-idling {
      color: orange;
    }
    .shutdown-done {
      color: red;
    }

    .stats {
      font-size: 85%;
      display: grid;
      grid-template-columns: 28ex 1fr;

      font-family: $base-code-font-family;
    }

    .bold {
      font-weight: bold;
    }
  }
}
</style>
