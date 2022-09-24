import Vue from 'vue'
import State from '@/components/State'

describe('State.vue', () => {
  it('should render correct contents', () => {
    const Constructor = Vue.extend(State)
    const vm = new Constructor({ propsData: { state: 'success', name: true } }).$mount()
    expect(vm.$el.querySelector('.name').textContent).toEqual('success')
    expect(vm.$el.querySelector('.tooltiptext').textContent).toEqual('SUCCESS')
  })
})
