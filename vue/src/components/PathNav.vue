<template lang="pug">
span
  span(v-if="this.parts.length > 0")
    a.home.dirnav(@click="$emit('path', '')")
      HomeIcon(
    )

    span(v-for="[subdir, name] in prefixes")
      a.part.dirnav(@click="$emit('path', subdir)") {{ name }}
      |  / 
    span.part {{ last }}

  span(v-else style="color: #888")
    | all jobs

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

.home {
  margin-right: 8px;
  &.dirnav:hover {
    border: 1px dotted $global-light-color;
  }
}

.part {
  cursor: default;
}

.dirnav {
  border: 1px solid transparent;
  &:hover {
    text-decoration: underline;
  }
}
</style>
