<template lang="pug">
div.frame
  div.heading(v-on:click="open = !open" style="cursor: default")
    | {{ title }}
    TriangleIcon(
      :direction="open ? 'down' : 'right'"
      color="#666"
      style="position: relative; top: -1px;"
    )

  div.pad(v-if="open")
    slot

</template>

<script>
import TriangleIcon from '@/components/icons/TriangleIcon'

export default {
  name: 'Frame',
  props: {
    title: {type: String, default: ''},
    closed: {type: Boolean, default: false},
  },
  components: {
    TriangleIcon,
  },

  data() {
    return {
      open: !this.closed,
    }
  },

}
</script>

<style lang="scss" scoped>
.heading {
  display: flex;
  direction: row;
  align-items: center;
  gap: 0 4px;
}
</style>
