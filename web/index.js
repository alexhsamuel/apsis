function onload() {

const Foo = { template: '<div>foo</div>' }
const Bar = { template: '<div>bar</div>' }

// Each route should map to a component. The "component" can either be an
// actual component constructor created via `Vue.extend()`, or just a component
// options object.
const routes = [
  { path: '/foo', component: Foo },
  { path: '/bar', component: Bar }
]

const router = new VueRouter({
  mode: 'history',
  routes: routes,
})

const app = new Vue({ router }).$mount('#app')

}
