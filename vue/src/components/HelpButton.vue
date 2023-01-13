<template lang="pug">
  .base
    div(
      @click="show = !show"
    )
      HelpIcon(
        :color="show ? '#b37' : '#d8d8d8'"
      ).icon
    .popup(v-if="show")
      slot
    //- Full-window underlay to capture clicks outside the droplist.
    #under(
      v-if="show"
      @click="show = false"
    )

</template>

<script>
import HelpIcon from '@/components/icons/HelpIcon'

export default {
  components: {
    HelpIcon,
  },

  data() {
    return {
      show: false,
    }
  }
}
</script>

<style lang="scss" scoped>
@import 'src/styles/vars.scss';

.base {
  margin-left: 0.25em;
  display: inline-block;
  vertical-align: middle;
}

.icon {
  width: 1em;
  height: 1em;
}

.popup {
  position: absolute;
  z-index: 1;
  max-width: 34em;
  text-align: left;
  white-space: normal;

  background-color: #f4f4f4;
  border: 3px solid #b37;
  border-radius: 8px;
  padding: 12px 20px;

  font-size: 90%;
  line-height: normal;
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
</style>
