<template lang="pug">
span
  a.dirnav(v-on:click="$emit('path', '')")
    HomeIcon(
  )

  span(v-if="this.parts.length > 0")
    |  / 
    span(v-for="[subdir, name] in prefixes")
      a.dirnav(v-on:click="$emit('path', subdir)") {{ name }}
      |  / 
    | {{ last }}

</template>

<script>
import HomeIcon from '@/components/icons/HomeIcon'

export default {
  name: 'PathNav',
  props: {
    path: { type: String },
  },
  components: {
    HomeIcon,
  },

  computed: {
    parts() {
      return this.path ? this.path.split('/') : []
    },

    prefixes() {
      const prefixes = []
      for (var i = 0; i < this.parts.length - 1; ++i)
        prefixes.push([this.parts.slice(0, i + 1).join('/'), this.parts[i]])
      return prefixes
    },

    last() {
      return this.parts[this.parts.length - 1]
    },
  },
}
</script>

<style lang="scss" scoped>
@import '../styles/vars.scss';

.dirnav{
  border: 1px solid transparent;
  &:hover {
    border: 1px solid $global-frame-color;
  }
}
</style>
