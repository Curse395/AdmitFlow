import { useEffect, useState } from 'react'
import { BarChart, Bar, CartesianGrid, LineChart, Line, PieChart, Pie, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './App.css'

const palette = ['#4F46E5', '#10B981', '#F59E0B', '#F97316', '#EC4899']

const fetchJson = async (url, options = {}) => {
  const token = localStorage.getItem('admitflow-token')
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json()
}

function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('admitflow-theme') || 'light')
  const [token, setToken] = useState(() => localStorage.getItem('admitflow-token') || '')
  const [page, setPage] = useState('Dashboard')
  const [cohortDimension, setCohortDimension] = useState('region')
  const [scenarioInputs, setScenarioInputs] = useState({ application_volume: 5000, submitted: 1.05, admitted: 1.08, enrolled: 1.04 })
  const [loginForm, setLoginForm] = useState({ email: 'admin@admitflow.local', password: 'admin123' })
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    document.body.dataset.theme = theme
    localStorage.setItem('admitflow-theme', theme)
  }, [theme])

  const loadData = async () => {
    try {
      const [dashboard, funnel, cohorts, programme, attribution, forecast, scenario, model, audit] = await Promise.all([
        fetchJson('http://localhost:8000/api/dashboard'),
        fetchJson('http://localhost:8000/api/funnel'),
        fetchJson('http://localhost:8000/api/cohorts'),
        fetchJson('http://localhost:8000/api/programmes'),
        fetchJson('http://localhost:8000/api/attribution'),
        fetchJson('http://localhost:8000/api/forecast'),
        fetchJson('http://localhost:8000/api/scenarios'),
        fetchJson('http://localhost:8000/api/model'),
        fetchJson('http://localhost:8000/api/audit'),
      ])
      setData({ dashboard, funnel, cohorts, programme, attribution, forecast, scenario, model, audit })
      setError('')
    } catch {
      setData(null)
      setError('Analytics could not be loaded. Check that the API is running, then retry.')
    }
  }

  useEffect(() => {
    if (!token) return undefined
    const request = window.setTimeout(() => void loadData(), 0)
    return () => window.clearTimeout(request)
  }, [token])

  const handleLogin = async (event) => {
    event?.preventDefault()
    try {
      const payload = await fetchJson('http://localhost:8000/auth/login', {
        method: 'POST',
        body: JSON.stringify(loginForm),
      })
      localStorage.setItem('admitflow-token', payload.token)
      setToken(payload.token)
      setError('')
    } catch {
      setError('Authentication failed. Use the demo credentials shown in the panel.')
    }
  }

  const logout = async () => {
    if (token) {
      try {
        await fetchJson(`http://localhost:8000/auth/logout?token=${encodeURIComponent(token)}`, { method: 'POST' })
      } catch {
        // ignore network errors during logout
      }
    }
    localStorage.removeItem('admitflow-token')
    setToken('')
  }

  const runScenario = async (event) => {
    event.preventDefault()
    try {
      const scenario = await fetchJson('http://localhost:8000/api/scenarios/run', {
        method: 'POST',
        body: JSON.stringify({
          application_volume: Number(scenarioInputs.application_volume),
          stage_adjustments: {
            submitted: Number(scenarioInputs.submitted),
            admitted: Number(scenarioInputs.admitted),
            enrolled: Number(scenarioInputs.enrolled),
          },
        }),
      })
      setData((current) => ({ ...current, scenario }))
      setError('')
    } catch {
      setError('Scenario could not be calculated. Check the API connection and retry.')
    }
  }

  const navItems = ['Dashboard', 'Funnel', 'Cohorts', 'Programme', 'Attribution', 'Forecast', 'Scenario', 'Model', 'Audit']

  const renderDashboard = () => (
    <div className="content-grid">
      <div className="stat-grid">
        <div className="stat-card"><span>Applicants</span><strong>{data.dashboard.applicants}</strong></div>
        <div className="stat-card"><span>Admissions</span><strong>{data.dashboard.admissions}</strong></div>
        <div className="stat-card"><span>Enrolments</span><strong>{data.dashboard.enrolments}</strong></div>
        <div className="stat-card"><span>Overall conversion</span><strong>{data.dashboard.overall_conversion.toFixed(2)}%</strong></div>
      </div>
      <div className="panel-grid two-up">
        <div className="panel chart-panel">
          <h3>Programme performance</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.programme}>
              <CartesianGrid strokeDasharray="4 4" />
              <XAxis dataKey="programme" interval={0} angle={-18} textAnchor="end" height={64} tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(value) => `${Math.round(value * 100)}%`} />
              <Tooltip />
              <Bar dataKey="admission_rate" fill="#4F46E5" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="panel chart-panel">
            <h3>Funnel volume</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={data.funnel.stage_summary}>
              <CartesianGrid strokeDasharray="4 4" />
              <XAxis dataKey="stage" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="volume" stroke="#10B981" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )

  const renderFunnel = () => (
    <div className="panel">
      <h3>Admission funnel</h3>
      <table>
        <thead>
          <tr><th>Stage</th><th>Volume</th><th>Conversion rate</th></tr>
        </thead>
        <tbody>
          {data.funnel.stage_summary.map((row) => (
            <tr key={row.stage}>
              <td>{row.stage}</td>
              <td>{row.volume}</td>
              <td>{((row.conversion_rate || 0) * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  const renderCohorts = () => (
    <div className="panel-grid two-up">
      <div className="panel">
        <h3>{cohortDimension[0].toUpperCase() + cohortDimension.slice(1)} cohorts</h3>
        <label>
          Cohort dimension
          <select value={cohortDimension} onChange={(event) => setCohortDimension(event.target.value)}>
            <option value="cycle">Cycle</option>
            <option value="programme">Programme</option>
            <option value="region">Region</option>
            <option value="selectivity">Selectivity</option>
          </select>
        </label>
        <table>
          <thead><tr><th>{cohortDimension}</th><th>Applicants</th><th>Admission rate</th><th>Enrolment rate</th></tr></thead>
          <tbody>
            {data.cohorts[cohortDimension].map((row) => {
              const dimensionKey = cohortDimension === 'cycle' ? 'cycle_year' : cohortDimension
              return (
              <tr key={row[dimensionKey]}>
                <td>{row[dimensionKey]}</td>
                <td>{row.applicants}</td>
                <td>{(row.admission_rate * 100).toFixed(1)}%</td>
                <td>{(row.enrolment_rate * 100).toFixed(1)}%</td>
              </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h3>Sample sufficiency</h3>
        <ul className="list">
          <li>Cycle cohorts are evaluated for minimum viable counts before conclusions.</li>
          <li>Small cohorts are flagged as low confidence in the analytics layer.</li>
          <li>Interpretation remains descriptive rather than causal.</li>
        </ul>
      </div>
    </div>
  )

  const renderProgramme = () => (
    <div className="panel">
      <h3>Programme comparison</h3>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie dataKey="admission_rate" data={data.programme} outerRadius={100} innerRadius={40} fill="#4F46E5" label>
            {data.programme.map((entry, idx) => (
              <Cell key={entry.programme} fill={palette[idx % palette.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )

  const renderForecast = () => (
    <div className="panel-grid two-up">
      <div className="panel">
        <h3>Forecast metrics</h3>
        <div className="stat-list">
          <div><span>MAE</span><strong>{data.forecast.metrics.mae}</strong></div>
          <div><span>RMSE</span><strong>{data.forecast.metrics.rmse}</strong></div>
          <div><span>MAPE</span><strong>{data.forecast.metrics.mape}</strong></div>
        </div>
      </div>
      <div className="panel">
        <h3>Horizon outlook</h3>
        <table>
          <thead><tr><th>Horizon</th><th>Forecast</th></tr></thead>
          <tbody>
            {Object.entries(data.forecast.horizons).map(([key, value]) => (
              <tr key={key}><td>{key}</td><td>{value}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const renderAttribution = () => (
    <div className="panel">
      <h3>Campaign attribution</h3>
      <table>
        <thead><tr><th>Source</th><th>Applications</th><th>Share</th><th>Admission rate</th><th>Enrolment rate</th></tr></thead>
        <tbody>
          {data.attribution.map((row) => (
            <tr key={row.campaign_source}>
              <td>{row.campaign_source}</td>
              <td>{row.applications}</td>
              <td>{(row.share_of_applications * 100).toFixed(1)}%</td>
              <td>{(row.admission_conversion * 100).toFixed(1)}%</td>
              <td>{(row.enrolment_conversion * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted">Descriptive attribution only; these associations do not establish causal impact.</p>
    </div>
  )

  const renderScenario = () => (
    <div className="panel-grid two-up">
      <div className="panel">
        <h3>Deterministic scenario</h3>
        <table>
          <thead><tr><th>Metric</th><th>Baseline</th><th>Scenario</th><th>Delta</th><th>Change</th></tr></thead>
          <tbody>
            <tr><td>Applications</td><td>{data.scenario.baseline.applications}</td><td>{data.scenario.scenario.applications}</td><td>{data.scenario.difference.applications}</td><td>{data.scenario.percentage_change.applications}%</td></tr>
            <tr><td>Submitted</td><td>{data.scenario.baseline.submitted}</td><td>{data.scenario.scenario.submitted}</td><td>{data.scenario.difference.submitted}</td><td>{data.scenario.percentage_change.submitted}%</td></tr>
            <tr><td>Admitted</td><td>{data.scenario.baseline.admitted}</td><td>{data.scenario.scenario.admitted}</td><td>{data.scenario.difference.admitted}</td><td>{data.scenario.percentage_change.admitted}%</td></tr>
            <tr><td>Enrolled</td><td>{data.scenario.baseline.enrolled}</td><td>{data.scenario.scenario.enrolled}</td><td>{data.scenario.difference.enrolled}</td><td>{data.scenario.percentage_change.enrolled}%</td></tr>
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h3>Scenario assumptions</h3>
        <form className="scenario-form" onSubmit={runScenario}>
          <label>Application volume<input type="number" min="1" step="1" value={scenarioInputs.application_volume} onChange={(event) => setScenarioInputs((current) => ({ ...current, application_volume: event.target.value }))} /></label>
          <label>Submitted multiplier<input type="number" min="0" max="3" step="0.01" value={scenarioInputs.submitted} onChange={(event) => setScenarioInputs((current) => ({ ...current, submitted: event.target.value }))} /></label>
          <label>Admitted multiplier<input type="number" min="0" max="3" step="0.01" value={scenarioInputs.admitted} onChange={(event) => setScenarioInputs((current) => ({ ...current, admitted: event.target.value }))} /></label>
          <label>Enrolled multiplier<input type="number" min="0" max="3" step="0.01" value={scenarioInputs.enrolled} onChange={(event) => setScenarioInputs((current) => ({ ...current, enrolled: event.target.value }))} /></label>
          <button className="primary-button" type="submit">Run scenario</button>
        </form>
      </div>
    </div>
  )

  const renderModel = () => (
    <div className="panel-grid two-up">
      <div className="panel">
        <h3>Baseline performance</h3>
        <div className="stat-list">
          <div><span>Accuracy</span><strong>{data.model.baseline.accuracy}</strong></div>
          <div><span>ROC-AUC</span><strong>{data.model.baseline.roc_auc}</strong></div>
          <div><span>PR-AUC</span><strong>{data.model.baseline.pr_auc}</strong></div>
          <div><span>F1</span><strong>{data.model.baseline.f1}</strong></div>
        </div>
        <h4>Top feature signals</h4>
        <ol className="list">
          {data.model.baseline.top_features.map((item) => <li key={item.feature}>{item.feature.replace(/^(num__|cat__)/, '')}</li>)}
        </ol>
      </div>
      <div className="panel">
        <h3>Advanced performance</h3>
        <div className="stat-list">
          <div><span>Accuracy</span><strong>{data.model.advanced.accuracy}</strong></div>
          <div><span>ROC-AUC</span><strong>{data.model.advanced.roc_auc}</strong></div>
          <div><span>PR-AUC</span><strong>{data.model.advanced.pr_auc}</strong></div>
          <div><span>F1</span><strong>{data.model.advanced.f1}</strong></div>
        </div>
        <h4>Top feature signals</h4>
        <ol className="list">
          {data.model.advanced.top_features.map((item) => <li key={item.feature}>{item.feature.replace(/^(num__|cat__)/, '')}</li>)}
        </ol>
      </div>
      <p className="muted">Feature signals summarize model associations and are not evidence of causal effects.</p>
    </div>
  )

  const renderAudit = () => (
    <div className="panel">
      <h3>Recent activity</h3>
      <table>
        <thead><tr><th>Action</th><th>Email</th><th>Status</th></tr></thead>
        <tbody>
          {data.audit.map((row, idx) => (
            <tr key={`${row.action}-${idx}`}>
              <td>{row.action}</td>
              <td>{row.email || 'system'}</td>
              <td>{row.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  const views = {
    Dashboard: renderDashboard,
    Funnel: renderFunnel,
    Cohorts: renderCohorts,
    Programme: renderProgramme,
    Attribution: renderAttribution,
    Forecast: renderForecast,
    Scenario: renderScenario,
    Model: renderModel,
    Audit: renderAudit,
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Data Science capstone</p>
          <h1>AdmitFlow</h1>
        </div>
        <div className="topbar-actions">
          <button className="ghost-button" type="button" onClick={() => setTheme((current) => current === 'light' ? 'dark' : 'light')}>
            {theme === 'light' ? 'Dark mode' : 'Light mode'}
          </button>
          {token ? (
            <button className="primary-button" type="button" onClick={logout}>Logout</button>
          ) : (
            <button className="primary-button" type="button" onClick={() => void handleLogin()}>Demo login</button>
          )}
        </div>
      </header>

      {!token ? (
        <main className="login-panel">
          <div className="login-card">
            <h2>Secure access</h2>
            <p>Use the local demo credentials for the authenticated dashboard flow.</p>
            <form onSubmit={handleLogin}>
              <label>
                Email
                <input type="email" value={loginForm.email} onChange={(event) => setLoginForm((current) => ({ ...current, email: event.target.value }))} />
              </label>
              <label>
                Password
                <input type="password" value={loginForm.password} onChange={(event) => setLoginForm((current) => ({ ...current, password: event.target.value }))} />
              </label>
              <button className="primary-button" type="submit">Log in</button>
            </form>
            <small>Demo user: admin@admitflow.local / admin123</small>
            {error && <p className="error-message">{error}</p>}
          </div>
        </main>
      ) : (
        <>
          {!data ? (
            <main className="content-area">
              <div className="panel" role={error ? 'alert' : 'status'}>
                {error || 'Loading analytics...'}
                {error && <button className="primary-button" type="button" onClick={() => { setError(''); void loadData() }}>Retry</button>}
              </div>
            </main>
          ) : (
            <>
              <nav className="nav tabs" aria-label="Main navigation">
                {navItems.map((item) => (
                  <button
                    key={item}
                    type="button"
                    className={page === item ? 'nav-button active' : 'nav-button'}
                    onClick={() => setPage(item)}
                  >
                    {item}
                  </button>
                ))}
              </nav>
              {error && <div className="toast" role="alert">{error}</div>}
              <main className="content-area">
                {views[page]()}
              </main>
            </>
          )}
        </>
      )}
    </div>
  )
}

export default App
