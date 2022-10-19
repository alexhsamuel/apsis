<template lang="pug">
select(
  v-model="timeZone"
  v-on:change="onTimeZoneChange"
)
  option(
    v-for="tz in timeZones"
    :key="tz"
    :value="tz"
  ) {{ shortTimeZone(tz) }}

</template>

<script>
import store from '../store'

const timeZones = [
  'UTC',
  'Asia/Tokyo',
  'Europe/London',
  'America/New_York',
]

const localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
if (!timeZones.includes(localTimeZone))
  timeZones.splice(0, 0, localTimeZone)

export default {
  name: 'TimeZoneSelect',
  data() {
    return {
      store,
      timeZone: store.state.timeZone,
      timeZones,
    }
  },

  methods: {
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

<style lang="scss" scoped>
@import 'src/styles/vars.scss';

select {
  display: inline-block;
  vertical-align: middle;
  width: 130px;
  background: white;
  border: 1px solid $global-frame-color;
  padding-left: 4px;
  height: 3.5ex;
  font: inherit;
  color: $global-color;
}
</style>
