<template lang="pug">
div
  table.widetable.joblist
    colgroup
      col(style="max-width: 300px;")
      col(style="max-width: 300px;")
      col(style="")

    thead
      tr
        th
          | Job
          span(style="margin-left: 8px")
            a.expand-button
              TriangleIcon(
                direction="right"
                v-on:click="expandAll(false)"
              )
            a.expand-button
              TriangleIcon(
                direction="down"
                v-on:click="expandAll(true)"
              )
        th Parameters
        th Description
        // th Schedule

    tbody
      tr(v-if="loading")
        td(class="loading") Loading jobs...

      tr(
        v-for="[path, subpath, name, job] in jobRows"
        :key="subpath.concat([name]).join('/')"
        :class="[job ? 'job' : 'dir']"
      ).grid
        td
          span(style="white-space: nowrap")
            //- indent
            span(:style="{ display: 'inline-block', width: (36 * subpath.length) + 'px' }")

            //- a job
            span(v-if="job")
              span(style="display: inline-block; position: relative; left: -2px; top: -3px; width: 22px;")
                svg(viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
                  path(d="M 100 600 L 1700 600 L 1700 1700 L 50 1700 L 100 600" stroke="#666" stroke-width="100" fill="transparent")
                  path(d="M 100 600 L 250 1000 L 1550 1000 L 1700 600" stroke="#888" stroke-width="80" fill="transparent")
                  path(d="M 500 600 a 200 200 0 0 1 800 0" stroke="#888" stroke-width="150" fill="transparent")

              Job.name(:job-id="job.job_id" :name="name")

              div(style="display: inline-block; margin-left: 16px;")
                JobLabel(v-for="label in job.metadata.labels" :key="label" :label="label")

            //- a dir entry
            span.name(v-else)
              span(v-on:click="toggleExpand(path)")
                span.indent(style="display: inline-block; position: relative; left: -2px; top: -2px; width: 22px;")
                  svg(viewBox="0 0 1800 1800", xmlns="http://www.w3.org/2000/svg" width="18px")
                    path(d="M 100 300 L 700 300 L 800 500 L 1600 500 L 1600 1600 L 100 1600 L 100 300" stroke="#666" stroke-width="100" fill="#f2f6f4")
                a.dir(v-on:click="$emit('dir', path.join('/'))") {{ name }} 
                TriangleIcon.indent.folder-icon(
                  v-if="isExpanded(path)"
                  direction="down"
                  style="position: relative; left: -3px; top: 0px;"
                )
                TriangleIcon.indent.folder-icon(
                  v-else
                  direction="right"
                  style="position: relative; left: -5px; top: -1px;"
                )

        td.params
          span.params(v-if="job && job.params.length > 0")
            | {{ join(job.params, ', ') }}

        td.description
          div(v-if="job" v-html="markdown(exerptDescription(job.metadata.description || ''))")

</template>

<script>
import Job from './Job'
import * as jobsFilter from '@/jobsFilter.js'
import JobLabel from './JobLabel'
import { filter, join, sortBy } from 'lodash'
import Program from './Program'
import showdown from 'showdown'
import TriangleIcon from '@/components/icons/TriangleIcon'

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
 * @param basePath - path corresponding to `tree`, as array of parts
 * @param tree - the tree node to flatten
 * @param expanded - lookup of expanded tree paths
 */
function* flattenTree(basePath, tree, expanded, path = []) {
  const [subtrees, items] = tree

  for (const [name, subtree] of sortBy(Object.entries(subtrees))) {
    const dirPath = basePath.concat(path, [name])
    yield [dirPath, path, name, null]
    if (expanded[dirPath])
      yield* flattenTree(basePath, subtree, expanded, path.concat([name]))
  }

  for (const [name, item] of sortBy(Object.entries(items)))
    yield [basePath.concat(path, [name]), path, name, item]
}

export default {
  props: [
    'dir',
    'query',
  ],

  data() {
    return {
      loading: true,
      allJobs: [],
      expand: {},
    }
  },

  components: {
    Job,
    JobLabel,
    Program,
    TriangleIcon,
  },

  created() {
    const v = this
    const url = '/api/v1/jobs'
    this.loading = true
    fetch(url)
      .then((response) => response.json())
      .then((response) => response.forEach((j) => v.allJobs.push(j)))
      .then(() => { this.expandAll(false); this.loading = false })
  },

  computed: {
    /** Jobs after applying the filter.  */
    visibleJobs() {
      const pred = jobsFilter.makePredicate(this.query)
      return filter(filter(this.allJobs, job => !job.ad_hoc), pred)
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
      return Array.from(flattenTree(parts, this.jobsDir, this.expand))
    },

  },

  methods: {
    // Returns a shortened form of the description Markdown `src`.
    exerptDescription(src) {
      var paragraph = src.split('\n\n')[0]
      if (paragraph.length > 256)
        paragraph = paragraph.substring(0, 256) + '…'
      return paragraph
    },

    // Converts Markdown `src` to HTML.
    markdown(src) { return src.trim() === '' ? '' : (new showdown.Converter()).makeHtml(src) },

    join,

    toggleExpand(path) {
      this.$set(this.expand, path, !this.expand[path])
    },

    isExpanded(path) {
      return this.expand[path]
    },

    expandAll(expanded) {
      let expand = {}
      if (expanded)
        for (const job of this.allJobs) {
          const path = job.job_id.split('/')
          path.pop()
          while (path.length > 0) {
            expand[path] = true
            path.pop()
          }
        }
      this.expand = expand
    },
  },
}
</script>

<style lang="scss">
@import '../styles/vars.scss';

.dirnav {
  color: $apsis-dir-color;
}

.joblist {
  span.indent {
    width: 36px;
  }

  th {
    text-align: left;
  }

  .loading {
    color: $apsis-status-color;
  }

  a.expand-button {
    display: inline-block;
    width: 21px;
    padding: 0 2px;
    color: black;

    border-radius: 14px;
    color: $global-color;
    &:hover {
      background: #ddd;
    }
  }

  a.dir {
    color: inherit;
    :hover {
      color: inherit;
    }
  }

  .dir > td {
    height: 30px;
  }

  .job > td {
    height: 30px;
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
