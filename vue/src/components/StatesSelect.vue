<template lang="pug">
span.states-select
  button.uk-button.uk-button-default(type="button")
    | States: 
    span(v-if="value.length == 0") All
    span(v-else)
      State(v-for="state in value" :key="state" :state="state")

  div(uk-dropdown="pos: bottom-left")
    ul.uk-nav.uk-dropdown-nav
      li(v-for="[label, states] in options")
        a(href="#" v-on:click="$emit('input', states)") 
          span(style="float: right")
            State(v-for="state in states" :key="state" :state="state")
          span.label {{ label }} 

</template>

<script>
import State from './State'

export default {
  name: 'StatesSelect',
  props: ['value'],

  components: {
    State,
  },

  data() {
    return {
      options: [
        ['All', []],
        ['Scheduled', ['scheduled']],
        ['Waiting', ['waiting']],
        ['Held', ['scheduled', 'waiting']],
        ['Running', ['starting', 'running']],
        ['Successful', ['success']],
        ['Unsuccessful', ['failure', 'error']],
        ['Started', ['running', 'success', 'failure', 'error']],
      ],
    }
  }
}
</script>

<style lang="scss">
.states-select {
  button {
    width: 100%;
    padding: 0 8px 0 12px;
  }
  li .label {
    text-transform: uppercase;
    margin-right: 3em;
  }
}
</style>
