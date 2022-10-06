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
      v-on:mousedown.stop="show = !show"
      v-on:blur="show = false"
    )
    div.drop
      .items(
        v-show="show"
        v-on:mousedown.stop="onItemClick"
      )
       slot
</template>

<script>
export default {
  props: {
    value: {
      type: Number,
      default: 0,
    },
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

    setValue() {
      const valueBox  = this.$el.querySelector('.value')
      const item = this.getItemsElement().childNodes[this.idx]

      // Remove existing contents.
      while (valueBox.hasChildNodes())
        valueBox.removeChild(valueBox.firstChild)

      // Replace with a clone of the selected item.
      valueBox.appendChild(item.cloneNode(true))
    },

    setSelection(idx) {
      const items = this.getItemsElement()
  
      // Unhighlight the old selected item.
      let item = items.childNodes[this.idx]
      item.classList.remove('selected')

      this.idx = idx
      item = this.getItemsElement().childNodes[this.idx]
      item.classList.add('selected')
    },

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
      for (let i = 0; i < items.childNodes.length; ++i)
        if (items.childNodes[i] === ev.target) {
          this.setSelection(i)
          this.setValue()
        }
      this.show = false
    },

    event(ev) {
      console.log(ev)
    }
  },
  
  mounted() {
    this.setSelection(0)  // FIXME
    this.setValue()
  },
}
</script>

<style lang="scss" scoped>
@import 'src/styles/vars.scss';

.value {
  width: 128px;
  height: 28px;
  background: white;
  border: 1px solid $global-frame-color;
  padding: 0px 12px;

  display: inline-flex;
  flex-direction: column;
  justify-content: center;

  &:focus {
    border-color: $global-focus-color;
  }
}

.drop {
  position: absolute;
  width: 0;
  height: 0;
}

.items {
  position: relative;
  top: 4px;
  background: white;
  width: 152px;
  border: 1px solid $global-frame-color;
  box-shadow: 4px 4px 4px #eee;

  div {
    padding: 4px 12px;
  }

  :hover {
    background: $global-hover-background;
  }

  .selected {
    background: $global-select-background;
  }
}
</style>
