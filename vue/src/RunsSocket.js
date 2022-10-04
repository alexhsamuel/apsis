export default class RunsSocket {
  constructor(callback, onConnect, onErr) {
    this.url = RunsSocket.get_url()
    this.websocket = null
    this.callback = callback
    this.onConnect = onConnect
    this.onErr = onErr
    this.open()
  }

  open() {
    if (this.websocket)
      return

    console.log('run web socket: opening ' + this.url)
    this.websocket = new WebSocket(this.url)

    this.websocket.onopen = () => {
      console.log('run web socket: connected')
      this.onConnect()
    }

    this.websocket.onerror = (event) => {
      console.log('run web socket: error:', event)
      this.onErr(event)
      this.websocket.close()
    }

    this.websocket.onmessage = (msg) => {
      const jso = JSON.parse(msg.data)
      this.callback(jso)
    }

    this.websocket.onclose = () => {
      console.log('run web socket: closed')
      this.websocket = null
      setTimeout(() => this.open(), 1000)
    }
  }

  close() {
    if (this.websocket !== null)
      this.websocket.close()
  }

  static get_url(run_id, job_id) {
    const url = new URL(location)
    url.protocol = 'ws'
    url.pathname = '/api/v1/ws/runs'
    if (run_id !== undefined)
      url.searchParams.set('run_id', run_id)
    if (job_id !== undefined)
      url.searchParams.set('job_id', job_id)
    return url
  }
}

