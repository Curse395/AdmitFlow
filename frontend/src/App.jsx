import { useEffect, useState } from 'react'
import {
  ArrowRight, Bell, ChevronDown, CircleUserRound, LogOut, Menu, Moon, Search, Sparkles, Sun, X,
} from 'lucide-react'
import AssistantPanel from './components/AssistantPanel'
import CommandPalette from './components/CommandPalette'
import Sidebar from './components/Sidebar'
import {
  AttributionPage, AuditPage, CohortsPage, DashboardPage, ForecastPage, FunnelPage, ModelPage,
  ProgrammeDrawer, ProgrammesPage, ScenarioPage, SettingsPage,
} from './pages/WorkspacePages'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const pageContext = {
  Dashboard: ['OVERVIEW', 'Monitor application momentum and admission outcomes.'],
  Funnel: ['ANALYTICS / CONVERSION', 'Inspect how applicants move through each stage.'],
  Cohorts: ['ANALYTICS / SEGMENTS', 'Compare observed cycle and applicant groups.'],
  Programmes: ['ANALYTICS / OFFER PORTFOLIO', 'Explore programme application and enrolment performance.'],
  Attribution: ['ANALYTICS / CHANNELS', 'Understand the distribution of source-associated outcomes.'],
  Forecast: ['INTELLIGENCE / OUTLOOK', 'Review the projected enrolment trajectory and its limits.'],
  Scenario: ['INTELLIGENCE / PLANNING', 'Test controlled assumptions against the observed baseline.'],
  Model: ['INTELLIGENCE / EVALUATION', 'Inspect model holdout metrics and feature signals.'],
  Audit: ['SYSTEM / ACTIVITY', 'Review recent authentication and scenario events.'],
  Settings: ['SYSTEM / PREFERENCES', 'Manage local workspace preferences and connected services.'],
}

