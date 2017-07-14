function onload() {

const jobs_template = `
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
      <tr v-for="job in jobs" v-on:click="$router.push({ name: 'job', params: { job_id: job.job_id } })">
        <td>{{ job.job_id }}</td>
        <td>{{ job.program_str || "" }}</td>
        <td>{{ job.schedule_str || "" }}</td>
      </tr>
    </tbody>
  </table>
</div>
`

const Jobs = { 
  template: jobs_template,
  data() {
    return {
      jobs: [],
    }
  },

  created() {
    const v = this
    const url = "/api/v1/jobs"
    fetch(url)
      .then((response) => response.json())
      .then((response) => response.forEach((j) => v.jobs.push(j)))
  },
}

/*------------------------------------------------------------------------------
------------------------------------------------------------------------------*/

const job_template = `
<div>
  <br>
  <h4>{{job_id}}</h4>
  <dl v-if="job">
    <template v-for="(value, key) in job">
      <dt>{{key}}</dt>
      <dd>{{value}}</dd>
    </template>
  </dl>
</div>
`

const Job = {
  template: job_template,
  props: ['job_id'],
  data() {
    return {
      job: null,
    }
  },

  created() {
    const v = this
    const url = "/api/v1/jobs/" + this.job_id
    fetch(url)
      .then((response) => response.json())
      .then((response) => { v.job = response })
  },
}

/*------------------------------------------------------------------------------
------------------------------------------------------------------------------*/

const runs_template = `
<div>
 <br>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Job</th>
        <th>State</th>
        <th>Schedule</th>
        <th>Start</th>
        <th>Elapsed</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="run in sorted" :key="run.run_id">
        <td>{{ run.run_id }}</td>
        <td>{{ run.job_id }}</td>
        <td>{{ run.state }}</td>
        <td>{{ run.meta.schedule_time || "" }}</td>
        <td>{{ run.meta.start_time || "" }}</td>
        <td>{{ run.meta.elapsed === undefined ? "" : run.meta.elapsed.toPrecision(2) + " s" }}</td>
      </tr>
    </tbody>
  </table>
</div>
`

const Runs = { 
  template: runs_template,

  data() { 
    return { 
      websocket: null, 
      runs: {},
    } 
  },

  computed: {
    sorted() {
      return _.flow(_.values, _.sortBy(r => r.meta.schedule_time))(this.runs)
    },
  },

  created() {
    const url = "ws://localhost:5000/api/v1/runs-live"  // FIXME!
    const v = this

    websocket = new WebSocket(url)
    websocket.onmessage = (msg) => {
      msg = JSON.parse(msg.data)
      v.runs = Object.assign({}, v.runs, msg.runs)
    }
    websocket.onclose = () => {
      console.log("web socket closed: " + url)
      websocket = null
    }
  },

  destroyed() {
    if (websocket) {
      websocket.close()
    }
  }
}

const Insts = { template: '<div>Insts</div>' }

// Each route should map to a component. The "component" can either be an
// actual component constructor created via `Vue.extend()`, or just a component
// options object.
const routes = [
  { name: 'job', path: '/job/:job_id', component: Job, props: true },
  { path: '/jobs', component: Jobs },
  { path: '/instances', component: Insts },
  { path: '/runs', component: Runs },
]

const router = new VueRouter({
  mode: 'history',
  routes: routes,
})

const app = new Vue({ router }).$mount('#app')

}
