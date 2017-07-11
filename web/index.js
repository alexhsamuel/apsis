function onload() {

const jobs_template = `
<div>
  <br>
  <table class="joblist">
    <thead>
      <tr>
        <th>Job ID</th>
        <th>Program</th>
        <th>Next Instance</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>test-job-2</td>
        <td><code>/bin/sleep 2</code></td>
        <td>2017-07-11T15:24:44Z</td>
      </tr>
      <tr>
        <td>test-job-5</td>
        <td><code>/bin/sleep 5</code></td>
        <td>2017-07-11T15:24:44Z</td>
      </tr>
      <tr>
        <td>test-job-8</td>
        <td><code>/bin/echo 'Hello, world!'</code></td>
        <td>2017-07-11T15:24:44Z</td>
      </tr>
    </tbody>
  </table>
</div>
`

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

const Jobs = { template: jobs_template }
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
