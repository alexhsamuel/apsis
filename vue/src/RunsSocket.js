export default class RunsSocket {
  constructor(run_id, job_id) {
    this.url = RunsSocket.get_url(run_id, job_id)
    this.websocket = null
  }

  open(callback) {
    this.websocket = new WebSocket(this.url)
    this.websocket.onmessage = (msg) => {
      const jso = JSON.parse(msg.data)
      callback(jso)
    }
    this.websocket.onclose = () => {
      console.log('web socket closed: ' + this.url)
      this.websocket = null
    }
  }

  close() {
    if (this.websocket !== null)
      this.websocket.close()
  }

  static get_url(run_id, job_id) {
    const url = new URL(location)
    url.protocol = 'ws'
    url.pathname = '/api/v1/runs-live'
    if (run_id !== undefined)
      url.searchParams.set('run_id', run_id)
    if (job_id !== undefined)
      url.searchParams.set('job_id', job_id)
    return url
  }
}

