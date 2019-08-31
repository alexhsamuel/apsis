<template lang="pug">
div
  table.widetable.joblist
    colgroup
      col(style="min-width: 10%")
      col(style="min-width: 10%")
      col(style="width: 30%;")
      col(style="width: 20%;")

    thead
      tr
        th Job
        th Parameters
        th Description
        th Schedule

    tbody
      tr(
        v-for="[path, subpath, name, job] in jobRows"
        :key="subpath.concat([name]).join('/')"
        :style="job ? {} : {background: '#f8f8f8'}"
      )
        td
          span(style="white-space: nowrap")
            //- indent
            span(:style="{ display: 'inline-block', width: (20 * subpath.length) + 'px' }")

            //- a job
            span(v-if="job")
              Job.name(:job-id="job.job_id" :name="name")

            //- a dir entry
            span.name(v-else)
              div.folder-icon(
                uk-icon="icon: minus-circle" ratio="0.7"
                style="width: 20px"
                v-on:click="toggleCollapse(path)"
                )
              a.dirnav(v-on:click="$emit('dir', path.join('/'))") {{ name }}
              |  /

        td.params
          span.params(v-if="job && job.params.length > 0")
            | {{ join(job.params, ', ') }}

        td.description
          div(v-if="job" v-html="markdown(job.metadata.description || '')")

        td.schedule
          ul(v-if="job")
            li(v-for="(schedule, idx) in job.schedules" :key="idx")
              span(:class="{ disabled: !schedule.enabled }") {{ schedule.str }}

</template>

<script>
import Job from './Job'
import { every, filter, join, map, sortBy, trim } from 'lodash'
import { markdown } from 'markdown'
import Program from './Program'

export function makePredicate(query) {
  const parts = filter(map(query.split(' '), trim))
  if (parts.length === 0)
    return job => true

  // Construct an array of predicates over runs, one for each term.
  const preds = map(parts, part => {
    return job => job.job_id.indexOf(part) >= 0
  })

  // The combined predicate function is true if all the predicates are.
  return job => every(map(preds, f => f(job)))
}

/**
 * Arranges an array of jobs into a tree by job ID path components.
 * 
 * Each node in the tree is [subtrees, jobs], where subtrees maps
 * names to subnodes, and jobs maps names to jobs.
 * 
 * @returns the root node
 */
function jobsToTree(jobs) {
  const tree = [{}, {}]
  for (const job of jobs) {
    const parts = job.job_id.split('/')
    const name = parts.splice(parts.length - 1, 1)[0]

    var subtree = tree
    for (const part of parts)
      subtree = subtree[0][part] = subtree[0][part] || [{}, {}]

    subtree[1][name] = job
  }

  return tree
}

/**
 * Flattens a tree into items for rendering.
 * 
 * Generates [path, subpath, name, job] items, where job is null
 * for directory items.
 * 
 * @param tree - the tree node to flatten
 */
function* flattenTree(parts, tree, collapse, path = []) {
  const [subtrees, items] = tree

  for (const [name, item] of sortBy(Object.entries(items)))
    yield [parts.concat(path, [name]), path, name, item]

  for (const [name, subtree] of sortBy(Object.entries(subtrees))) {
    const dirPath = parts.concat(path, [name])
    yield [dirPath, path, name, null]
    if (collapse[dirPath])
      yield* flattenTree(path, subtree, collapse, path.concat([name]))
  }
}

export default {
  props: [
    'dir',
    'query',
  ],

  data() {
    return {
      allJobs: [],
      collapse: {},
    }
  },

  components: {
    Job,
    Program,
  },

  created() {
    const v = this
    const url = '/api/v1/jobs'
    fetch(url)
      .then((response) => response.json())
      .then((response) => response.forEach((j) => v.allJobs.push(j)))
  },

  computed: {
    /** Jobs after applying the filter.  */
    visibleJobs() {
      const query = makePredicate(this.query)
      const pred = job => !job.ad_hoc && query(job)
      return filter(this.allJobs, pred)
    },

    /** Filtered jobs, as a tree.  */
    jobsTree() {
      return jobsToTree(this.visibleJobs)
    },

    /** Filtered jobs subtree for current dir.  */
    jobsDir() {
      var tree = this.jobsTree
      if (this.dir)
        for (const part of this.dir.split('/'))
          tree = tree[0][part] || [{}, {}]
      return tree
    },

    /** Filtered jobs subtree flattened to display rows, including dirs.  */
    jobRows() {
      const parts = this.dir ? this.dir.split('/') : []
      return Array.from(flattenTree(parts, this.jobsDir, this.collapse))
    },

},

  methods: {
    markdown(src) { return src.trim() === '' ? '' : markdown.toHTML(src) },
    join,

    toggleCollapse(path) {
      this.$set(this.collapse, path, !this.collapse[path])
    }
  },
}
</script>

<style lang="scss">
@import '../styles/vars.scss';

.dirnav {
  color: $apsis-dir-color;
}

.joblist {
  th {
    text-align: left;
  }
  td {
    vertical-align: top;
    height: 40px;
  }

  .job-title {
    .name {
      font-weight: 500;
    }
    .params {
      padding-left: 0.2rem;
      span {
        padding: 0 0.2rem;
      }
    }
  }

  .description {
    font-size: 85%;
    color: #777;

    p {
      margin: 0;
    }
  }

  .schedule {
    font-size: 85%;
    padding-top: 4px;
    ul {
      margin: 0;
    }

    .disabled {
      color: #aaa;
    }
  }

}
</style>
