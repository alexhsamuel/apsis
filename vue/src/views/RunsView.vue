<template lang="pug">
div
  div.controls
    .control
      label.field-label Job &amp; Args
      span.uk-inline
        span.uk-form-icon(
          uk-icon="icon: search"
          style="pointer-events: auto; color: black;"
        )
        div(uk-drop="mode: hover")
          .uk-card.uk-card-body.uk-card-default 
            p Filter by JOB-ID or ARG=VALUE
            p
              span(uk-icon="icon: forward")
              |
              | Enter to filter

        input.uk-input(
          v-model="jobFilterInput"
          v-on:change="jobFilter = jobFilterInput"
          v-on:keyup.esc="jobFilterInput = jobFilter = ''"
        )

    .control
      label.field-label States
      button.uk-button.uk-button-default(type="button" style="width: 11em")
        span(v-if="stateFilter.length == 0") All
        State(v-else v-for="state in stateFilter" :key="state" :state="state")
      div.state-filter-select(uk-dropdown="pos: bottom-left")
        ul.uk-nav.uk-dropdown-nav
          li(v-for="[label, states] in stateOptions")
            a(href="#" v-on:click="stateFilter = states") 
              span(style="float: right")
                State(v-for="state in states" :key="state" :state="state")
              span.label {{ label }} 

    .control
      label.field-label Since
      span.uk-inline(:class="{error: sinceError}")
        span.uk-form-icon.uk-form-icon-flip(
          uk-icon="icon: close"
        )
        input.uk-input(
          v-model="sinceInput"
          v-on:change="since = parseTime(sinceInput, false)"
          v-on:keyup.esc="sinceInput = ''; since = parseTime(since, false)"
        )

    .control
      label.field-label Until
      input.uk-input(
        v-model="untilInput"
        v-on:change="until = parseTime(untilInput, true)"
        v-on:keyup.esc="untilInput = ''; until = parseTime(until, true)"
      )

  RunsList(:job-filter="jobFilter" :state-filter="stateFilter")
</template>

<script>
import RunsList from '@/components/RunsList'
import State from '@/components/State'
import store from '@/store'
import { parseTime } from '@/time'

export default {
  name: 'RunsView',
  components: {
    RunsList,
    State,
  },

  data() {
    return {
      jobFilter: '',
      jobFilterInput: '',
      since: '',
      sinceInput: '',
      stateFilter: [],
      until: '',
      untilInput: '',
    }
  },

  computed: {
    stateOptions() {
      return [
        ['All', []],
        ['Scheduled', ['scheduled']],
        ['Running', ['running']],
        ['Successful', ['success']],
        ['Unsuccessful', ['failure', 'error']],
        ['Started', ['running', 'success', 'failure', 'error']],
      ]
    },

    sinceError() { return this.sinceInput !== '' && this.since === null },
    untilError() { return this.untilInput !== '' && this.until === null },
  },

  methods: {
    parseTime(str, end) {
      return parseTime(str, end, store.state.timeZone)
    }
  },
}
</script>

<style lang="scss" scoped>
.control {
  display: inline-block;
  margin: 1em;

  &:first-child {
    margin-left: 0;
  }

  .field-label {
    margin-right: 1rem;
  }

  input {
    width: auto;
  }
}

.state-filter-select .label {
  text-transform: uppercase;
  margin-right: 3em;
}

:not(.error) .uk-icon {
  visibility: hidden;
}

.error {
  input {
    color: red;
  }
  .uk-icon {
    visibility: visible;
    color: red;
  }
}
</style>
