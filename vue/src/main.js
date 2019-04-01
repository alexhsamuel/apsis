import './styles/index.scss'

import App from './App'
import Icons from 'uikit/dist/js/uikit-icons'
import router from './router'
import store from './store'
import UIkit from 'uikit'
import Vue from 'vue'
import VueVirtualScroller from 'vue-virtual-scroller'

Vue.use(VueVirtualScroller)

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

