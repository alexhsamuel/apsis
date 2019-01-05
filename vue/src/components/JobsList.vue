<template lang="pug">
div
  .row.head
    | {{ jobs.length }} Jobs

  .row.job(
    v-for="job in jobs"
    :key="job.job_id"
    v-on:click="$router.push({ name: 'job', params: { job_id: job.job_id } })"
  )
    .job-title
      Job.name(:job-id="job.job_id")
      span.params(v-if="job.params.length > 0")
        | ({{ join(job.params, ', ') }})
    .schedule: ul
      li(v-for="(schedule, idx) in job.schedules" :key="idx")
        span(:class="{ disabled: !schedule.enabled }") {{ schedule.str }}
    .description(v-html="markdown(job.metadata.description || ' ')")
    .program
      tt {{ job.program.str }}
      //- host
      //- user

</template>

<script>
import Job from './Job'
import { filter, join, sortBy } from 'lodash'
import MarkdownIt from 'markdown-it'
import Program from './Program'

const markdownit = new MarkdownIt()

export default { 
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
      return sortBy(filter(this.allJobs, j => !j.ad_hoc), j => j.job_id)
    }
  },

  methods: {
    markdown(src) { return markdownit.renderInline(src) },
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
  float: left;
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
  float: left;
  clear: left;
  margin-bottom: 8px;
  font-size: 85%;
  color: #777;
}

.program {
  float: left;
  clear: left;
  padding-left: 12px;
}

.schedule {
  float: right;
  width: 33%;
  font-size: 85%;
  ul {
    margin: 0;
  }

  .disabled {
    color: #aaa;
  }
}
</style>
