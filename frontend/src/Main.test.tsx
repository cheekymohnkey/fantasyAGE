import { render, screen } from '@testing-library/react'
import { act } from 'react'

// Ensure a root element exists before importing the app entrypoint
beforeAll(() => {
  const root = document.createElement('div')
  root.id = 'root'
  document.body.appendChild(root)
})

it('imports and runs main entrypoint mounting the App', async () => {
  // dynamic import so the module executes after DOM setup
  await act(async () => {
    await import('./main')
  })
  // wait for the App to render
  const title = await screen.findByText('FantasyAGE')
  expect(title).toBeInTheDocument()
})
