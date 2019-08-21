<template lang="pug">
div
  h3
    | {{ dir ? 'Jobs in ' + dir : 'All Jobs' }}
    | ({{ numVisibleJobs }} jobs)

  table.widetable.joblist
    thead
      tr
        th Job
        th Description
        th Schedule

    tbody
      tr(
        v-for="[dir, name, job] in jobRows"
        :key="dir.concat([name]).join('/')"
      )
        td.job-title
          //- indent
          span(:style="{ display: 'inline-block', width: (16 * dir.length) + 'px' }") &nbsp;

          //- a job
          span(v-if="job")
            Job.name(:job-id="job.job_id" :name="name")
            span.params(v-if="job && job.params.length > 0")
              | ({{ join(job.params, ', ') }})

          //- a dir entry
          span.name(v-else)
            a(v-on:click="$emit('dir', dir.concat([name]).join('/'))") {{ name }} /

        td.description
          div(v-if="job" v-html="markdown(job.metadata.description || '')")

        td.schedule
          ul(v-if="job")
            li(v-for="(schedule, idx) in job.schedules" :key="idx")
              span(:class="{ disabled: !schedule.enabled }") {{ schedule.str }}

</template>

<script>
import Job from './Job'
import { every, filter, join, map, sum, trim } from 'lodash'
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
 * Generates [path, name, job] items, where job is null
 * for directory items.
 * 
 * @param tree - the tree node to flatten
 */
function* flattenTree(tree, path = []) {
  const [subtrees, items] = tree

  for (const [name, item] of Object.entries(items))
    yield [path, name, item]

  for (const [name, subtree] of Object.entries(subtrees)) {
    yield [path, name, null]
    yield* flattenTree(subtree, path.concat([name]))
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
          tree = tree[0][part]
      return tree
    },

    /** Filtered jobs subtree flattened to display rows, including dirs.  */
    jobRows() {
      return Array.from(flattenTree(this.jobsDir))
    },

    numVisibleJobs() {
      function count(tree) {
        return Object.keys(tree[1]).length
          + sum(map(count, Object.values(tree[0])))
      }
      return count(this.jobsDir)
    },
  },

  methods: {
    markdown(src) { return src.trim() === '' ? '' : markdown.toHTML(src) },
    join,
  },
}
</script>

<style lang="scss">
.joblist {
  th {
    text-align: left;
  }
  td {
    vertical-align: top;
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
    // margin-bottom: 8px;
    font-size: 85%;
    color: #777;

    p {
      margin: 0;
    }
  }

  .schedule {
    max-width: 33%;
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
