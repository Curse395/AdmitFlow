import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'

describe('AdmitFlow dashboard', () => {
  it('renders the authentication card', () => {
    render(<App />)

    expect(screen.getByText(/Secure access/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('toggles the theme mode button', () => {
    render(<App />)

    const themeButton = screen.getByRole('button', { name: /switch to (light|dark) theme/i })
    const previousLabel = themeButton.getAttribute('aria-label')
    fireEvent.click(themeButton)

    expect(themeButton.getAttribute('aria-label')).not.toBe(previousLabel)
  })

  it('clears stale bearer tokens and returns to the secure access screen', async () => {
    localStorage.setItem('admitflow-token', 'stale-token')
    localStorage.setItem('admitflow-user', JSON.stringify({ email: 'admin@admitflow.local', role: 'admin' }))
    vi.stubGlobal('fetch', vi.fn(async (_url) => ({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid token' }),
    })))

    render(<App />)

    await waitFor(() => expect(screen.getByText(/Secure access/i)).toBeInTheDocument())
    expect(localStorage.getItem('admitflow-token')).toBeNull()
    expect(localStorage.getItem('admitflow-user')).toBeNull()
  })

  it('loads live cohort data with the stored bearer token', async () => {
    localStorage.setItem('admitflow-token', 'test-token')
    const responses = {
      '/api/dashboard': { applicants: 4, applications: 4, admissions: 2, enrolments: 1, overall_conversion: 25 },
      '/api/funnel': { stage_summary: [] },
      '/api/cohorts': {
        region: [{ region: 'North', applicants: 4, admission_rate: 0.5, enrolment_rate: 0.25 }],
        selectivity: [{ selectivity: 'Selective', applicants: 4, admission_rate: 0.5, enrolment_rate: 0.25 }],
      },
      '/api/programmes': [],
      '/api/attribution': [{ campaign_source: 'Referral', applications: 4, share_of_applications: 1, admission_conversion: 0.5, enrolment_conversion: 0.25 }],
      '/api/forecast': { metrics: { mae: 1, rmse: 1, mape: 0.1 }, horizons: { H1: 2, H2: 2, H4: 2, H6: 2 }, series: [], future_series: [], forecast_years: [] },
      '/api/scenarios': { baseline: {}, scenario: {}, difference: {}, percentage_change: {} },
      '/api/scenarios/run': { baseline: {}, scenario: {}, difference: {}, percentage_change: {} },
      '/api/model': { baseline: {}, advanced: {} },
      '/api/audit': [],
      '/api/cycle': [],
      '/api/assistant/status': { configured: false, provider: null },
    }
    vi.stubGlobal('fetch', vi.fn(async (url) => ({
      ok: true,
      json: async () => responses[new URL(url).pathname],
    })))
    render(<App />)

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(11))
    expect(globalThis.fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer test-token')
    fireEvent.click(screen.getByRole('button', { name: 'Cohorts' }))
    fireEvent.change(screen.getByLabelText('Compare by'), { target: { value: 'region' } })
    expect((await screen.findAllByText('North')).length).toBeGreaterThan(0)
    fireEvent.change(screen.getByLabelText('Compare by'), { target: { value: 'selectivity' } })
    expect((await screen.findAllByText('Selective')).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: 'Attribution' }))
    expect((await screen.findAllByText('Referral')).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: 'Scenario' }))
    fireEvent.change(screen.getByLabelText('Exact volume'), { target: { value: '5200' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run scenario' }))
    await waitFor(() => expect(globalThis.fetch.mock.calls.some(([url]) => new URL(url).pathname === '/api/scenarios/run')).toBe(true))
    const request = globalThis.fetch.mock.calls.find(([url]) => new URL(url).pathname === '/api/scenarios/run')
    expect(JSON.parse(request[1].body).application_volume).toBe(5200)
    expect(screen.getByText('Baseline to scenario')).toBeInTheDocument()
    expect(screen.getAllByText('Submitted').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: 'Ask AI' }))
    expect(await screen.findByText(/GROQ_API_KEY/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /largest funnel drop-off/i })).toBeDisabled()
    fireEvent.keyDown(window, { key: 'Escape' })
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true })
    const search = await screen.findByRole('textbox', { name: /search pages, programmes, and metrics/i })
    fireEvent.change(search, { target: { value: '4 applications' } })
    fireEvent.click(screen.getByRole('option', { name: /4 applications/i }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Admission intelligence' })).toBeInTheDocument()
  })
})
