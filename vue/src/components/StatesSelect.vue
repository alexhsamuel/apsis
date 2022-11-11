<template lang="pug">
  .combo(
    @keyup.enter.prevent="setShow()"
    @keyup.space.prevent="setShow()"
    @keyup.escape.prevent="setShow(false)"
  )
    .value(@mousedown.stop="setShow()" tabindex=0)
      span(v-if="value.length == 0") All States
      span(v-else) States:&nbsp;
      State(v-for="state in value" :key="'value-' + state" :state="state" :name="false")

    //- Full-window underlay to capture clicks outside the droplist.
    #under(
      v-show="show"
      @click="setShow(false)"
    )

    #drop
      #items(v-show="show" tabindex=0)
        div
          label(for="all-states") All States 
          input#all-states(type="checkbox" :checked="checked.length == 0" @change="checkAll")
        div.separator
        div(v-for="state in STATES")
          label(:for="state")
            State(:key="state" :state="state" :name="true")
          input(type="checkbox" :id="state" :value="state" v-model="checked")

</template>

<script>
import DropList from '@/components/DropList'
import { STATES, sortStates } from '@/runs'
import State from './State'

/**
 * Selected states indicator with droplist to select individual states.
 * 
 * `value` is an array of state names.  An empty array means all states.
 */
export default {
  name: 'StatesSelect',
  props: ['value'],

  components: {
    DropList,
    State,
  },

  data() {
    console.log(this.value)
    return {
      STATES,
      // Array of checked values.
      checked: this.value.splice(),
      // Whether the droplist is displayed.
      show: false,
    }
  },

  methods: {
    /**
     * Show or hide the droplist.  If undefined, toggle.
     */
    setShow(show) {
      if (typeof show === 'undefined')
        show = !this.show
      this.show = show
    },

    checkAll(ev) {
      this.$set(this, 'checked', [])
    },
  },

  watch: {
    checked(checked, old) {
      // Send state to the parent.
      this.$emit('input', sortStates(checked))
    },
  },
}
</script>

<style lang="scss" scoped>@import 'src/styles/vars.scss';
.value {
  box-sizing: border-box;
  width: 16em;
  background: white;
  border: 1px solid $global-frame-color;
  padding: 4px 12px 3px 12px;
  text-transform: uppercase;

  display: inline-flex;
  flex-direction: row;
  justify-content: left;
  align-items: start;
  gap: 1px;

  &:focus {
    border-color: $global-focus-color;
  }
}

#under {
  position: fixed;
  z-index: 2;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
}

#drop {
  z-index: 2;
  position: absolute;
  width: max-content;
  height: 0;
}

#items {
  position: relative;
  top: 4px;
  box-sizing: border-box;
  width: 16em;
  background: white;
  border: 1px solid $global-frame-color;
  box-shadow: 4px 4px 4px #eee;
  padding-top: 4px;
  padding-bottom: 4px;
  text-transform: uppercase;

  .separator {
    margin: 6px 0;
    border-top: 1px solid #eee;
    padding: 0;
    height: 0;
  }

  div {
    padding: 6px 12px;
  }

  input[type="checkbox"] {
    float: right;
    width: 16px;
    height: 16px;
  }
}
</style>
