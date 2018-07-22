class Store {
  state = {
    // The current time.
    time: new Date(),

    // The time zone for displaying times by default.
    timeZone: 'UTC',

    runList: {
      // Collapse state for run groups.
      groupCollapse: {},

    },
  }

  setTime(time) {
    this.state.time = time || new Date()
  }

  setTimeZone(timeZone) {
    this.state.timeZone = timeZone
  }

  _tick() {
    this.setTime()
    // Update every second, on the second.
    window.setTimeout(() => this._tick(), 1000 - this.state.time % 1000)
  }

  constructor() {
    this._tick()
  }
}

const store = new Store()
export default store
