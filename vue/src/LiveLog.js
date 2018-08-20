export default class LiveLog {
  constructor(lines, maxLines) {
    this.url = new URL(location)
    this.url.protocol = 'ws'
    this.url.pathname = '/api/log'

    this.lines = lines
    this.maxLines = maxLines

    console.log('live log web socket connecting to ' + this.url)
    this.websocket = new WebSocket(this.url)

    this.websocket.onmessage = (msg) => {
      const lines = JSON.parse(msg.data)
      for (let i = 0; i < lines.length; ++i)
        this.lines.push(lines[i])
      if (this.lines.length > this.maxLines)
        this.lines.splice(0, this.maxLines - this.lines.length)
    }
    
    this.websocket.onclose = () => {
      console.log('live log web socket closed')
      this.websocket = null
    }
  }

  close() {
    if (this.websocket !== null)
      this.websocket.close()
  }
}
