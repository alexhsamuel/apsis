<template>
  <nav class="navbar">
    <div class="container">
      <ul class="navbar-list">
        <li class="navbar-item">
          <svg width="3em" height="5em" version="1.1" xmlns="http://www.w3.org/2000/svg">
            <circle cx="1.5em" cy="2.05em" r="20%" stroke="black" fill="transparent" stroke-width="3.1"/>
            <circle cx="1.5em" cy="1.60em" r="4%" fill="#40c060"/>
          </svg>
        </li>
        <li class="navbar-item">
          <span class="navbar-title">APSİS</span>
        </li>
        <li class="navbar-item">
          <router-link to="/jobs" class="navbar-link">Jobs</router-link>
        </li>
        <li class="navbar-item">
          <router-link to="/runs" class="navbar-link">Runs</router-link>
        </li>
        <li class="navbar-clock"><clock></clock></li>
      </ul>
    </div>
  </nav>
</template>

<script>
import Clock from './clock.vue'
export default {
  name: 'navbar',
  components: {
    Clock,
  }
}
</script>

<style>
.navbar + .docs-section {
  border-top-width: 0;
}
.navbar,
.navbar-spacer {
  display: block;
  width: 100%;
  height: 6.5rem;
  background: #fff;
  z-index: 99;
  border-bottom: 1px solid #eee;
}
.navbar-spacer {
  display: none;
}
.navbar > .container {
  width: 100%;
}
.navbar-list {
  list-style: none;
  margin-bottom: 0;
}
.navbar-item {
  position: relative;
  float: left;
  margin-bottom: 0;
}
.navbar-title {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: .2rem;
  margin-right: 35px;
  text-decoration: none;
  line-height: 6.5rem;
  color: #222;
}
.navbar-link {
  text-transform: uppercase;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .2rem;
  margin-right: 35px;
  text-decoration: none;
  line-height: 6.5rem;
  color: #222;
}
.navbar-link.active {
  color: #33C3F0;
}
.navbar-clock {
  position: relative;
  float: right;
  margin-bottom: 0;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .12rem;
  line-height: 6.5rem;
}

.title {
  font-size: 150%;
  font-weight: 700;
}

</style>

