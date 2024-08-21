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
    this.isOpen     = false
  }

  open() {
    if (this.websocket !== null)
      // Already have a websocket.
      return

    console.log('websocket connecting:', this.url.toString())
    this.websocket = new WebSocket(this.url)

    this.websocket.onopen = () => {
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
      this.websocket = null
      // Retry the connection after a second.
      if (this.isOpen)
        setTimeout(() => this.open(), 1000)
    }

    this.isOpen = true
  }

  close() {
    if (this.isOpen) {
      if (this.websocket !== null)
        this.websocket.close()
      this.isOpen = false
    }
  }
}
