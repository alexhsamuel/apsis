class Errors {
  // FIXME: I'm using  a list here because I can't figure out how to get
  // watch behavior working with an object keyed by errorId.
  errors = []
  nextErrorId = 0

  add(message) {
    const errorId = this.nextErrorId++
    this.errors.push({errorId, message, time: new Date()})
    return errorId
  }

  clear(errorId) {
    for (let i = 0; i < this.errors.length; i++)
      if (this.errors[i].errorId === errorId) {
        this.errors.splice(i, 1)
        break
      }
  }
}

class Store {
  state = {
    errors: new Errors(),
    logLines: [],
    runs: {},
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
