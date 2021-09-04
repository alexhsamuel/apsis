<template lang="pug">
span
  span: a.dirnav(v-on:click="$emit('path', '')")
    div.folder-icon(
      uk-icon="icon: home"
      ratio="0.8"
      style="display: relative; top: -3px;"
    )

  span(v-if="this.parts.length > 0")
    |  / 
    span(v-for="[subdir, name] in prefixes")
      a.dirnav(v-on:click="$emit('path', subdir)") {{ name }}
      |  / 
    | {{ last }}

</template>

<script>
export default {
  name: 'PathNav',
  props: {
    path: { type: String },
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
