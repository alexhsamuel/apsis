import Vue from 'vue'
import Router from 'vue-router'

import AgentsView   from '@/views/AgentsView'
import JobView      from '@/views/JobView'
import JobsView     from '@/views/JobsView'
import RunView      from '@/views/RunView'
import RunsView     from '@/views/RunsView'

Vue.use(Router)

export default new Router({
  mode: 'history',
  routes: [
    {
      path: '/',
      redirect: '/jobs',
    },
    {
      path: '/agents',
      props: false,
      name: 'agents',
      component: AgentsView,
    },
    {
      path: '/jobs/:path*',
      props: true,
      name: 'jobs-list',
      component: JobsView,
    },
    {
      path: '/job/:job_id*',
      props: true,
      name: 'job',
      component: JobView,
    },
    {
      path: '/runs/:run_id',
      props: true,
      name: 'run',
      component: RunView,
    },
    {
      path: '/runs',
      name: 'runs-list',
      component: RunsView,
    },
  ]
})