async function fetchJson(path, options = {}) {
  const token = localStorage.getItem('admitflow-token')
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`)
  return body
}

function userInitials(user) {
  return (user?.email || 'admin').split('@')[0].split(/[._-]/).map((part) => part[0]).join('').slice(0, 2).toUpperCase()
}

function LoadingWorkspace() {
  return <div className="page-stack loading-workspace" role="status" aria-label="Loading admission analytics">
    <div className="skeleton-heading"><i /><i /><i /></div>
    <div className="metric-grid">{Array.from({ length: 5 }, (_, index) => <div className="metric-card skeleton-card" key={index}><i /><i /><i /></div>)}</div>
    <div className="skeleton-panels"><div className="surface-panel skeleton-chart"><i /><i /><i /><i /><i /></div><div className="surface-panel skeleton-chart"><i /><i /><i /></div></div>
  </div>
}

function LoginPage({ onLogin, onUseDemo, loading, error, theme, onToggleTheme }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  return <main className="login-layout">
    <section className="login-story">
      <div className="login-brand"><span className="brand-symbol" aria-hidden="true"><span /><span /><span /></span><span>Admit<span>Flow</span></span></div>
      <div className="login-story-copy"><p className="eyebrow">ADMISSION INTELLIGENCE & FORECASTING</p><h1>Turn admission data into <em>predictable growth.</em></h1><p>One clear view of your applicant journey, programme performance, and enrollment outlook.</p></div>
      <div className="login-visual" aria-hidden="true"><div className="login-visual-grid"/><div className="login-funnel-line line-one"/><div className="login-funnel-line line-two"/><div className="login-funnel-line line-three"/><div className="login-node node-one"/><div className="login-node node-two"/><div className="login-node node-three"/><div className="login-data-readout"><span>ENROLMENT OUTLOOK</span><strong>H1 <i /></strong><small>Signal ready</small></div></div>
      <div className="login-story-footer"><span>ADMITFLOW / LOCAL WORKSPACE</span><span>DATA, MADE DECISIVE</span></div>
    </section>
    <section className="login-access-area"><button className="login-theme-toggle icon-button" type="button" onClick={onToggleTheme} aria-label={`Switch to ${theme==='dark'?'light':'dark'} theme`}>{theme==='dark'?<Sun size={17}/>:<Moon size={17}/>}</button><div className="login-access-card"><div className="access-card-top"><div className="access-icon"><CircleUserRound size={19}/></div><span className="context-badge"><i className="mini-live"/> Protected access</span></div><p className="eyebrow">WELCOME BACK</p><h2>Secure access</h2><p className="login-intro">Sign in to your admission intelligence workspace.</p><form onSubmit={(event)=>{event.preventDefault();onLogin({email,password})}} className="login-form"><label>Email address<input type="email" autoComplete="username" value={email} onChange={(event)=>setEmail(event.target.value)} placeholder="you@institution.edu" required/></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={(event)=>setPassword(event.target.value)} placeholder="Enter your password" required/></label><button className="primary-button login-submit" type="submit" disabled={loading}>{loading?<><span className="button-spinner"/> Securing workspace</>:<>Sign in <span>→</span></>}</button>{error&&<p className="login-error" role="alert">{error}</p>}</form><div className="login-divider"><span/>Local evaluation access<span/></div><button className="demo-access-button" type="button" onClick={onUseDemo}>Use demo access</button><p className="login-security-note">Demo sign-in is available for local evaluation. Credentials are not displayed in the interface.</p></div><div className="login-help"><span>AdmitFlow</span><span>Admission intelligence for enrollment teams</span></div></section>
  </main>
}

function NotificationsPopover({ audit, onClose }) {
  const recent = [...audit].reverse().slice(0, 4)
  return <div className="popover notification-popover"><div className="popover-heading"><div><span className="section-overline">RECENT ACTIVITY</span><h3>Notifications</h3></div><button className="icon-button" type="button" onClick={onClose} aria-label="Close notifications"><X size={15}/></button></div>{recent.length ? recent.map((event,index)=><div className="notification-row" key={`${event.action}-${event.timestamp||index}`}><span className="notification-dot"/><div><strong>{event.action.replaceAll('_',' ')}</strong><small>{event.timestamp?new Date(event.timestamp).toLocaleTimeString():event.status}</small></div></div>):<div className="popover-empty">No recent activity in this session.</div>}</div>
}

function UserPopover({ user, onLogout, onClose }) {
  return <div className="popover user-popover"><div className="user-popover-profile"><span className="profile-avatar">{userInitials(user)}</span><div><strong>{user?.email||'Admissions admin'}</strong><small>{user?.role||'Workspace admin'}</small></div></div><button type="button" onClick={onLogout}><LogOut size={15}/> Sign out</button><button className="popover-dismiss" type="button" onClick={onClose}>Close</button></div>
}

export default function App() {
  const [theme, setTheme] = useState(()=>localStorage.getItem('admitflow-theme')||'dark')
  const [token, setToken] = useState(()=>localStorage.getItem('admitflow-token')||'')
  const [user, setUser] = useState(()=>{try{return JSON.parse(localStorage.getItem('admitflow-user')||'null')}catch{return null}})
  const [page, setPage] = useState('Dashboard')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(Boolean(localStorage.getItem('admitflow-token')))
  const [error, setError] = useState('')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(()=>localStorage.getItem('admitflow-sidebar')==='collapsed')
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [assistantQuestion, setAssistantQuestion] = useState('')
  const [assistantAnswer, setAssistantAnswer] = useState(null)
  const [assistantError, setAssistantError] = useState('')
  const [assistantLoading, setAssistantLoading] = useState(false)
  const [assistantScenario, setAssistantScenario] = useState(null)
  const [commandOpen, setCommandOpen] = useState(false)
  const [commandQuery, setCommandQuery] = useState('')
  const [popover, setPopover] = useState('')
  const [scenarioInputs, setScenarioInputs] = useState({ application_volume: 5000, submitted: 1.05, admitted: 1.08, enrolled: 1.04 })
  const [scenarioRunning, setScenarioRunning] = useState(false)
  const [selectedProgramme, setSelectedProgramme] = useState(null)

  useEffect(()=>{
    document.documentElement.dataset.theme=theme
    localStorage.setItem('admitflow-theme',theme)
  },[theme])

  useEffect(()=>{
    localStorage.setItem('admitflow-sidebar',sidebarCollapsed?'collapsed':'expanded')
  },[sidebarCollapsed])

  function clearStoredSession() {
    localStorage.removeItem('admitflow-token')
    localStorage.removeItem('admitflow-user')
    setToken('')
    setUser(null)
    setData(null)
    setPage('Dashboard')
    setPopover('')
  }

  async function loadData() {
    try {
      const [dashboard,funnel,cohorts,programme,attribution,forecast,scenario,model,audit,cycle,assistantStatus] = await Promise.all([
        fetchJson('/api/dashboard'),fetchJson('/api/funnel'),fetchJson('/api/cohorts'),fetchJson('/api/programmes'),
        fetchJson('/api/attribution'),fetchJson('/api/forecast'),fetchJson('/api/scenarios'),fetchJson('/api/model'),
        fetchJson('/api/audit'),fetchJson('/api/cycle'),fetchJson('/api/assistant/status'),
      ])
      setData({dashboard,funnel,cohorts,programme,attribution,forecast,scenario,model,audit,cycle,assistantStatus,updatedAt:new Intl.DateTimeFormat(undefined,{hour:'numeric',minute:'2-digit'}).format(new Date())})
      setError('')
    } catch (requestError) {
      const detail = requestError.message || ''
      if (detail === 'Invalid token' || detail === 'Missing token' || /invalid token|missing token|unauthorized/i.test(detail)) {
        clearStoredSession()
        setError('Your session expired. Please sign in again.')
        return
      }
      setData(null)
      setError(detail || 'Analytics could not be loaded. Check the API connection and retry.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(()=>{
    if(!token)return undefined
    const request=window.setTimeout(()=>void loadData(),0)
    return ()=>window.clearTimeout(request)
  },[token])

  async function submitLogin(credentials) {
    setLoading(true)
    setError('')
    try {
      const result=await fetchJson('/auth/login',{method:'POST',body:JSON.stringify(credentials)})
      localStorage.setItem('admitflow-token',result.token)
      localStorage.setItem('admitflow-user',JSON.stringify(result.user))
      setUser(result.user)
      setToken(result.token)
    } catch (requestError) {
      setError(requestError.message||'Authentication failed. Check your email and password.')
      setLoading(false)
    }
  }

  async function useDemoAccess() {
    await submitLogin({email:'admin@admitflow.local',password:'admin123'})
  }

  async function logout() {
    try { if(token) await fetchJson(`/auth/logout?token=${encodeURIComponent(token)}`,{method:'POST'}) } catch { /* Local sign-out still clears expired credentials. */ }
    clearStoredSession()
  }

  async function runScenario() {
    setScenarioRunning(true)
    setError('')
    try {
      const scenario=await fetchJson('/api/scenarios/run',{method:'POST',body:JSON.stringify({application_volume:Number(scenarioInputs.application_volume),stage_adjustments:{submitted:Number(scenarioInputs.submitted),admitted:Number(scenarioInputs.admitted),enrolled:Number(scenarioInputs.enrolled)}})})
      setData((current)=>({...current,scenario}))
      setScenarioRunning(false)
      return scenario
    } catch(requestError) {
      setError(`Scenario could not be calculated. ${requestError.message}`)
      setScenarioRunning(false)
      return null
    }
  }

  function openAssistant(question='',scenario=null) {
    setAssistantOpen(true)
    setPopover('')
    setAssistantQuestion(question)
    setAssistantScenario(scenario)
    setAssistantAnswer(null)
    setAssistantError('')
    if(question.trim()) void askAssistant(question,scenario)
  }

  async function askAssistant(question=assistantQuestion,scenario=assistantScenario) {
    const trimmed=question.trim()
    setAssistantOpen(true)
    setAssistantQuestion(trimmed)
    setAssistantAnswer(null)
    setAssistantError('')
    if(trimmed.length<3)return
    if(!data?.assistantStatus.configured){setAssistantError('Live AI is offline because GROQ_API_KEY is not configured on the backend. Your question was not sent.');return}
    setAssistantLoading(true)
    try {
      const answer=await fetchJson('/api/assistant',{method:'POST',body:JSON.stringify({question:trimmed,...(scenario?{scenario}:{})})})
      setAssistantAnswer(answer)
      setData((current)=>({...current,audit:[...current.audit,{action:'assistant_question',status:'success',timestamp:new Date().toISOString()}]}))
    } catch(requestError) {
      setAssistantError(requestError.message||'The assistant could not retrieve an answer.')
    } finally {
      setAssistantLoading(false)
    }
  }

  useEffect(()=>{
    function onKeyDown(event) {
      if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='k'){
        event.preventDefault()
        setCommandOpen((current)=>!current)
        setCommandQuery('')
      }
      if(event.key==='Escape'){
        setCommandOpen(false)
        setAssistantOpen(false)
        setPopover('')
        setMobileSidebarOpen(false)
        setSelectedProgramme(null)
      }
    }
    window.addEventListener('keydown',onKeyDown)
    return ()=>window.removeEventListener('keydown',onKeyDown)
  },[])

  function navigate(nextPage) {
    setPage(nextPage)
    setPopover('')
  }

  const context=pageContext[page]||pageContext.Dashboard
  const setSelectedProgrammeFromSearch=(name)=>setSelectedProgramme(data?.programme.find((row)=>row.programme===name)||null)

  if(!token)return <LoginPage onLogin={submitLogin} onUseDemo={useDemoAccess} loading={loading} error={error} theme={theme} onToggleTheme={()=>setTheme((value)=>value==='dark'?'light':'dark')}/>

  return <div className={`app-frame ${sidebarCollapsed?'sidebar-compact':''} ${mobileSidebarOpen?'mobile-sidebar-open':''}`}>
    {mobileSidebarOpen&&<button className="mobile-sidebar-scrim" type="button" onClick={()=>setMobileSidebarOpen(false)} aria-label="Close navigation"/>}
    <Sidebar activePage={page} onNavigate={navigate} collapsed={sidebarCollapsed} onToggle={()=>setSidebarCollapsed((value)=>!value)} onAskAI={()=>openAssistant()} onOpenSettings={()=>navigate('Settings')} onCloseMobile={()=>setMobileSidebarOpen(false)} user={user}/>
    <div className="workspace-shell">
      <header className="workspace-topbar">
        <div className="topbar-title-group"><button className="icon-button mobile-menu-button" type="button" onClick={()=>setMobileSidebarOpen(true)} aria-label="Open navigation"><Menu size={19}/></button><div><div className="breadcrumb"><span>AdmitFlow</span><span>/</span><span>{context[0]}</span></div><h1>{page==='Programmes'?'Programme performance':page==='Dashboard'?'Admission intelligence':page==='Scenario'?'Scenario lab':page==='Forecast'?'Admission forecast':page}</h1></div></div>
        <div className="workspace-topbar-actions"><button className="global-search-button" type="button" onClick={()=>{setCommandOpen(true);setCommandQuery('')}} aria-label="Search AdmitFlow"><Search size={16}/><span>Search anything</span><kbd>⌘ K</kbd></button><button className="topbar-ai-button" type="button" onClick={()=>openAssistant()}><Sparkles size={15}/><span>Ask AI</span></button><span className="topbar-separator"/><button className="icon-button topbar-icon" type="button" onClick={()=>setPopover((value)=>value==='notifications'?'':'notifications')} aria-label="Notifications" title="Notifications"><Bell size={17}/>{(data?.audit?.length||0)>0&&<i className="notification-indicator"/>}</button><button className="icon-button topbar-icon" type="button" onClick={()=>setTheme((value)=>value==='dark'?'light':'dark')} aria-label={`Switch to ${theme==='dark'?'light':'dark'} theme`} title={`Switch to ${theme==='dark'?'light':'dark'} theme`}>{theme==='dark'?<Sun size={17}/>:<Moon size={17}/>}</button><button className="profile-menu-button" type="button" onClick={()=>setPopover((value)=>value==='user'?'':'user')} aria-label="Open user profile"><span className="profile-avatar">{userInitials(user)}</span><ChevronDown size={14}/></button></div>
        {popover==='notifications'&&<NotificationsPopover audit={data.audit} onClose={()=>setPopover('')}/>}{popover==='user'&&<UserPopover user={user} onLogout={logout} onClose={()=>setPopover('')}/>}
      </header>
      <main className="workspace-content" id="main-content">
        {error&&data&&<div className="toast-message" role="alert">{error}<button type="button" onClick={()=>setError('')} aria-label="Dismiss message"><X size={14}/></button></div>}
        {!data&&loading&&<LoadingWorkspace/>}
        {!data&&!loading&&<div className="api-error-state" role="alert"><div className="error-state-icon"><CircleUserRound size={22}/></div><h2>Workspace unavailable</h2><p>{error||'Analytics could not be loaded. Check that the API is running.'}</p><button className="primary-button" type="button" onClick={()=>{setLoading(true);void loadData()}}>Retry connection <ArrowRight size={15}/></button></div>}
        {data&&<div key={page} className="page-transition">{page==='Dashboard'&&<DashboardPage data={data} onNavigate={navigate} onAskAI={openAssistant} onSelectProgramme={setSelectedProgramme}/>}{page==='Funnel'&&<FunnelPage data={data} onAskAI={openAssistant}/ >}{page==='Cohorts'&&<CohortsPage data={data}/ >}{page==='Programmes'&&<ProgrammesPage data={data} onSelectProgramme={setSelectedProgramme}/>}{page==='Attribution'&&<AttributionPage data={data} onAskAI={openAssistant}/>}{page==='Forecast'&&<ForecastPage data={data} onAskAI={openAssistant}/>}{page==='Scenario'&&<ScenarioPage data={data} inputs={scenarioInputs} setInputs={setScenarioInputs} onRun={runScenario} running={scenarioRunning} onAskAI={openAssistant}/>}{page==='Model'&&<ModelPage data={data} onAskAI={openAssistant}/>}{page==='Audit'&&<AuditPage data={data}/>}{page==='Settings'&&<SettingsPage data={data} theme={theme} onTheme={()=>setTheme((value)=>value==='dark'?'light':'dark')} collapsed={sidebarCollapsed} onToggleSidebar={()=>setSidebarCollapsed((value)=>!value)} user={user}/>}</div>}
      </main>
      <footer className="workspace-footer"><span>ADMITFLOW <i/> ADMISSION INTELLIGENCE</span><span><span className="mini-live"/> API connected <b>·</b> Updated {data?.updatedAt||'—'}</span></footer>
    </div>
    {data&&<button className="floating-ai-button" type="button" onClick={()=>openAssistant()} aria-label="Ask AdmitFlow AI" aria-keyshortcuts="Control+K Meta+K"><span><Sparkles size={17}/></span><strong>Ask AdmitFlow</strong><kbd>⌘K</kbd></button>}
    {assistantOpen&&<AssistantPanel configured={Boolean(data?.assistantStatus.configured)} question={assistantQuestion} setQuestion={setAssistantQuestion} answer={assistantAnswer} loading={assistantLoading} error={assistantError} onAsk={askAssistant} onClose={()=>setAssistantOpen(false)}/>}
    {commandOpen&&<CommandPalette query={commandQuery} setQuery={setCommandQuery} data={data} onNavigate={navigate} onAskAI={()=>openAssistant()} onClose={()=>setCommandOpen(false)} onSelectProgramme={setSelectedProgrammeFromSearch}/>}
    {selectedProgramme&&<ProgrammeDrawer programme={selectedProgramme} onClose={()=>setSelectedProgramme(null)}/>}
  </div>
}
