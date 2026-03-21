import React, { useEffect, useState } from 'react'

const STORAGE_KEY = 'fantasyage.session_selector'

type SelectorState = {
  loginId: string
  campaignId: string
  sessionId: string
}

export default function SessionSelector({ onChange }: { onChange?: (s: SelectorState) => void }) {
  const [state, setState] = useState<SelectorState>({
    loginId: 'default',
    campaignId: 'default',
    sessionId: 'default',
  })
  const [sessions, setSessions] = useState<Array<{session_id:string,campaign_id:string,login_id:string}>>([])

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        setState(JSON.parse(raw))
      }
    } catch (e) {
      // ignore
    }
  }, [])

  // fetch known sessions from backend
  useEffect(() => {
    let mounted = true
    try {
      fetch('/api/sessions')
        .then((r) => r.json())
        .then((j) => {
          if (!mounted) return
          const list = j?.sessions || []
          setSessions(list)
        })
        .catch(() => {
          if (mounted) setSessions([])
        })
    } catch (e) {
      // ignore
    }
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch (e) {
      // ignore
    }
    onChange?.(state)
  }, [state, onChange])

  return (
    <div style={{display:'flex',gap:8,alignItems:'center',marginBottom:8}}>
      <label style={{display:'flex',flexDirection:'column'}}>
        Login
        <input aria-label="Login id" value={state.loginId} onChange={(e)=>setState({...state,loginId:e.target.value})} />
      </label>
      <label style={{display:'flex',flexDirection:'column'}}>
        Campaign
        <input aria-label="Campaign id" value={state.campaignId} onChange={(e)=>setState({...state,campaignId:e.target.value})} />
      </label>
      <label style={{display:'flex',flexDirection:'column'}}>
        Session
        <input aria-label="Session id" value={state.sessionId} onChange={(e)=>setState({...state,sessionId:e.target.value})} />
      </label>
      {sessions.length > 0 && (
        <label style={{display:'flex',flexDirection:'column'}}>
          Known sessions
          <select aria-label="Known sessions" value={state.sessionId} onChange={(e)=>setState({...state,sessionId:e.target.value})}>
            {sessions.map(s => (
              <option key={s.session_id} value={s.session_id}>{s.session_id} ({s.campaign_id})</option>
            ))}
          </select>
        </label>
      )}
    </div>
  )
}
