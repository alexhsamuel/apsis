import Vue from 'vue'
import Router from 'vue-router'
import JobsList from '@/components/JobsList'
import HelloWorld from '@/components/HelloWorld'

Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'HelloWorld',
      component: HelloWorld
    },
    {
      path: '/jobs',
      name: 'jobs-list',
      component: JobsList,
    },
  ]
})
