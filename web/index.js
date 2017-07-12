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
      <tr v-for="job in jobs">
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

const results_template = `
<div>
 <br>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Outcome</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="result in results">
        <td>{{ result.inst_id }}</td>
        <td>{{ result.outcome }}</td>
      </tr>
    </tbody>
  </table>
</div>
`

const Insts = { template: '<div>Insts</div>' }

const Results = { 
  template: results_template,

  data() { 
    return { 
      websocket: null, 
      results: [],
    } 
  },

  created() {
    const url = "ws://localhost:5000/api/v1/results-live"  // FIXME!
    const v = this

    websocket = new WebSocket(url)
    websocket.onmessage = (msg) => {
      msg = JSON.parse(msg.data)
      msg.results.forEach((e) => { v.results.push(e) })
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

// Each route should map to a component. The "component" can either be an
// actual component constructor created via `Vue.extend()`, or just a component
// options object.
const routes = [
  { path: '/jobs', component: Jobs },
  { path: '/instances', component: Insts },
  { path: '/results', component: Results },
]

const router = new VueRouter({
  mode: 'history',
  routes: routes,
})

const app = new Vue({ router }).$mount('#app')

}
