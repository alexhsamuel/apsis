<template lang="pug">
  .combo(
    v-on:keyup.enter.prevent="toggle()"
    v-on:keyup.space.prevent="toggle()"
    v-on:keydown.up.prevent="move(-1)"
    v-on:keydown.down.prevent="move(1)"
    v-on:keyup.escape.prevent="show = false"
  )
    .value(
        tabindex=0
        @mousedown.stop="show = !show"
        @blur="show = false"
    )
      div#selected
      div(style="flex-grow: 10000;")
      TriangleIcon(direction="down")

    div.drop
      .items(
        v-show="show"
        v-on:mousedown="onItemClick"
      )
       slot
</template>

<script>
import TriangleIcon from '@/components/icons/TriangleIcon'

export default {
  props: {
    value: {
      type: Number,
      default: 0,
    },
  },

  components: {
    TriangleIcon,
  },

  data() {
    return {
      idx: this.value,
      show: false,
    }
  },

  methods: {
    getItemsElement() {
      return this.$el.childNodes[1].childNodes[0]
    },

    toggle() {
      if (this.show)
        this.setValue()
      else
        this.idx = this.value
      this.show = !this.show
    },

    /**
     * Sets the value in the value box to the selected `this.idx`.
     */
    setValue() {
      const valueBox  = this.$el.querySelector('#selected')
      const item = this.getItemsElement().childNodes[this.idx]

      // Remove existing contents.
      while (valueBox.hasChildNodes())
        valueBox.removeChild(valueBox.firstChild)

      // Replace with a clone of the selected item.
      valueBox.appendChild(item.cloneNode(true))

      // Send an input event, so that v-model works with this component.
      this.$emit('input', this.idx)
    },

    /**
     * Sets the highlighted selection to `idx`.
     */
    setSelection(idx) {
      const items = this.getItemsElement()
  
      // Unhighlight the old selected item.
      let item = items.childNodes[this.idx]
      item.classList.remove('selected')

      this.idx = idx
      item = this.getItemsElement().childNodes[this.idx]
      item.classList.add('selected')
    },

    /**
     * Moves the highlighted selection by `delta`.
     */
    move(delta) {
      if (this.show) {
        const len = this.getItemsElement().childNodes.length
        this.setSelection((this.idx + delta + len) % len)
      }
      else
        this.show = true
    },

    onItemClick(ev) {
      const items = this.getItemsElement()
      // Scan through items, looking for a click hit.
      for (let i = 0; i < items.childNodes.length; ++i) {
        const item = items.childNodes[i]
        if (item.contains(ev.target)) {
          // Hit.  Set the selection as well as the top-level value.
          this.setSelection(i)
          this.setValue()
        }
      }
      this.show = false
    },

  },
  
  mounted() {
    this.setSelection(this.idx)
    this.setValue()
  },
}
</script>

<style lang="scss" scoped>
@import 'src/styles/vars.scss';

.combo {
  border: 1px solid $global-frame-color;
  background: $global-background;
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 0 8px 0 12px;
}

.value {
  box-sizing: border-box;
  width: 100%;
  background: white;

  display: inline-flex;
  flex-direction: row;
  justify-content: center;

  &:focus {
    border-color: $global-focus-color;
  }
}

.drop {
  z-index: 1;
  position: absolute;
  width: max-content;
  height: 0;
}

.items {
  position: relative;
  left: -13px;
  top: 1.2em;
  background: white;
  border: 1px solid $global-frame-color;
  box-shadow: 4px 4px 4px #eee;
  padding-top: 4px;
  padding-bottom: 4px;

  div {
    padding: 3px 12px;
  }

  :hover {
    background: $global-hover-background;
  }

  .selected {
    background: $global-select-background;
  }
}
</style>
