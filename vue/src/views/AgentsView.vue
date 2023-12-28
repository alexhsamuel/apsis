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
          div.count {{ conns.length }} connection{{ conns.length == 1 ? '' : 's' }}

        div.conns
          div.conn(v-for="conn in conns" :class="{ connected: conn.info.stats.connected }")
            div.basics
              label Host
              span {{ conn.info.proc.hostname }}
              label User &amp; Group
              span {{ conn.info.proc.username }}:{{ conn.info.proc.groupname }}
              label PID
              span {{ conn.info.proc.pid }}
              label Connection ID
              span {{ conn.info.conn.conn_id }}
            div.stats
              template(v-for="(value, name) in conn.info.stats")
                label(:class="{ bold: name === 'connected' }") {{ name }}
                div(:class="{ bold: name === 'connected' }") {{ value }}

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
    border: 1px solid $apsis-frame-color;

    display: grid;
    grid-template-columns: 24ex 128ex;
  }

  .name {
    padding: 8px 16px;
    background: $apsis-frame-color;
  }
}

.conns {
  display: flex;
  flex-direction: column;

  .conn {
    &:not(.connected) {
      color: #a0a0a0;
    }

    border-left: 1px solid $apsis-frame-color;
    border-bottom: 1px solid $apsis-frame-color;
    &:last-child {
      border-bottom: none;
    }

    display: grid;
    grid-template-columns: 50% 50%;
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

      .conn_id {
        font-family: $base-code-font-family;
      }
    }

    .stats {
      font-family: $base-code-font-family;
      font-size: 85%;
      display: grid;
      grid-template-columns: 1fr 1fr;
    }

    .bold {
      font-weight: bold;
    }
  }
}
</style>
