import React, { useState } from 'react'
import './styles.css'

export default function App() {
  const [response, setResponse] = useState<string | null>(null)
  const [statusLevel, setStatusLevel] = useState<string | null>(null)

  async function sendNoOp() {
    const payload = {
      idempotency_key: 'test-noop-1',
      action_id: 'NO_OP',
      payload: { noop: true }
    }

    const res = await fetch('http://127.0.0.1:8000/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    let json = null
    try {
      json = await res.json()
    } catch (e) {
      setResponse(`Failed to parse JSON response: ${e}`)
      return
    }

    // Normalize display fields according to command/result contract
    const status = json.status || (res.status === 200 ? 'ok' : 'error')
    const action = json.action_id || json.action || payload.action_id
    const idempotency = json.idempotency_key || payload.idempotency_key
    const dataField = json.data || json.action_result || null
    const event = json.event || null

    setResponse(JSON.stringify({ status, action, idempotency, data: dataField, event }, null, 2))
    setStatusLevel(status)
  }

  return (
    <div className="app-container">
      <div className="card">
        <h1 className="title">FantasyAGE</h1>
        <p className="subtitle">Send a no-op command to test roundtrip</p>
        <div className="controls">
          <button className="btn" onClick={sendNoOp}>Send No-Op Command</button>
        </div>
        <div className="response">
          {statusLevel && (
            <div className={`status-indicator ${
              statusLevel === 'ok' ? 'status-ok' : statusLevel === 'warning' || statusLevel === 'partial' ? 'status-warning' : 'status-error'
            }`} />
          )}
          <pre>{response ?? 'No response yet'}</pre>
        </div>
      </div>
    </div>
  )
}
