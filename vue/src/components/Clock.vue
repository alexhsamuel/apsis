<template>
  <div>
    <span>
      {{ formatTime(store.state.time, store.state.timeZone, TIME_FORMAT) }}
    </span>
    <select id="timeZone" class="uk-select uk-form-width-small" v-model="timeZone" v-on:change="onTimeZoneChange">
      <option v-for="tz in timeZones" v-bind:key="tz" v-bind:value="tz">{{ shortTimeZone(tz) }}</option>
    </select>
  </div>
</template>

<script>
import { formatTime } from '../format'
import store from '../store'

export default {
  data() {
    return {
      store,
      timeZone: store.state.timeZone,
      timeZones: [
        Intl.DateTimeFormat().resolvedOptions().timeZone,
        'UTC',
        'Asia/Tokyo',
        'Europe/London',
        'America/New_York',
      ],
      TIME_FORMAT: 'YYYY-MM-DD HH:mm:ss Z',
    }
  },

  methods: {
    formatTime,

    shortTimeZone(tz) {
      const parts = tz.split('/')
      return parts[parts.length - 1].replace('_', ' ')
    },

    onTimeZoneChange(event) {
      const tz = event.target.value
      this.store.setTimeZone(tz)
    }
  },

}
</script>

<style scoped>
#timeZone {
  height: 3.5ex;
}
</style>

