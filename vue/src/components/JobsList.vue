<template>
  <div>
    <br>
    <table class="joblist">
      <thead>
        <tr>
          <th>Job ID</th>
          <th>Program</th>
          <th>Schedule</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="job in jobs" 
            v-bind:key="job.job_id"
            v-on:click="$router.push({ name: 'job', params: { job_id: job.job_id } })"
            >
          <td class="job-link">{{ job.job_id }}</td>
          <td>{{ job.program.str || "" }}</td>
          <td>
            <template 
                v-for="s in job.schedules"
              >
              {{ s.str }}
              <!-- eslint-disable-next-line -->
              <br>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default { 
  data() {
    return {
      jobs: [],
    }
  },

  created() {
    const v = this
    const url = '/api/v1/jobs'
    fetch(url)
      .then((response) => response.json())
      .then((response) => response.forEach((j) => v.jobs.push(j)))
  },
}
</script>

<style scoped>
table {
  width: 100%;
}

th, td {
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
  padding-left: 0.5rem;
}

tbody tr:hover {
  background: #f0fff8;
}

tbody td {
  min-width: 8rem;
  max-width: 48rem;
}
</style>

