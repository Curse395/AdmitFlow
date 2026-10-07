import { useEffect, useRef } from 'react'
import { ArrowRight, ChartNoAxesCombined, GraduationCap, Search, Sparkles } from 'lucide-react'

const destinations = ['Dashboard', 'Funnel', 'Cohorts', 'Programmes', 'Attribution', 'Forecast', 'Scenario', 'Model', 'Audit']

export default function CommandPalette({ query, setQuery, data, onNavigate, onAskAI, onClose, onSelectProgramme }) {
  const inputRef = useRef(null)
  const search = query.trim().toLowerCase()
  const actions = [
    ...destinations.map((label) => ({ label, detail: 'Navigate to page', type: 'page', icon: ChartNoAxesCombined })),
    ...(data?.programme || []).map((row) => ({ label: row.programme, detail: 'Open programme profile', type: 'programme', icon: GraduationCap })),
    ...(data ? [
      { label: `${new Intl.NumberFormat('en-US').format(data.dashboard.applications)} applications`, detail: 'Current applicant total', type: 'metric', icon: ChartNoAxesCombined },
      { label: `${new Intl.NumberFormat('en-US').format(data.dashboard.enrolments)} enrolments`, detail: 'Current enrolled total', type: 'metric', icon: ChartNoAxesCombined },
      { label: `H1 forecast ${new Intl.NumberFormat('en-US').format(data.forecast.horizons.H1)}`, detail: 'Next-cycle enrolment projection', type: 'metric', icon: ChartNoAxesCombined },
    ] : []),
    { label: 'Ask AdmitFlow AI', detail: 'Ask a question about your data', type: 'assistant', icon: Sparkles },
  ]
  const filtered = actions.filter((action) => !search || `${action.label} ${action.detail}`.toLowerCase().includes(search)).slice(0, 9)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  function activate(action) {
    if (action.type === 'assistant') onAskAI()
    else if (action.type === 'programme') {
      onSelectProgramme(action.label)
      onNavigate('Programmes')
    } else onNavigate(action.type === 'metric' ? 'Dashboard' : action.label)
    onClose()
  }

  return (
    <div className="command-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section className="command-dialog" role="dialog" aria-modal="true" aria-labelledby="command-title">
        <h2 id="command-title" className="sr-only">Search AdmitFlow</h2>
        <div className="command-search-row">
          <Search size={19} aria-hidden="true" />
          <input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search pages, programmes, metrics..." aria-label="Search pages, programmes, and metrics" />
          <kbd>ESC</kbd>
        </div>
        <div className="command-section-label">{search ? 'Best matches' : 'Quick actions'}</div>
        <div className="command-results" role="listbox" aria-label="Search results">
          {filtered.map((action) => {
            const Icon = action.icon
            return (
              <button key={`${action.type}-${action.label}`} className="command-option" role="option" aria-selected="false" type="button" onClick={() => activate(action)}>
                <span className="command-option-icon"><Icon size={17} /></span>
                <span className="command-option-copy"><strong>{action.label}</strong><small>{action.detail}</small></span>
                <ArrowRight size={15} className="command-option-arrow" />
              </button>
            )
          })}
          {!filtered.length && <p className="command-empty">No matching pages or programmes.</p>}
        </div>
        <footer className="command-footer"><span><kbd>Tab</kbd> to move</span><span><kbd>↵</kbd> to open</span><span>AdmitFlow command search</span></footer>
      </section>
    </div>
  )
}
