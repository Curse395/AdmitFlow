import {
  Activity,
  BarChart3,
  BrainCircuit,
  ChevronLeft,
  Compass,
  FlaskConical,
  GraduationCap,
  LayoutDashboard,
  Megaphone,
  PanelLeftClose,
  PanelLeftOpen,
  Settings2,
  Sparkles,
  UsersRound,
} from 'lucide-react'

const groups = [
  { label: 'Overview', items: [{ label: 'Dashboard', icon: LayoutDashboard }] },
  {
    label: 'Analytics',
    items: [
      { label: 'Funnel', icon: Activity },
      { label: 'Cohorts', icon: UsersRound },
      { label: 'Programmes', icon: GraduationCap },
      { label: 'Attribution', icon: Megaphone },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { label: 'Forecast', icon: Compass },
      { label: 'Scenario', icon: FlaskConical },
      { label: 'Model', icon: BrainCircuit },
    ],
  },
  { label: 'System', items: [{ label: 'Audit', icon: BarChart3 }] },
]

export default function Sidebar({ activePage, onNavigate, collapsed, onToggle, onAskAI, onOpenSettings, onCloseMobile, user }) {
  const email = user?.email || 'Admissions admin'
  const initials = email.split('@')[0].split(/[._-]/).map((part) => part[0]).join('').slice(0, 2).toUpperCase()
  return (
    <aside className={`sidebar ${collapsed ? 'is-collapsed' : ''}`} aria-label="Application sidebar">
      <div className="sidebar-brand-row">
        <button className="brand-lockup" type="button" onClick={() => onNavigate('Dashboard')} aria-label="AdmitFlow dashboard">
          <span className="brand-symbol" aria-hidden="true"><span /><span /><span /></span>
          {!collapsed && <span className="brand-name">Admit<span>Flow</span></span>}
        </button>
        <button className="icon-button sidebar-collapse" type="button" onClick={onToggle} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          {collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
        </button>
      </div>

      <div className="workspace-switcher">
        <span className="workspace-mark">AF</span>
        {!collapsed && <><span className="workspace-name">Admissions workspace</span><ChevronLeft className="workspace-chevron" size={14} /></>}
      </div>

      <nav className="sidebar-nav" aria-label="Primary navigation">
        {groups.map((group) => (
          <section className="nav-group" key={group.label}>
            {!collapsed && <h2>{group.label}</h2>}
            {group.items.map(({ label, icon: Icon }) => (
              <button
                className={`nav-item ${activePage === label ? 'is-active' : ''}`}
                key={label}
                type="button"
                onClick={() => { onNavigate(label); onCloseMobile() }}
                aria-label={label}
                aria-current={activePage === label ? 'page' : undefined}
                title={collapsed ? label : undefined}
              >
                <Icon size={18} strokeWidth={1.8} />
                {!collapsed && <span>{label}</span>}
                {activePage === label && <span className="nav-active-marker" aria-hidden="true" />}
              </button>
            ))}
          </section>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <button className="assistant-rail-button" type="button" onClick={onAskAI} title={collapsed ? 'Ask AdmitFlow' : undefined} aria-label="Ask AdmitFlow AI">
          <Sparkles size={17} />
          {!collapsed && <><span>Ask AdmitFlow</span><kbd>⌘ K</kbd></>}
        </button>
        <button className={`nav-item ${activePage === 'Settings' ? 'is-active' : ''}`} type="button" onClick={() => { onOpenSettings(); onCloseMobile() }} aria-label="Settings" title={collapsed ? 'Settings' : undefined}>
          <Settings2 size={18} strokeWidth={1.8} />
          {!collapsed && <span>Settings</span>}
        </button>
        <div className="sidebar-profile">
          <span className="profile-avatar">{initials || 'AA'}</span>
          {!collapsed && <div className="profile-copy"><strong>{email}</strong><span>{user?.role || 'Workspace admin'}</span></div>}
          {!collapsed && <span className="profile-status" title="Signed in" />}
        </div>
      </div>
    </aside>
  )
}
