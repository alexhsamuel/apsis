<template lang="pug">
div(v-if="numPages > 1")
  .link(
    :class="{'hidden': currentPage == 0}"
    v-on:click="incPage(-1)"
  )
    span(uk-icon="icon: triangle-left")

  .link(
    v-for="(p, i) in pages" 
    :key="i"
    :class="{ 'current': p === currentPage, 'hidden': p === ELLIPSIS }"
    v-on:click="setPage(p)"
  )
    span {{ p === ELLIPSIS ? p : p + 1 }}

  .link(
    :class="{'hidden': currentPage == numPages - 1}"
    v-on:click="incPage(1)"
  )
    span(uk-icon="icon: triangle-right")

</template>

<script>
import { concat, range } from 'lodash'

export default {
  props: {
    page: Number,
    numPages: Number,
  },

  data() { 
    return {
      currentPage: this.page,
      ELLIPSIS: '\u22ef',
    }
  },

  watch: {
    page(val) {
      this.currentPage = val
    }
  },

  computed: {
    pages() {
      const num = this.numPages
      const page = this.page
      if (num < 10)
        return range(num)
      else if (page < 5)
        return concat(range(7), this.ELLIPSIS, num - 1)
      else if (page >= num - 5)
        return concat(0, this.ELLIPSIS, range(num - 7, num))
      else
        return concat(0, this.ELLIPSIS, range(page - 2, page + 3), this.ELLIPSIS, num - 1)
    },
  },

  methods: {
    setPage(page) {
      if (page === this.ELLIPSIS)
        return
      if (page >= 0 && page < this.numPages) {
        this.currentPage = page
        this.$emit('update:page', this.currentPage)
      }
    },

    incPage(inc) {
      this.setPage(this.currentPage + inc)
    },
  },

}
</script>

<style lang="scss" scoped>
.link {
  display: inline-block;
  margin: 0 2px;
  padding-left: 4px;
  padding-right: 4px;
  width: 1.5em;
  text-align: center;
  color: #444;
  border-radius: 4px;
  border: 1px solid white;

  &:first-child {
    padding-left: 0;
  }
  &:last-child {
    padding-right: 0;
  }

  cursor: default;
  &:not(.hidden):hover {
    border-color: #aaa;
  }

  &.current {
    background-color: #0a5;
    border-color: #0a5;
    color: white;

    &:hover {
      border-color: #0a5;
    }
  }

}

// Adjust vertical positioning of icons.
.uk-icon svg {
  padding-bottom: 0.2rem;
}

.hidden {
  color: #ccc;
}
</style>
