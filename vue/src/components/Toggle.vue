<template lang="pug">
  label.control
    input(
      type="checkbox"
      :checked="value"
      @click="$emit('input', $event.target.checked)"
    )
    span.slider
</template>

<script>
export default {
  props: ['value'],
}
</script>

<style lang="scss" scoped>
@import '@/styles/index.scss';

.control {
  position: relative;
  display: inline-block;
  width: 3em;
  height: 1.5em;
}

.control input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0.2ch;
  left: 0;
  right: 0;
  bottom: -0.2ch;
  background-color: $global-button-color;
  border-radius: 0.75em;
}

.slider:hover {
  background: $control-hover-color;
}

.slider:before {
  position: absolute;
  content: "";
  height: 1em;
  width: 1em;
  left: 0.25em;
  bottom: 0.25em;
  border-radius: 50%;
  background-color: white;
  transition: .05s;
}

input:checked + .slider:before {
  transform: translateX(1.5em);
}
</style>
