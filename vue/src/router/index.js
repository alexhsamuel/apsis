import Vue from 'vue'
import Router from 'vue-router'

import JobView      from '@/views/JobView'
import JobsList     from '@/components/JobsList'
import Overview     from '@/views/Overview'
import RunView      from '@/views/RunView'
import RunsList     from '@/components/RunsList'

Vue.use(Router)

export default new Router({
  mode: 'history',
  routes: [
    {
      path: '/',
      name: 'Overvue',
      component: Overview,
    },
    {
      path: '/jobs/:job_id',
      props: true,
      name: 'job',
      component: JobView,
    },
    {
      path: '/jobs',
      name: 'jobs-list',
      component: JobsList,
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
      component: RunsList,
    },
  ]
})
