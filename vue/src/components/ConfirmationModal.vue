<template lang="pug">
.modal
  .content
    .message {{ message }}
    .buttons
      button(
        v-on:click="onOk"
      ) OK
      button(
        v-on:click="onCancel"
      ) Cancel
</template>

<script>
export default {
  props: [
    'cancel',
    'ok',
    'message',
  ],

  methods: {
    onOk() {
      if (this.ok)
        this.ok()
      this.close()
    },

    onCancel() {
      if (this.cancel)
        this.cancel()
      this.close()
    },

    close() {
      this.$destroy()
      this.$el.parentNode.removeChild(this.$el)
    },
  },
}
</script>

<style lang="scss" scoped>
@import 'src/styles/vars.scss';

.modal {
  position: fixed;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  opacity: 1;
  transform: scale(1.1);  // ??

  .content {
    position: absolute;
    top: 40%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: white;
    padding: 24px 32px;
    z-index: 1;

    .message {
      margin-bottom: 20px;
    }

    .buttons {
      button {
        margin-left: 8px;
        margin-right: 8px;
        color: white;
        background: $global-focus-color;
      }
      button:first-child {
        margin-left: 0;
      }
      button:last-child {
        margin-right: 0;
      }
    }
  }
}
</style>
