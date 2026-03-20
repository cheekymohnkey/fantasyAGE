import React, { useState, useRef } from 'react'
import './styles.css'

export default function App() {
  const [response, setResponse] = useState<string | null>(null)
  const [statusLevel, setStatusLevel] = useState<string | null>(null)
  const [errorMeta, setErrorMeta] = useState<any | null>(null)
  const [playerName, setPlayerName] = useState<string>('')
  const [fieldErrors, setFieldErrors] = useState<Record<string,string>>({})
  const nameRef = useRef<HTMLInputElement | null>(null)

  async function sendNoOp() {
    const payload = {
      idempotency_key: 'test-noop-1',
      action_id: 'NO_OP',
      payload: { noop: true, player_name: playerName }
    }

    const backendBase = (import.meta as any).env?.VITE_BACKEND_URL || ''
    const url = backendBase ? `${backendBase.replace(/\/$/, '')}/api/command` : '/api/command'

    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    const resClone = res.clone()
    let json = null
    let rawText = null
    try {
      json = await res.json()
    } catch (e) {
      try {
        rawText = await resClone.text()
      } catch (e2) {
        rawText = `<failed to read response body: ${e2}>`
      }
      setResponse(`Non-JSON response (status=${res.status}):\n${rawText}`)
      setStatusLevel(res.ok ? 'ok' : 'error')
      return
    }

    // Normalize display fields according to command/result contract
    const status = json?.status || (res.status === 200 ? 'ok' : 'error')
    const action = json?.action_id || json?.action || payload.action_id
    const idempotency = json?.idempotency_key || payload.idempotency_key
    const dataField = json?.data || json?.action_result || null
    const event = json?.event || null

    // Capture structured error metadata for UX mapping (validation, preconditions)
    const reason = json?.reason_code || null
    const remediation = json?.remediation_hint || null
    if (reason) {
      setErrorMeta({ reason, remediation, message: json?.message || null })

      // If backend indicates a missing field, try to extract field name and mark inline
      if (reason === 'validation.missing_field') {
        const match = (remediation || json?.message || '').match(/'([^']+)'/) || []
        const field = match[1] || 'unknown'
        setFieldErrors({ [field]: remediation || json?.message || 'Missing required field' })
        // focus the field if present
        if (field === 'player_name' && nameRef.current) nameRef.current.focus()
      }
    } else {
      setErrorMeta(null)
      setFieldErrors({})
    }

    setResponse(JSON.stringify({ status, action, idempotency, data: dataField, event }, null, 2))
    setStatusLevel(status)
  }

  return (
    <div className="app-container">
      <div className="card">
        <h1 className="title">FantasyAGE</h1>
        <p className="subtitle">Send a no-op command to test roundtrip</p>
        <div className="controls">
          <label style={{display:'flex',flexDirection:'column',gap:6}}>
            Player name
            <input
              aria-label="Player name"
              ref={nameRef}
              className={fieldErrors['player_name'] ? 'input-error' : ''}
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
            />
            {fieldErrors['player_name'] && (
              <div className="field-error">{fieldErrors['player_name']}</div>
            )}
          </label>
          <button className="btn" onClick={sendNoOp}>Send No-Op Command</button>
          <button
            className="btn"
            onClick={() => {
              setPlayerName('')
              setFieldErrors({})
              setErrorMeta(null)
              setResponse(null)
            }}
          >Reset</button>
        </div>
        <div className="response">
          {errorMeta && (
            <div className="toast toast-error">
              <strong>Error:</strong> {errorMeta.reason}
              {errorMeta.remediation && (
                <div className="toast-remediation">{errorMeta.remediation}</div>
              )}
            </div>
          )}
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
