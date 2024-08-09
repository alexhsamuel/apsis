/*
 * WebSocket connection that receives JSON messages.
 */
export default class JsonSocket {
  constructor(url, onMessage, onConnect, onErr) {
    this.url        = url
    this.websocket  = null
    this.onMessage  = onMessage
    this.onConnect  = onConnect
    this.onErr      = onErr
  }

  open() {
    if (this.websocket)
      return

    console.log('websocket connecting:', this.url.toString())
    this.websocket = new WebSocket(this.url)

    this.websocket.onopen = () => {
      console.log('websocket connected')
      this.onConnect()
    }

    this.websocket.onerror = (event) => {
      console.log('websocket error:', event)
      this.onErr(event)
      this.websocket.close()
    }

    this.websocket.onmessage = (msg) => {
      const jso = JSON.parse(msg.data)
      this.onMessage(jso)
    }

    this.websocket.onclose = () => {
      console.log('websocket: closed')
      this.websocket = null
      // Retry the connection after a second.
      setTimeout(() => this.open(), 1000)
    }
  }

  close() {
    if (this.websocket !== null)
      this.websocket.close()
  }
}
