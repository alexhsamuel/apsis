<template lang="pug">
div
  JobsList(
    :path="path"
    @path="path = $event"
    :keywords="keywords"
    @keywords="keywords = $event"
    :labels="labels"
    @labels="labels = $event"
  )

</template>

<script>
import JobsList from '@/components/JobsList'

function toPathStr(path) {
  return (
    !path ? ''
    : Array.isArray(path) ? path.join('/')
    : path
  )
}

function toPathParts(path) {
  return (
    !path ? []
    : Array.isArray(path) ? path
    : path.split('/')
  )
}

export default {
  name: 'JobsView',
  props: {
  },

  components: {
    JobsList,
  },

  data() {
    const labels = this.$route.query.labels
    const keywords = this.$route.query.keywords

    return {
      keywords: keywords ? keywords.split(',') : null,
      labels: labels ? labels.split(',') : null,
      path: toPathStr(this.$route.params.path),
    }
  },

  methods: {
    pushRoute() {
      const joinWords = (words) => words !== null ? words.join(',') : undefined
      this.$router.push({
        params: {
          path: toPathParts(this.path),
        },
        query: {
          keywords: joinWords(this.keywords),
          labels: joinWords(this.labels),
        }
      })
    },
  },

  watch: {
    '$route'(to) {
      const keywords = this.$route.query.keywords
      const labels = this.$route.query.labels
      console.log('$route to', keywords, labels)

      this.keywords = keywords ? keywords.split(',') : null
      this.labels = labels ? labels.split(',') : null
      this.path = toPathStr(this.$route.params.path)
    },

    path() { this.pushRoute() },
    keywords() { this.pushRoute() },
    labels() { this.pushRoute() },
  },
}
</script>

<style lang="scss" scoped>
</style>
