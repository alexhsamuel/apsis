<template lang="pug">
  .combo(
    @keyup.enter.prevent="setShow()"
    @keyup.space.prevent="setShow()"
    @keyup.escape.prevent="setShow(false)"
  )
    .value(
      tabindex=0
      @mousedown.stop="setShow()"
    )
      span(v-if="allChecked") All States
      span(v-else-if="noneChecked") No States
      span(v-else) States:&nbsp;
      State(v-for="state in value" :key="'value-' + state" :state="state" :name="false")

      span(style="flex-grow: 99999;")
      TriangleIcon(
        style="width: 1em;"
        direction="down"
      )

    //- Full-window underlay to capture clicks outside the droplist.
    #under(
      v-show="show"
      @click="setShow(false)"
    )

    #drop
      #items(v-show="show" tabindex=0)
        div
          label(for="all-states") All States 
          input#all-states(
            type="checkbox"
            :checked="allChecked"
            @change="onAllStates"
            ref="all"
          )

        div.separator

        div(v-for="state in STATES")
          label(:for="state")
            State(:key="state" :state="state" :name="true")
          input(type="checkbox" :id="state" :value="state" v-model="checked")

</template>

<script>
import { STATES, sortStates } from '@/runs'
import State from '@/components/State'
import TriangleIcon from '@/components/icons/TriangleIcon'

/**
 * Selected states indicator with droplist to select individual states.
 * 
 * `value` is an array of state names; null means all states.
 */
export default {
  name: 'StatesSelect',
  props: {
    value: {type: Array, default: null},
  },

  components: {
    State,
    TriangleIcon,
  },

  data() {
    return {
      STATES,
      // Array of checked states.
      checked: this.value === null ? STATES : this.value.slice(),
      // Whether the droplist is displayed.
      show: false,
    }
  },

  computed: {
    noneChecked() {
      return this.checked.length === 0
    },

    allChecked() {
      return this.checked.length === this.STATES.length
    },
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

    onAllStates(ev) {
      this.$set(this, 'checked', ev.target.checked ? this.STATES : [])
    },
  },

  watch: {
    checked(checked) {
      // Send state to the parent.
      this.$emit('input', this.allChecked ? null : sortStates(checked))

      // Vue doesn't seem to have a way to set indeterminate on the all states checkbox, so set it here.
      this.$refs.all.indeterminate = !(this.noneChecked || this.allChecked)
    },
  },

  mounted() {
    // Possibly set indeterminate on the all states checkbox.
    this.$refs.all.indeterminate = !(this.noneChecked || this.allChecked)
  },
}
</script>

<style lang="scss" scoped>
@import 'src/styles/vars.scss';

.combo {
  display: flex;
  flex-direction: row;
  align-items: center;
  border: 1px solid $global-frame-color;
  padding: 0 8px 0 12px;
}

.value {
  box-sizing: border-box;
  width: 16em;
  background: white;
  text-transform: uppercase;

  display: inline-flex;
  flex-direction: row;
  justify-content: left;
  align-items: center;
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
  height: 0;
}

#items {
  position: relative;
  left: -13px;
  top: 1.2em;
  box-sizing: border-box;
  width: calc(100% + 2em);
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
