<template lang="pug">
div
  .row.head
    | {{ jobs.length }} Jobs

  .row.job(
    v-for="job in jobs"
    :key="job.job_id"
  )
    .schedule: ul
      li(v-for="(schedule, idx) in job.schedules" :key="idx")
        span(:class="{ disabled: !schedule.enabled }") {{ schedule.str }}

    .job-title
      Job.name(:job-id="job.job_id")
      span.params(v-if="job.params.length > 0")
        | ({{ join(job.params, ', ') }})
    .description(v-html="markdown(job.metadata.description || '')")

</template>

<script>
import Job from './Job'
import { every, filter, join, map, sortBy, trim } from 'lodash'
import { markdown } from 'markdown'
import Program from './Program'

export function makePredicate(search) {
  const parts = filter(map(search.split(' '), trim))
  if (parts.length === 0)
    return job => true

  // Construct an array of predicates over runs, one for each term.
  const preds = map(parts, part => {
    return job => job.job_id.indexOf(part) >= 0
  })

  // The combined predicate function is true if all the predicates are.
  return job => every(map(preds, f => f(job)))
}


export default {
  props: ['search'],

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
    jobs() {
      const pred = job => !job.ad_hoc && this.searchPredicate(job)
      return sortBy(filter(this.allJobs, pred), j => j.job_id)
    },

    searchPredicate() {
      return makePredicate(this.search)
    }
  },

  methods: {
    markdown(src) { return src.trim() === '' ? '' : markdown.toHTML(src) },
    join,
  },
}
</script>

<style lang="scss" scoped>
.row {
  border: 1px solid #e1e8e4;
  border-top: none;
  border-radius: 3px;
  padding: 8px 24px 12px 24px;
  overflow: auto;
}

.head {
  background-color: #f6faf8;
  border-top: 1px solid #e1e8e4;
  padding: 12px 24px;
}

.job {
  &:hover {
    background-color: #fafafa;
  }
}

.job-title {
  .name {
    font-size: 120%;
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
  margin-bottom: 8px;
  font-size: 85%;
  color: #777;

  // Need /deep/ here because v-html doesn't produce scoping attributes.
  /deep/ p {
    margin: 0;
  }
}

.schedule {
  float: right;
  width: 33%;
  font-size: 85%;
  padding-top: 4px;
  ul {
    margin: 0;
  }

  .disabled {
    color: #aaa;
  }
}
</style>
