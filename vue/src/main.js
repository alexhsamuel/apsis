import './styles/index.scss'

import App from './App'
import router from './router'
import store from './store'
import Vue from 'vue'

Vue.config.productionTip = false

/* eslint-disable no-new */
new Vue({
  el: '#app',
  router,
  data: store,
  components: { App },
  template: '<App/>'
})

