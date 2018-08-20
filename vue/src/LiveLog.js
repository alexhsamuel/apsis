export default class LiveLog {
  constructor() {
    this.websocket = null

    this.url = new URL(location)
    this.url.protocol = 'ws'
    this.url.pathname = '/api/log'
  }

  open(callback) {
    this.websocket = new WebSocket(this.url)
    this.websocket.onmessage = (msg) => {
      callback(msg.data)
    }
    this.websocket.onclose = () => {
      console.log('log web socket closed')
      this.websocket = null
    }
  }

  close() {
    if (this.websocket !== null)
      this.websocket.close()
  }
}
