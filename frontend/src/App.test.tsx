import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders no-op command control', () => {
    render(<App />)
    expect(screen.getByText('FantasyAGE')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send No-Op Command' })).toBeInTheDocument()
  })

  it('highlights missing field when backend returns validation.missing_field', async () => {
    const mockResp = {
      status: 'error',
      reason_code: 'validation.missing_field',
      message: "Missing required field",
      remediation_hint: "Missing 'player_name'.",
    }

    // mock global.fetch (include clone() used by the client)
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 400,
        json: async () => mockResp,
        clone: () => ({ text: async () => JSON.stringify(mockResp) }),
      })
    ))

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
