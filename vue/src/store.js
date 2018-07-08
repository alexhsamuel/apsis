class Store {
  state = {
    time: new Date(),
    timeZone: 'UTC',
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
