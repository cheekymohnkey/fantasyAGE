import React, { useState, useRef } from 'react'
import './styles.css'
import SessionSelector from './SessionSelector'

type CommandPayload = {
  idempotency_key: string
  action_id: string
  payload: {
    noop: boolean
    player_name: string
  }
  metadata: {
    login_id: string
    campaign_id: string
    session_id: string
  }
}

export default function App() {
  const [response, setResponse] = useState<string | null>(null)
  const [statusLevel, setStatusLevel] = useState<string | null>(null)
  const [errorMeta, setErrorMeta] = useState<any | null>(null)
  const [playerName, setPlayerName] = useState<string>('')
  const [selector, setSelector] = useState({ loginId: 'default', campaignId: 'default', sessionId: 'default' })
  const [fieldErrors, setFieldErrors] = useState<Record<string,string>>({})
  const [lastCommand, setLastCommand] = useState<CommandPayload | null>(null)
  const [events, setEvents] = useState<Array<any>>([])
  const [contextError, setContextError] = useState<string | null>(null)
  const nameRef = useRef<HTMLInputElement | null>(null)

  function buildIdempotencyKey() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID()
    }
    return `idem-${Date.now()}-${Math.random().toString(16).slice(2)}`
  }

  async function submitCommand(payload: CommandPayload) {
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

      const mismatchReasons = [
        'precondition.campaign_session_mismatch',
        'precondition.owner_scope_mismatch',
      ]
      if (mismatchReasons.includes(reason)) {
        setContextError(json?.message || remediation || 'Context mismatch detected')
      } else {
        setContextError(null)
      }

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
      setContextError(null)
    }

    setResponse(JSON.stringify({ status, action, idempotency, data: dataField, event }, null, 2))
    setStatusLevel(status)
  }

  async function sendNoOp() {
    const payload: CommandPayload = {
      idempotency_key: buildIdempotencyKey(),
      action_id: 'NO_OP',
      payload: { noop: true, player_name: playerName },
      metadata: {
        login_id: selector.loginId && selector.loginId.trim() ? selector.loginId.trim() : 'default',
        campaign_id: selector.campaignId && selector.campaignId.trim() ? selector.campaignId.trim() : 'default',
        session_id: selector.sessionId && selector.sessionId.trim() ? selector.sessionId.trim() : 'default',
      },
    }
    setLastCommand(payload)
    await submitCommand(payload)
    // Refresh events after successful send
    await fetchEvents(payload.metadata.session_id, payload.metadata.login_id)
  }

  async function retryLastCommand() {
    if (!lastCommand) return
    await submitCommand(lastCommand)
    await fetchEvents(lastCommand.metadata.session_id, lastCommand.metadata.login_id)
  }

  async function fetchEvents(sessionId: string, loginId?: string) {
    const trimmedSessionId = sessionId?.trim()
    if (!trimmedSessionId) {
      setResponse('Cannot refresh events: session id is empty')
      setStatusLevel('error')
      setEvents([])
      return
    }

    const backendBase = (import.meta as any).env?.VITE_BACKEND_URL || ''
    const base = backendBase ? `${backendBase.replace(/\/$/, '')}` : ''
    const url = `${base}/api/sessions/${encodeURIComponent(trimmedSessionId)}/events`
    const headers: Record<string,string> = { 'Content-Type': 'application/json' }
    if (loginId) headers['X-Login-Id'] = loginId
    try {
      const res = await fetch(url, { headers })
      if (!res.ok) {
        const err = await res.text().catch(() => 'failed to read body')
        setResponse(`Failed to fetch events (status=${res.status}): ${err}`)
        setStatusLevel('error')
        return
      }
      const j = await res.json()
      setEvents(j?.events || [])
      setResponse(JSON.stringify({ status: 'ok', sessionId: trimmedSessionId, events: j.events }, null, 2))
      setStatusLevel('ok')
    } catch (e) {
      setResponse(`Error fetching events: ${e}`)
      setStatusLevel('error')
    }
  }

  const isContextMismatch = contextError !== null

  return (
    <div className="app-container">
      <div className="card">
        <h1 className="title">FantasyAGE</h1>
        <p className="subtitle">Send a no-op command to test roundtrip</p>
        {isContextMismatch && (
          <div className="toast toast-warning">
            <strong>Context mismatch:</strong> {contextError}
            <div>Check campaign/session selection, or use the selector to recover context.</div>
            <button
              className="btn"
              onClick={() => {
                setSelector({ loginId: 'default', campaignId: 'default', sessionId: 'default' })
                setErrorMeta(null)
                setFieldErrors({})
                setContextError(null)
                setResponse('Reset context to default, please retry command')
                setStatusLevel('warning')
              }}
            >
              Reset to default context
            </button>
          </div>
        )}
        <div className="controls">
          <SessionSelector onChange={(s) => setSelector(s)} />
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
          <button className="btn" onClick={retryLastCommand} disabled={!lastCommand}>Retry Last Command</button>
          <button className="btn" onClick={() => fetchEvents(selector.sessionId, selector.loginId)}>Refresh Events</button>
          <button
            className="btn"
            onClick={() => {
              setPlayerName('')
              setFieldErrors({})
              setErrorMeta(null)
              setResponse(null)
              setLastCommand(null)
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
        <div className="events">
          <h3>Session Events</h3>
          {events.length === 0 && <div>No events</div>}
          {events.length > 0 && (
            <ul>
              {events.map((e:any) => (
                <li key={e.idempotency_key}>
                  <strong>{e.action_id}</strong> — {e.idempotency_key} — {e.created_at}
                  <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(e.action_result || {}, null, 2)}</pre>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
