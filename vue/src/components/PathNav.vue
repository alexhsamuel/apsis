<template lang="pug">
span
  span(v-for="[subdir, name] in prefixes")
    a.dirnav(v-on:click="$emit('path', subdir)") {{ name }}
    |  / 

</template>

<script>
export default {
  name: 'PathNav',
  props: {
    path: { type: String },
  },

  computed: {
    prefixes() {
      const parts = this.path ? this.path.split('/') : []
      const prefixes = []
      for (var i = 0; i < parts.length; ++i)
        prefixes.push([parts.slice(0, i + 1).join('/'), parts[i]])
      return prefixes
    },
  },
}
</script>
