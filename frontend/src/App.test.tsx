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

    render(<App />)

    // ensure input present and empty
    const input = screen.getByLabelText('Player name') as HTMLInputElement
    expect(input).toBeInTheDocument()
    expect(input.value).toBe('')

    // click send to trigger mocked fetch
    fireEvent.click(screen.getByRole('button', { name: 'Send No-Op Command' }))

    // remediation hint should appear
    const remediationNodes = await screen.findAllByText("Missing 'player_name'.")
    expect(remediationNodes.length).toBeGreaterThan(0)

    // input should have error class
    expect(input.className).toContain('input-error')
  })
})
