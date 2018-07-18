<template>
  <nav class="uk-navbar-container" uk-navbar>
    <div class="uk-navbar-left">
      <div class="uk-navbar-item">
        <svg width="3em" height="4em" version="1.1" xmlns="http://www.w3.org/2000/svg">
          <circle cx="1.5em" cy="2.05em" r="20%" stroke="black" fill="transparent" stroke-width="3.1"/>
          <circle cx="1.5em" cy="1.68em" r="4%" fill="#40c060"/>
        </svg>
      </div>
      <div class="uk-navbar-item title">
        APSİS
      </div>
      <ul class="uk-navbar-nav">
        <li><router-link to="/jobs">Jobs</router-link></li>
        <li><router-link to="/runs">Runs</router-link></li>
      </ul>
    </div>

    <div class="uk-navbar-right">
      <div class="uk-navbar-item clock">
        <clock></clock>
      </div>
    </div>

  </nav>
</template>

<script>
import Clock from './Clock.vue'
export default {
  name: 'navbar',
  components: {
    Clock,
  }
}
</script>

<style>
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
}

</style>

