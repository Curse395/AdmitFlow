import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'

describe('AdmitFlow dashboard', () => {
  it('renders the authentication card', () => {
    render(<App />)

    expect(screen.getByText(/Secure access/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument()
  })

  it('toggles the theme mode button', () => {
    render(<App />)

    const themeButton = screen.getByRole('button', { name: /dark mode/i })
    fireEvent.click(themeButton)

    expect(screen.getByRole('button', { name: /light mode/i })).toBeInTheDocument()
  })

  it('loads live cohort data with the stored bearer token', async () => {
    localStorage.setItem('admitflow-token', 'test-token')
    const responses = {
      '/api/dashboard': { applicants: 4, admissions: 2, enrolments: 1, overall_conversion: 25 },
      '/api/funnel': { stage_summary: [] },
      '/api/cohorts': {
        region: [{ region: 'North', applicants: 4, admission_rate: 0.5, enrolment_rate: 0.25 }],
        selectivity: [{ selectivity: 'Selective', applicants: 4, admission_rate: 0.5, enrolment_rate: 0.25 }],
      },
      '/api/programmes': [],
      '/api/attribution': [{ campaign_source: 'Referral', applications: 4, share_of_applications: 1, admission_conversion: 0.5, enrolment_conversion: 0.25 }],
      '/api/forecast': { metrics: { mae: 1, rmse: 1, mape: 0.1 }, horizons: { H1: 2 } },
      '/api/scenarios': { baseline: {}, scenario: {}, difference: {}, percentage_change: {} },
      '/api/scenarios/run': { baseline: {}, scenario: {}, difference: {}, percentage_change: {} },
      '/api/model': { baseline: {}, advanced: {} },
      '/api/audit': [],
    }
    vi.stubGlobal('fetch', vi.fn(async (url) => ({
      ok: true,
      json: async () => responses[new URL(url).pathname],
    })))
    render(<App />)

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(9))
    expect(globalThis.fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer test-token')
    fireEvent.click(screen.getByRole('button', { name: 'Cohorts' }))
    expect(await screen.findByText('North')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Cohort dimension'), { target: { value: 'selectivity' } })
    expect(await screen.findByText('Selective')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Attribution' }))
    expect(await screen.findByText('Referral')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Scenario' }))
    fireEvent.change(screen.getByLabelText('Application volume'), { target: { value: '5200' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run scenario' }))
    await waitFor(() => expect(globalThis.fetch.mock.calls.some(([url]) => new URL(url).pathname === '/api/scenarios/run')).toBe(true))
    const request = globalThis.fetch.mock.calls.find(([url]) => new URL(url).pathname === '/api/scenarios/run')
    expect(JSON.parse(request[1].body).application_volume).toBe(5200)
    expect(screen.getByRole('cell', { name: 'Submitted' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Change' })).toBeInTheDocument()
  })
})
