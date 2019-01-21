<template lang="pug">
nav.uk-navbar-container.uk-navbar
  .uk-navbar-left
    .uk-navbar-item
      svg(
        width="3em" 
        height="4em" 
        version="1.1" 
        xmlns="http://www.w3.org/2000/svg"
      )
        circle(cx="1.5em" cy="2.05em" r="20%" stroke="black" fill="transparent" stroke-width="3.1")
        circle(cx="1.5em" cy="1.68em" r="4%" fill="#40c060")

    .uk-navbar-item.title
      router-link(to="/") APSİS

    ul.uk-navbar-nav
      li: router-link(to="/jobs") Jobs
      li: router-link(to="/runs?q=since:1d") Runs
      li: router-link(to="/control") Control

  .uk-navbar-right
    .uk-navbar-item 
      clock
      TimeZoneSelect

</template>

<script>
import Clock from './Clock.vue'
import TimeZoneSelect from './TimeZoneSelect'

export default {
  name: 'navbar',
  components: {
    Clock,
    TimeZoneSelect,
  }
}
</script>

<style lang="scss">
.title {
  font-family: Helvetica;
  font-weight: 600;
  padding-left: 0;
  letter-spacing: .1rem;
  margin-right: 12px;
  color: #222;
}

.clock {
  letter-spacing: .04rem;
}

.title {
  font-size: 150%;
  font-weight: 700;
  padding-top: 4px;
  a {
    color: #222;
  }
  a:hover {
    text-decoration: none;
  }
}

</style>

