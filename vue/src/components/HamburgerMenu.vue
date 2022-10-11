<template lang="pug">
  .combo(
    v-on:keyup.escape.prevent="show = false"
  )
    div.burger(
      tabindex=0
      v-on:mousedown.stop="show = !show"
      v-on:onblur.self="onBlur"
    )
      HamburgerIcon
    div.drop
      .items(
        v-if="show"
        v-on:click="show = false"
      )
        slot
</template>

<script>
import HamburgerIcon from './icons/HamburgerIcon.vue'

export default {
  props: {
  },

  components: {
    HamburgerIcon,
  },

  data() {
    return {
      show: false,
    }
  },

  methods: {
    ev(ev) {
      console.log(ev)
    },

    onBlur(ev) {
      // If the user clicks on a button in the burger drop menu, the menu loses
      // focus before the button receives the click event, so we cannot close
      // the drop menu prematurely.  In that case, we'll close the drop menu
      // when it receives the bubbled-up click event later.
      const drop = this.$el.querySelector('.drop')
      if (!drop.contains(ev.explicitOriginalTarget))
        this.show = false
    }
  },
}
</script>

<style lang="scss" scoped>
@import 'src/styles/vars.scss';

.combo {
  display: inline-block;
  .burger {
    width: 40px;
    border: 1px solid $global-frame-color;
  }
}

.drop {
  z-index: 1;
  position: absolute;
  width: 0;
  height: 0;
}

.items {
  position: absolute;
  top: -32px;
  right: 8px;

  background: white;
  border: 1px solid $global-frame-color;
  box-shadow: 4px 4px 4px #eee;
  padding: 8px;

  display: inline-flex;
  align-items: center;
  align-content: flex-end;

  div {
    padding: 6px 12px;
  }

  :hover {
    background: $global-hover-background;
  }

  .selected {
    background: $global-select-background;
  }
}
</style>
