import Vue from 'vue'
import Router from 'vue-router'

import Job          from '@/components/Job'
import JobsList     from '@/components/JobsList'
import HelloWorld   from '@/components/HelloWorld'
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
      component: Job,
    },
    {
      path: '/jobs',
      name: 'jobs-list',
      component: JobsList,
    },
    {
      path: '/runs',
      name: 'runs-list',
      component: RunsList,
    },
  ]
})
