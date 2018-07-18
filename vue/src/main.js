import './styles/index.scss'

import Vue from 'vue'
import UIkit from 'uikit'
import Icons from 'uikit/dist/js/uikit-icons'
import App from './App'
import router from './router'
import store from './store'

UIkit.use(Icons)
window.UIkit = UIkit

Vue.config.productionTip = false

/* eslint-disable no-new */
new Vue({
  el: '#app',
  router,
  data: store,
  components: { App },
  template: '<App/>'
})

