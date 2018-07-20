import Vue from 'vue'
import Router from 'vue-router'

import JobView      from '@/components/JobView'
import JobsList     from '@/components/JobsList'
import HelloWorld   from '@/components/HelloWorld'
import RunView      from '@/components/RunView'
import RunsList     from '@/components/RunsList'

Vue.use(Router)

export default new Router({
  mode: 'history',
  routes: [
    {
      path: '/',
      name: 'HelloWorld',
      component: HelloWorld
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
