import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import App from './App'

describe('App', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('renders no-op command control', () => {
    // stub sessions fetch
    vi.stubGlobal('fetch', vi.fn((input: any) => {
      if (typeof input === 'string' && input.endsWith('/api/sessions')) {
        // Keep this pending in the synchronous render test to avoid late state updates.
        return new Promise(() => {})
      }
      return Promise.resolve({ ok: true, json: async () => ({ status: 'ok' }), clone: () => ({ text: async () => '{}' }) })
    }))

    render(<App />)
    expect(screen.getByText('FantasyAGE')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send No-Op Command' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry Last Command' })).toBeDisabled()
    // selector inputs present
    expect(screen.getByLabelText('Login id')).toBeInTheDocument()
    expect(screen.getByLabelText('Campaign id')).toBeInTheDocument()
    expect(screen.getByLabelText('Session id')).toBeInTheDocument()
  })

  it('highlights missing field when backend returns validation.missing_field', async () => {
    const mockResp = {
      status: 'error',
      reason_code: 'validation.missing_field',
      message: "Missing required field",
      remediation_hint: "Missing 'player_name'.",
    }

    // mock global.fetch (include clone() used by the client) and handle sessions endpoint
    vi.stubGlobal('fetch', vi.fn((input: any) => {
      if (typeof input === 'string' && input.endsWith('/api/sessions')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ status: 'ok', sessions: [] }),
          clone: () => ({ text: async () => JSON.stringify({ status: 'ok', sessions: [] }) }),
        })
      }
      return Promise.resolve({
        ok: false,
        status: 400,
        json: async () => mockResp,
        clone: () => ({ text: async () => JSON.stringify(mockResp) }),
      })
    }))

  })

  it('shows context mismatch banner when precondition error is returned', async () => {
    vi.stubGlobal('fetch', vi.fn((input: any) => {
      if (typeof input === 'string' && input.endsWith('/api/sessions')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ status: 'ok', sessions: [] }),
          clone: () => ({ text: async () => JSON.stringify({ status: 'ok', sessions: [] }) }),
        })
      }
      if (typeof input === 'string' && input.endsWith('/api/command')) {
        return Promise.resolve({
          ok: false,
          status: 412,
          json: async () => ({
            status: 'error',
            reason_code: 'precondition.campaign_session_mismatch',
            message: 'Session/campaign mismatch',
            remediation_hint: 'Select a valid session/campaign',
          }),
          clone: () => ({ text: async () => JSON.stringify({ status: 'error' }) }),
        })
      }
      return Promise.resolve({ ok: true, json: async () => ({ status: 'ok' }), clone: () => ({ text: async () => '{}' }) })
    }))

    render(<App />)

    const sendButton = screen.getByRole('button', { name: 'Send No-Op Command' })
    expect(sendButton).toBeInTheDocument()

    sendButton.click()

    const banner = await screen.findByText('Context mismatch:')
    expect(banner).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reset to default context' })).toBeInTheDocument()
  })

  it('fetches and renders session events when Refresh Events clicked', async () => {
    vi.stubGlobal('fetch', vi.fn((input: any) => {
      if (typeof input === 'string' && input.endsWith('/api/sessions')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ status: 'ok', sessions: [] }),
          clone: () => ({ text: async () => JSON.stringify({ status: 'ok', sessions: [] }) }),
        })
      }

      if (typeof input === 'string' && input.endsWith('/api/sessions/default/events')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            status: 'ok',
            events: [
              {
                idempotency_key: 'event-123',
                action_id: 'NO_OP',
                created_at: '2026-03-22T00:00:00Z',
                action_result: { foo: 'bar' },
              },
            ],
          }),
          clone: () => ({ text: async () => JSON.stringify({ status: 'ok', events: [] }) }),
        })
      }

      return Promise.resolve({
        ok: true,
        json: async () => ({ status: 'ok' }),
        clone: () => ({ text: async () => '{}' }),
      })
    }))

    render(<App />)

    const refreshButton = screen.getByRole('button', { name: 'Refresh Events' })
    expect(refreshButton).toBeInTheDocument()

    refreshButton.click()

    const listItems = await screen.findAllByRole('listitem')
    expect(listItems.length).toBeGreaterThan(0)
    expect(listItems[0]).toHaveTextContent('event-123')
    expect(listItems[0]).toHaveTextContent('NO_OP')
  })
})
