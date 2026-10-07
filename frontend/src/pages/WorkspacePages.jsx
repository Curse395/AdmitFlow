import { useState } from 'react'
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3, BrainCircuit, Check, ChevronDown,
  CircleHelp, Database, Eye, Filter, FlaskConical, Gauge, GraduationCap, Info, Layers3, Sparkles,
  Target, TrendingDown, UsersRound, X,
} from 'lucide-react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, ComposedChart, Line, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

const colors = ['#8b7bff', '#44d8c3', '#ffcf70', '#5aa7ff', '#ff7e8c', '#b8e79a']
const number = (value) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Number(value || 0))
const percent = (value, digits = 1) => `${(Number(value || 0) * 100).toFixed(digits)}%`
const rate = (value, digits = 1) => `${Number(value || 0).toFixed(digits)}%`
const percentageDelta = (value) => `${Number(value || 0).toFixed(1)}%`
const TooltipBox = (props) => <Tooltip {...props} contentStyle={{ background: '#151b2b', border: '1px solid rgba(173, 185, 219, .18)', borderRadius: 10, color: '#f3f5ff', fontSize: 12, boxShadow: '0 12px 40px rgba(0,0,0,.28)' }} labelStyle={{ color: '#aab4d0', marginBottom: 5 }} />
const latest = (rows) => rows?.[rows.length - 1]
const primaryFunnelDrop = (funnel) => {
  const stages = funnel?.stage_summary || []
  return stages.slice(1).reduce((largest, stage, index) => {
    const previous = stages[index]
    const loss = previous.volume - stage.volume
    return loss > largest.loss ? { from: previous.stage, to: stage.stage, loss, previous: previous.volume } : largest
  }, { from: '', to: '', loss: 0, previous: 1 })
}

function PageHeading({ eyebrow, title, description, actions }) {
  return <header className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2>{description && <p className="page-description">{description}</p>}</div>{actions && <div className="page-heading-actions">{actions}</div>}</header>
}

function Sparkline({ values, color = '#8b7bff' }) {
  const data = (values || []).map((value, index) => ({ index, value }))
  if (data.length < 2) return <span className="sparkline-empty" aria-label="No historical trend available" />
  return <div className="sparkline" aria-hidden="true"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data}><Area type="monotone" dataKey="value" stroke={color} fill={color} fillOpacity={0.13} strokeWidth={1.8} isAnimationActive animationDuration={700} /></AreaChart></ResponsiveContainer></div>
}

function MetricCard({ label, value, context, values, icon: Icon, tone = 'violet', suffix = '' }) {
  return <article className={`metric-card tone-${tone}`}>
    <div className="metric-card-top"><span>{label}</span><span className="metric-icon"><Icon size={16} /></span></div>
    <div className="metric-card-value">{value}{suffix && <small>{suffix}</small>}</div>
    <div className="metric-card-bottom"><span>{context}</span><Sparkline values={values} color={tone === 'teal' ? '#44d8c3' : tone === 'amber' ? '#ffcf70' : tone === 'blue' ? '#5aa7ff' : '#8b7bff'} /></div>
  </article>
}

function StageFunnel({ funnel, large = false, onSelect }) {
  const stages = funnel?.stage_summary || []
  const maximum = stages[0]?.volume || 1
  return <div className={`stage-funnel ${large ? 'is-large' : ''}`}>
    {stages.map((stage, index) => {
      const previous = stages[index - 1]
      const lost = previous ? previous.volume - stage.volume : 0
      const drop = previous?.volume ? lost / previous.volume : 0
      return <button className="funnel-stage" key={stage.stage} type="button" onClick={() => onSelect?.(stage)} style={{ '--stage-width': `${Math.max(28, (stage.volume / maximum) * 100)}%`, '--stage-delay': `${index * 70}ms` }}>
        <span className="funnel-stage-meta"><span className="funnel-stage-index">0{index + 1}</span><strong>{stage.stage}</strong><span>{percent(stage.conversion_rate, 1)} of applicants</span></span>
        <span className="funnel-stage-track"><i /></span>
        <span className="funnel-stage-volume">{number(stage.volume)}</span>
          <span className="funnel-stage-detail"><b>{previous ? percent(stage.from_previous_stage) : '100%'}</b><small>{previous ? 'stage conversion' : 'starting volume'}</small></span>
        <span className={`funnel-stage-drop ${drop > 0.25 ? 'is-high' : ''}`}>{previous ? <><TrendingDown size={13} /> {number(lost)} <small>drop</small></> : <span>Lead base</span>}</span>
      </button>
    })}
    {!stages.length && <div className="empty-state">Funnel data is not available.</div>}
  </div>
}

function DataSignal({ label = 'Data signal', title, body, action, onClick, icon: Icon = Sparkles }) {
  return <article className="signal-card"><div className="signal-card-icon"><Icon size={17} /></div><div className="signal-card-content"><div className="signal-label">{label}</div><h3>{title}</h3><p>{body}</p>{action && <button className="text-action" type="button" onClick={onClick}>{action}<ArrowRight size={14} /></button>}</div></article>
}

function ProgrammeTable({ rows, onSelect, compact = false }) {
  const [sort, setSort] = useState('applications')
  const [direction, setDirection] = useState(-1)
  const [filter, setFilter] = useState('')
  const sorted = [...(rows || [])].filter((row) => row.programme.toLowerCase().includes(filter.toLowerCase())).sort((a, b) => {
    const left = a[sort] ?? 0
    const right = b[sort] ?? 0
    return (typeof left === 'string' ? left.localeCompare(right) : left - right) * direction
  })
  const changeSort = (key) => { if (sort === key) setDirection((value) => -value); else { setSort(key); setDirection(-1) } }
  return <>
    {!compact && <label className="search-field programme-filter"><Filter size={15} /><span className="sr-only">Filter programmes</span><input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Filter programmes" /></label>}
    <div className="table-scroll"><table className="data-table programme-table"><thead><tr><th>Programme</th><th><button type="button" onClick={() => changeSort('applications')}>Applications <ChevronDown size={12} /></button></th><th><button type="button" onClick={() => changeSort('admissions')}>Admissions <ChevronDown size={12} /></button></th><th><button type="button" onClick={() => changeSort('enrolments')}>Enrolments <ChevronDown size={12} /></button></th><th><button type="button" onClick={() => changeSort('enrolment_rate')}>Enrolment rate <ChevronDown size={12} /></button></th><th>Trend</th></tr></thead>
      <tbody>{sorted.slice(0, compact ? 5 : undefined).map((row, index) => <tr key={row.programme} onClick={() => onSelect(row)} tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter') onSelect(row) }}>
        <td><span className="programme-name"><i style={{ '--swatch': colors[index % colors.length] }} />{row.programme}</span></td><td>{number(row.applications)}</td><td>{number(row.admissions)}</td><td>{number(row.enrolments)}</td><td><span className="rate-value">{percent(row.enrolment_rate)}</span></td><td><Sparkline values={row.trend?.map((point) => point.applications)} color={colors[index % colors.length]} /></td>
      </tr>)}</tbody>
    </table>{!sorted.length && <div className="empty-state">No programmes match this filter.</div>}</div>
  </>
}

export function DashboardPage({ data, onNavigate, onAskAI, onSelectProgramme }) {
  const drop = primaryFunnelDrop(data.funnel)
  const cycle = latest(data.cycle)
  const submitted = data.funnel.stage_summary.find((stage) => stage.stage === 'submitted')
  const cards = [
    { label: 'Applications', value: number(data.dashboard.applications), context: 'All applicant records', values: data.cycle.map((row) => row.applications), icon: UsersRound, tone: 'violet' },
    { label: 'Submitted', value: number(submitted?.volume), context: `${percent(submitted?.conversion_rate)} of applicant records`, values: [], icon: Check, tone: 'teal' },
    { label: 'Admissions', value: number(data.dashboard.admissions), context: `${rate(data.dashboard.admission_rate)} overall`, values: data.cycle.map((row) => row.admissions), icon: GraduationCap, tone: 'blue' },
    { label: 'Enrolments', value: number(data.dashboard.enrolments), context: `${rate(data.dashboard.enrolment_rate)} overall`, values: data.cycle.map((row) => row.enrolments), icon: Target, tone: 'amber' },
    { label: 'Conversion', value: rate(data.dashboard.overall_conversion), context: 'Lead to enrolled', values: data.cycle.map((row) => row.enrolment_rate * 100), icon: Gauge, tone: 'violet' },
  ]
  return <div className="page-stack">
    <section className="executive-hero">
      <div className="executive-copy"><div className="hero-kicker"><span className="live-dot" /> ADMISSION INTELLIGENCE <span className="hero-divider">/</span> OVERVIEW</div><h1>Admissions, <em>in focus.</em></h1><p>Monitor the funnel, understand segment performance, and plan with a clearer view of enrolment.</p><div className="hero-meta"><span><span className="mini-live" /> Data connected</span><span>Latest cycle <strong>{cycle?.cycle_year ?? '—'}</strong></span><span>{data.cycle.length} observed cycles</span></div></div>
      <div className="executive-aside"><span className="aside-overline">CURRENT DATASET</span><strong>{number(data.dashboard.applicants)}</strong><span>synthetic applicant records</span><div className="aside-rule" /><span className="updated-time">Updated {data.updatedAt}</span></div>
    </section>

    <section className="metric-grid" aria-label="Executive metrics">{cards.map((card) => <MetricCard key={card.label} {...card} />)}</section>

    <section className="dashboard-main-grid">
      <article className="surface-panel funnel-panel">
        <div className="panel-header"><div><span className="section-overline">01 / CONVERSION FLOW</span><h2>Admission funnel</h2><p>Stage volume and conversion are calculated from cumulative applicant flags.</p></div><button className="icon-button" type="button" aria-label="Open funnel analytics" onClick={() => onNavigate('Funnel')}><ArrowRight size={17} /></button></div>
        <StageFunnel funnel={data.funnel} onSelect={(stage) => onAskAI(`Explain the ${stage.stage} stage using the admission funnel data.`)} />
        <button className="panel-footer-link" type="button" onClick={() => onNavigate('Funnel')}>Open funnel workspace <ArrowRight size={14} /></button>
      </article>
      <div className="dashboard-right-column">
        <DataSignal label="Observed signal" title={`${drop.from} to ${drop.to} has the largest volume loss`} body={`${number(drop.loss)} records do not continue to the next stage (${percent(drop.loss / Math.max(drop.previous, 1))} of the prior stage). This is descriptive, not causal.`} action="Investigate with AI" onClick={() => onAskAI(`Why is the largest observed funnel loss between ${drop.from} and ${drop.to}? Use the available data and distinguish facts from possible explanations.`)} icon={TrendingDown} />
        <article className="surface-panel mini-forecast-panel"><div className="panel-header"><div><span className="section-overline">02 / OUTLOOK</span><h2>Forecast trajectory</h2></div><button className="icon-button" type="button" aria-label="Open forecast" onClick={() => onNavigate('Forecast')}><ArrowRight size={17} /></button></div>
          <div className="mini-forecast-value"><strong>{number(data.forecast.horizons.H1)}</strong><span>H1 projected enrolments</span></div>
          <div className="mini-forecast-chart"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={[...data.forecast.series.map((row) => ({ year: row.cycle_year, historical: row.enrolments })), ...data.forecast.future_series.map((row) => ({ year: row.cycle_year, forecast: row.enrolments }))]}><CartesianGrid strokeDasharray="3 5" vertical={false} /><XAxis dataKey="year" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} /><YAxis hide /><TooltipBox /><Line type="monotone" dataKey="historical" stroke="#44d8c3" strokeWidth={2.4} dot={false} connectNulls isAnimationActive /><Line type="monotone" dataKey="forecast" stroke="#8b7bff" strokeWidth={2.4} strokeDasharray="5 4" dot={false} connectNulls isAnimationActive /></ComposedChart></ResponsiveContainer></div>
          <div className="chart-legend"><span><i className="legend-mark historical" /> Historical</span><span><i className="legend-mark forecast" /> Projection</span></div>
        </article>
      </div>
    </section>

    <section className="surface-panel programme-preview"><div className="panel-header"><div><span className="section-overline">03 / PROGRAMME MIX</span><h2>Programme performance</h2><p>Compare applications, offers, enrolments, and observed cycle-level volume.</p></div><button className="secondary-button" type="button" onClick={() => onNavigate('Programmes')}>Explore programmes <ArrowRight size={15} /></button></div><ProgrammeTable rows={data.programme} onSelect={onSelectProgramme} compact /></section>
  </div>
}

export function FunnelPage({ data, onAskAI }) {
  const drop = primaryFunnelDrop(data.funnel)
  return <div className="page-stack"><PageHeading eyebrow="ANALYTICS / FUNNEL" title="Funnel intelligence" description="Inspect every transition from lead through enrolment. Stage counts are cumulative and use the dataset's explicit outcome flags." actions={<button className="secondary-button" onClick={() => onAskAI('Which stage has the largest drop-off? Summarize the observed funnel and avoid causal claims.')}><Sparkles size={15} /> Investigate with AI</button>} />
    <section className="metric-grid three-metrics"><MetricCard label="Lead volume" value={number(data.funnel.baseline_applications)} context="Starting population" values={[]} icon={UsersRound} /><MetricCard label="Enrolled" value={number(data.funnel.enrolled)} context={`${rate(data.funnel.overall_conversion)} lead-to-enrolled`} values={[]} icon={GraduationCap} tone="teal" /><MetricCard label="Largest transition loss" value={number(drop.loss)} context={`${drop.from} → ${drop.to}`} values={[]} icon={TrendingDown} tone="amber" /></section>
    <section className="surface-panel"><div className="panel-header"><div><span className="section-overline">STAGE-BY-STAGE</span><h2>Conversion path</h2><p>Hover or focus a stage for its counts; select it to ask a grounded question.</p></div><span className="context-badge"><Database size={13} /> Live dataset</span></div><StageFunnel funnel={data.funnel} large onSelect={(stage) => onAskAI(`Explain the ${stage.stage} stage using the admission funnel data.`)} /></section>
    <div className="insight-grid"><DataSignal label="Funnel signal" title={`Largest loss: ${drop.from} to ${drop.to}`} body={`${number(drop.loss)} records, or ${percent(drop.loss / Math.max(drop.previous, 1))} of the previous stage. This identifies where volume changes, not why.`} action="Ask why this stage is underperforming" onClick={() => onAskAI(`Why might the observed loss between ${drop.from} and ${drop.to} be occurring? Separate measured facts from hypotheses.`)} icon={Activity} /><article className="surface-panel transition-table-panel"><div className="panel-header"><div><span className="section-overline">TRANSITION DETAIL</span><h2>Stage conversion</h2></div></div><div className="table-scroll"><table className="data-table"><thead><tr><th>Stage</th><th>Volume</th><th>Of leads</th><th>Stage conversion</th><th>Drop-off</th></tr></thead><tbody>{data.funnel.stage_summary.map((stage,index) => {const prior=data.funnel.stage_summary[index-1]; const lost=prior?prior.volume-stage.volume:0; return <tr key={stage.stage}><td>{stage.stage}</td><td>{number(stage.volume)}</td><td>{percent(stage.conversion_rate)}</td><td>{prior?percent(stage.from_previous_stage):'—'}</td><td>{prior?`${number(lost)} (${percent(lost/Math.max(prior.volume,1))})`:'—'}</td></tr>})}</tbody></table></div></article></div>
  </div>
}

export function CohortsPage({ data }) {
  const [dimension, setDimension] = useState('cycle')
  const keys = { cycle: 'cycle', region: 'region', programme: 'programme', campaign_source: 'campaign_source', selectivity: 'selectivity' }
  const labels = { cycle: 'Cycle year', region: 'Region', programme: 'Programme', campaign_source: 'Campaign source', selectivity: 'Selectivity' }
  const rows = data.cohorts[keys[dimension]] || []
  const axis = dimension === 'cycle' ? 'cycle_year' : dimension
  return <div className="page-stack"><PageHeading eyebrow="ANALYTICS / COHORTS" title="Cohort explorer" description="Compare applicant volume and conversion across observed cycles and segments." actions={<label className="select-field"><span>Compare by</span><select value={dimension} onChange={(event) => setDimension(event.target.value)}>{Object.entries(labels).map(([key,label]) => <option value={key} key={key}>{label}</option>)}</select><ChevronDown size={14} /></label>} />
    <section className="cohort-summary-grid">{rows.slice(0,3).map((row,index) => <article className="surface-panel cohort-highlight" key={row[axis]}><span className="cohort-rank">0{index+1}</span><span className="section-overline">{labels[dimension]}</span><h3>{row[axis]}</h3><strong>{number(row.applicants)}</strong><span>applicants</span><div className="cohort-rates"><span>Admission <b>{percent(row.admission_rate)}</b></span><span>Enrolment <b>{percent(row.enrolment_rate)}</b></span></div></article>)}</section>
    <section className="surface-panel"><div className="panel-header"><div><span className="section-overline">SEGMENT COMPARISON</span><h2>{labels[dimension]} outcomes</h2><p>Rates are calculated against each cohort's applicant count.</p></div></div><div className="cohort-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={rows} margin={{ top: 10, right: 12, bottom: 0, left: 0 }}><CartesianGrid strokeDasharray="3 5" vertical={false} /><XAxis dataKey={axis} tickLine={false} axisLine={false} tick={{ fontSize: 11 }} /><YAxis tickFormatter={(value) => `${Math.round(value*100)}%`} tickLine={false} axisLine={false} /><TooltipBox formatter={(value) => percent(value)} /><Bar dataKey="admission_rate" name="Admission rate" fill="#8b7bff" radius={[5,5,0,0]} isAnimationActive animationDuration={550} /><Bar dataKey="enrolment_rate" name="Enrolment rate" fill="#44d8c3" radius={[5,5,0,0]} isAnimationActive animationDuration={650} /></BarChart></ResponsiveContainer></div><div className="chart-legend"><span><i className="legend-mark admission" /> Admission rate</span><span><i className="legend-mark enrolled" /> Enrolment rate</span></div><div className="table-scroll"><table className="data-table"><thead><tr><th>{labels[dimension]}</th><th>Applicants</th><th>Admissions</th><th>Enrolments</th><th>Admission rate</th><th>Enrolment rate</th><th>Sample</th></tr></thead><tbody>{rows.map((row) => <tr key={row[axis]}><td>{row[axis]}</td><td>{number(row.applicants)}</td><td>{number(row.admissions)}</td><td>{number(row.enrolments)}</td><td>{percent(row.admission_rate)}</td><td>{percent(row.enrolment_rate)}</td><td><span className="status-badge">{row.sample_sufficiency || 'Observed'}</span></td></tr>)}</tbody></table></div></section>
  </div>
}

export function ProgrammesPage({ data, onSelectProgramme }) {
  const max = Math.max(...data.programme.map((row) => row.applications), 1)
  return <div className="page-stack"><PageHeading eyebrow="ANALYTICS / PROGRAMMES" title="Programme performance" description="Explore how application volume moves through each programme. Select a row to inspect its cycle history." />
    <section className="surface-panel programme-chart-panel"><div className="panel-header"><div><span className="section-overline">APPLICATION VOLUME</span><h2>Programme mix</h2></div><span className="context-badge">{data.cycle.length} cycles observed</span></div><div className="programme-bars">{data.programme.map((row,index) => <button className="programme-bar-row" type="button" key={row.programme} onClick={() => onSelectProgramme(row)}><span className="programme-bar-label"><i style={{'--swatch':colors[index%colors.length]}} />{row.programme}</span><span className="programme-bar-track"><i style={{width:`${(row.applications/max)*100}%`,'--swatch':colors[index%colors.length]}} /></span><strong>{number(row.applications)}</strong><span className="programme-bar-rate">{percent(row.enrolment_rate)} enrolled</span></button>)}</div></section>
    <section className="surface-panel"><div className="panel-header"><div><span className="section-overline">PERFORMANCE DETAIL</span><h2>Compare programmes</h2><p>Select a metric header to sort. Programme rows open a detail drawer.</p></div></div><ProgrammeTable rows={data.programme} onSelect={onSelectProgramme} /></section>
  </div>
}

export function ProgrammeDrawer({ programme, onClose }) {
  if (!programme) return null
  const trend = programme.trend || []
  return <div className="drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><aside className="detail-drawer" role="dialog" aria-modal="true" aria-labelledby="programme-detail-title"><header className="drawer-header"><div><span className="section-overline">PROGRAMME PROFILE</span><h2 id="programme-detail-title">{programme.programme}</h2></div><button className="icon-button" type="button" onClick={onClose} aria-label="Close programme detail"><X size={18} /></button></header><div className="drawer-metric-row"><div><span>Applications</span><strong>{number(programme.applications)}</strong></div><div><span>Admissions</span><strong>{number(programme.admissions)}</strong></div><div><span>Enrolments</span><strong>{number(programme.enrolments)}</strong></div></div><div className="drawer-rate"><span>Enrolment rate</span><strong>{percent(programme.enrolment_rate)}</strong></div><div className="drawer-chart"><div className="panel-header"><div><span className="section-overline">CYCLE TREND</span><h3>Applications by cycle</h3></div></div><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend}><defs><linearGradient id="programmeTrend" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#8b7bff" stopOpacity={0.34}/><stop offset="100%" stopColor="#8b7bff" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 5" vertical={false}/><XAxis dataKey="cycle_year" tickLine={false} axisLine={false}/><YAxis hide/><TooltipBox/><Area type="monotone" dataKey="applications" stroke="#8b7bff" fill="url(#programmeTrend)" strokeWidth={2} isAnimationActive/></AreaChart></ResponsiveContainer></div><p className="drawer-footnote"><Info size={14}/> Observational programme comparisons do not establish why outcomes differ.</p></aside></div>
}

export function AttributionPage({ data, onAskAI }) {
  const [source, setSource] = useState('all')
  const rows = data.attribution.filter((row) => source === 'all' || row.campaign_source === source)
  return <div className="page-stack"><PageHeading eyebrow="ANALYTICS / ATTRIBUTION" title="Campaign attribution" description="Understand how application volume and outcomes are distributed across campaign sources." actions={<button className="secondary-button" type="button" onClick={() => onAskAI('Which campaign source generates the most applications, and how do their descriptive enrolment rates compare?')}><Sparkles size={15}/> Ask AI about sources</button>} />
    <div className="attribution-summary"><div className="attribution-total"><span>Total applications</span><strong>{number(data.dashboard.applications)}</strong><small>across all observed sources</small></div><div className="attribution-insight"><span className="signal-label">SOURCE SIGNAL</span><strong>{data.attribution[0]?.campaign_source || '—'}</strong><span>has the highest application count at {number(data.attribution[0]?.applications)}.</span></div><label className="select-field"><span>Filter source</span><select value={source} onChange={(event) => setSource(event.target.value)}><option value="all">All sources</option>{data.attribution.map((row) => <option key={row.campaign_source}>{row.campaign_source}</option>)}</select><ChevronDown size={14}/></label></div>
    <section className="attribution-grid"><article className="surface-panel"><div className="panel-header"><div><span className="section-overline">APPLICATION DISTRIBUTION</span><h2>Share by source</h2></div></div><div className="attribution-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={rows} layout="vertical" margin={{left:8,right:18,top:8,bottom:8}}><CartesianGrid strokeDasharray="3 5" horizontal={false}/><XAxis type="number" tickFormatter={(v)=>`${Math.round(v*100)}%`} tickLine={false} axisLine={false}/><YAxis type="category" dataKey="campaign_source" width={82} tickLine={false} axisLine={false} tick={{fontSize:11}}/><TooltipBox formatter={(value)=>percent(value)}/><Bar dataKey="share_of_applications" name="Application share" fill="#8b7bff" radius={[0,5,5,0]} isAnimationActive animationDuration={650}/></BarChart></ResponsiveContainer></div></article><article className="surface-panel"><div className="panel-header"><div><span className="section-overline">CONVERSION COMPARISON</span><h2>Observed enrolment rate</h2></div></div><div className="attribution-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={rows} margin={{left:0,right:10,top:8,bottom:5}}><CartesianGrid strokeDasharray="3 5" vertical={false}/><XAxis dataKey="campaign_source" tickLine={false} axisLine={false} tick={{fontSize:10}}/><YAxis tickFormatter={(v)=>`${Math.round(v*100)}%`} tickLine={false} axisLine={false}/><TooltipBox formatter={(value)=>percent(value)}/><Bar dataKey="enrolment_conversion" name="Enrolment rate" fill="#44d8c3" radius={[5,5,0,0]} isAnimationActive animationDuration={700}/></BarChart></ResponsiveContainer></div></article></section>
    <section className="surface-panel"><div className="panel-header"><div><span className="section-overline">SOURCE DETAIL</span><h2>Attribution table</h2></div></div><div className="table-scroll"><table className="data-table"><thead><tr><th>Source</th><th>Applications</th><th>Share</th><th>Admissions</th><th>Admission rate</th><th>Enrolments</th><th>Enrolment rate</th></tr></thead><tbody>{rows.map((row)=> <tr key={row.campaign_source}><td>{row.campaign_source}</td><td>{number(row.applications)}</td><td>{percent(row.share_of_applications)}</td><td>{number(row.admissions)}</td><td>{percent(row.admission_conversion)}</td><td>{number(row.enrolments)}</td><td>{percent(row.enrolment_conversion)}</td></tr>)}</tbody></table></div><p className="causal-disclaimer"><Info size={15}/> Descriptive attribution only; these associations do not establish causal impact.</p></section>
  </div>
}

export function ForecastPage({ data, onAskAI }) {
  const chart = [...data.forecast.series.map((row)=>({year:row.cycle_year,historical:row.enrolments})), ...data.forecast.future_series.map((row)=>({year:row.cycle_year,forecast:row.enrolments}))]
  const h1 = data.forecast.horizons.H1
  const lastActual = latest(data.forecast.series)?.enrolments || 0
  const change = lastActual ? (h1-lastActual)/lastActual : 0
  return <div className="page-stack"><PageHeading eyebrow="INTELLIGENCE / FORECAST" title="Admission forecast" description="Projected enrolment trajectory from the current linear trend. The short history makes these projections directional, not operational." actions={<button className="secondary-button" type="button" onClick={() => onAskAI('Explain the current admission forecast, its horizon values, and the limits of the available history.')}><Sparkles size={15}/> Explain with AI</button>} />
    <section className="forecast-hero"><div className="forecast-hero-copy"><span className="section-overline">NEXT CYCLE / H1</span><div className="forecast-primary-value">{number(h1)}<span>projected enrolments</span></div><div className={`forecast-change ${change>=0?'positive':'negative'}`}>{change>=0?<ArrowUpRight size={15}/>:<ArrowDownRight size={15}/>} {percent(Math.abs(change))} vs last observed cycle <span>descriptive comparison</span></div></div><div className="forecast-hero-meta"><span>Forecast model</span><strong>{data.forecast.model}</strong><span>Observed history</span><strong>{data.forecast.training_years} annual cycles</strong><span>Forecast window</span><strong>{data.forecast.forecast_years[0]}–{data.forecast.forecast_years.at(-1)}</strong></div></section>
    <section className="surface-panel forecast-chart-panel"><div className="panel-header"><div><span className="section-overline">HISTORICAL + PROJECTED</span><h2>Enrolment trajectory</h2><p>Solid line shows observed cycles; dashed line shows the current model extrapolation.</p></div><span className="context-badge"><span className="mini-live"/> Updated from dataset</span></div><div className="forecast-chart"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={chart} margin={{top:15,right:15,left:0,bottom:3}}><defs><linearGradient id="historicalFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#44d8c3" stopOpacity={0.18}/><stop offset="100%" stopColor="#44d8c3" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 5" vertical={false}/><XAxis dataKey="year" tickLine={false} axisLine={false}/><YAxis tickLine={false} axisLine={false}/><ReferenceLine x={latest(data.forecast.series)?.cycle_year} stroke="#71809e" strokeDasharray="4 4"/><TooltipBox/><Area type="monotone" dataKey="historical" name="Historical enrolments" stroke="#44d8c3" fill="url(#historicalFill)" strokeWidth={2.5} connectNulls isAnimationActive animationDuration={700}/><Line type="monotone" dataKey="forecast" name="Projected enrolments" stroke="#9c8fff" strokeWidth={2.5} strokeDasharray="7 5" dot={{r:3,fill:'#9c8fff'}} connectNulls isAnimationActive animationDuration={850}/></ComposedChart></ResponsiveContainer></div><div className="chart-legend"><span><i className="legend-mark historical"/> Historical</span><span><i className="legend-mark forecast"/> Forecast</span><span className="forecast-break-label">Forecast boundary</span></div></section>
    <section className="forecast-bottom-grid"><article className="surface-panel horizon-panel"><div className="panel-header"><div><span className="section-overline">PLANNING HORIZONS</span><h2>Projected enrolments</h2></div></div><div className="horizon-grid">{['H1','H2','H4','H6'].map((horizon,index)=><div className="horizon-card" key={horizon}><span>{horizon}</span><strong>{number(data.forecast.horizons[horizon])}</strong><small>{data.forecast.forecast_years[[0,1,3,5][index]]}</small></div>)}</div></article><article className="surface-panel forecast-error-panel"><div className="panel-header"><div><span className="section-overline">HOLDOUT ERROR</span><h2>Validation metrics</h2></div><span className="context-badge"><Info size={13}/> Secondary</span></div><div className="error-metric-list"><div><span>MAE</span><strong>{data.forecast.metrics.mae}</strong></div><div><span>RMSE</span><strong>{data.forecast.metrics.rmse}</strong></div><div><span>MAPE</span><strong>{percent(data.forecast.metrics.mape)}</strong></div></div><p className="muted-note">Evaluation uses a two-cycle holdout. Only six annual observations are available.</p></article></section>
    <DataSignal label="Forecast interpretation" title="An extrapolation, not a guarantee" body={`H1 projects ${number(h1)} enrolments compared with ${number(lastActual)} in the latest observed cycle. Holdout MAPE is ${percent(data.forecast.metrics.mape)}; the series contains only ${data.forecast.training_years} annual observations.`} action="Ask AI to explain the forecast" onClick={() => onAskAI('Explain the forecast trajectory and holdout error. What can and cannot be inferred from six annual cycles?')} icon={BrainCircuit}/>
  </div>
}

const scenarioPresets = {
  Conservative: { application_volume: 4200, submitted: 0.98, admitted: 0.98, enrolled: 0.98 },
  Expected: { application_volume: 5000, submitted: 1.05, admitted: 1.08, enrolled: 1.04 },
  Growth: { application_volume: 6000, submitted: 1.08, admitted: 1.1, enrolled: 1.12 },
}

export function ScenarioPage({ data, inputs, setInputs, onRun, running, onAskAI }) {
  const result = data.scenario
  const [selectedPreset,setSelectedPreset] = useState('Expected')
  const setField = (field,value) => { setSelectedPreset('Custom'); setInputs((current)=>({...current,[field]:value})) }
  const setPreset = (name) => { setSelectedPreset(name); setInputs(scenarioPresets[name]) }
  const chartRows = ['applications','submitted','admitted','enrolled'].map((key)=>({metric:key[0].toUpperCase()+key.slice(1),baseline:result.baseline[key],scenario:result.scenario[key]}))
  return <div className="page-stack"><PageHeading eyebrow="INTELLIGENCE / SIMULATION" title="Scenario lab" description="Test controlled volume and stage assumptions against the observed baseline. Results are deterministic, not causal forecasts." actions={<span className="context-badge"><span className="mini-live"/> Live simulation</span>} />
    <div className="scenario-workspace"><section className="surface-panel scenario-controls"><div className="panel-header"><div><span className="section-overline">SCENARIO CONTROLS</span><h2>Set assumptions</h2><p>Multipliers apply after scaling the observed funnel to the requested application volume.</p></div></div><div className="preset-row"><span>Presets</span>{Object.keys(scenarioPresets).map((preset)=><button type="button" key={preset} onClick={()=>setPreset(preset)} className={selectedPreset===preset?'is-selected':''}>{preset}</button>)}<button type="button" className={selectedPreset==='Custom'?'is-selected':''} onClick={()=>setSelectedPreset('Custom')}>Custom</button></div>
      <label className="range-field"><span>Application volume <strong>{number(inputs.application_volume)}</strong></span><input type="range" min="0" max="10000" step="100" value={inputs.application_volume} onChange={(event)=>setField('application_volume',Number(event.target.value))}/><span className="range-ends"><small>0</small><small>10,000</small></span></label><label className="number-field">Exact volume<input type="number" min="0" max="10000" step="1" value={inputs.application_volume} onChange={(event)=>setField('application_volume',Number(event.target.value))}/></label>
      <div className="scenario-multipliers">{[['submitted','Submitted'],['admitted','Admitted'],['enrolled','Enrolled']].map(([key,label])=><label className="range-field" key={key}><span>{label} multiplier <strong>{Number(inputs[key]).toFixed(2)}×</strong></span><input type="range" min="0.5" max="1.5" step="0.01" value={inputs[key]} onChange={(event)=>setField(key,Number(event.target.value))}/><span className="range-ends"><small>0.50×</small><small>1.50×</small></span></label>)}</div><button className="primary-button run-scenario-button" type="button" disabled={running} onClick={onRun}>{running?<><span className="button-spinner"/> Calculating scenario</>:<>Run scenario <ArrowRight size={15}/></>}</button>
    </section><section className="surface-panel simulation-results"><div className="panel-header"><div><span className="section-overline">LIVE SIMULATION</span><h2>Baseline to scenario</h2><p>Current output reflects the last successfully run assumptions.</p></div><span className="context-badge"><Activity size={13}/> Deterministic</span></div><div className="simulation-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartRows} margin={{top:15,right:10,left:0,bottom:5}}><CartesianGrid strokeDasharray="3 5" vertical={false}/><XAxis dataKey="metric" tickLine={false} axisLine={false}/><YAxis tickLine={false} axisLine={false}/><TooltipBox/><Bar dataKey="baseline" name="Baseline" fill="#46506a" radius={[4,4,0,0]} isAnimationActive animationDuration={450}/><Bar dataKey="scenario" name="Scenario" fill="#8b7bff" radius={[4,4,0,0]} isAnimationActive animationDuration={650}/></BarChart></ResponsiveContainer></div><div className="simulation-delta-list">{chartRows.map((row)=>{const key=row.metric.toLowerCase();const delta=result.difference[key];const change=result.percentage_change[key];return <div key={key}><span>{row.metric}</span><span>{number(row.baseline)} <ArrowRight size={13}/> <strong>{number(row.scenario)}</strong></span><b className={delta>=0?'delta-positive':'delta-negative'}>{delta>=0?'+':''}{number(delta)} <small>({percentageDelta(change)})</small></b></div>})}</div><div className="scenario-ai-note"><div><Sparkles size={15}/><span>SCENARIO INTERPRETATION</span></div><p>At {number(result.scenario.applications)} applications, the configured stage assumptions yield {number(result.scenario.enrolled)} enrolments ({rate(result.scenario.enrolment_rate)} of scenario volume). This is a deterministic calculation, not a causal outcome prediction.</p><button className="text-action" type="button" onClick={()=>onAskAI('Interpret the current scenario. Use its baseline, scenario counts, and configured multipliers; distinguish the calculation from a causal prediction.',{application_volume:Number(inputs.application_volume),stage_adjustments:{submitted:Number(inputs.submitted),admitted:Number(inputs.admitted),enrolled:Number(inputs.enrolled)}})}>Ask AI about this scenario <ArrowRight size={14}/></button></div></section></div>
  </div>
}

export function ModelPage({ data, onAskAI }) {
  const baseline=data.model.baseline
  const advanced=data.model.advanced
  const metricRows=['accuracy','roc_auc','pr_auc','f1'].map((metric)=>({metric:metric==='roc_auc'?'ROC-AUC':metric==='pr_auc'?'PR-AUC':metric.toUpperCase(),baseline:baseline[metric],advanced:advanced[metric]}))
  const [model,setModel]=useState('advanced')
  const features=data.model[model].top_features
  const max=Math.max(...features.map((feature)=>feature.importance||feature.absolute_coefficient||0),0.00001)
  return <div className="page-stack"><PageHeading eyebrow="INTELLIGENCE / MODEL" title="Model intelligence" description="Compare holdout classification metrics and inspect the signals each fitted model uses." actions={<span className="status-badge status-warning"><CircleHelp size={13}/> Research quality</span>} />
    <section className="model-alert"><BrainCircuit size={17}/><p>Current holdout discrimination is weak. The random forest predicts no positive cases at threshold 0.5; neither model is suitable for real admissions decisions.</p></section>
    <section className="surface-panel"><div className="panel-header"><div><span className="section-overline">HOLDOUT COMPARISON</span><h2>Baseline vs advanced</h2><p>Models share the same stratified 75/25 split and target label.</p></div></div><div className="model-metric-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={metricRows} margin={{top:12,right:12,left:0,bottom:0}}><CartesianGrid strokeDasharray="3 5" vertical={false}/><XAxis dataKey="metric" tickLine={false} axisLine={false}/><YAxis domain={[0,1]} tickLine={false} axisLine={false}/><TooltipBox formatter={(value)=>Number(value).toFixed(3)}/><Bar dataKey="baseline" name="Logistic regression" fill="#44d8c3" radius={[5,5,0,0]} isAnimationActive/><Bar dataKey="advanced" name="Random forest" fill="#8b7bff" radius={[5,5,0,0]} isAnimationActive/></BarChart></ResponsiveContainer></div><div className="chart-legend"><span><i className="legend-mark historical"/> Logistic regression</span><span><i className="legend-mark forecast"/> Random forest</span></div><div className="model-metric-cards">{metricRows.map((row)=><div key={row.metric}><span>{row.metric}</span><small>Logistic</small><strong>{Number(row.baseline).toFixed(3)}</strong><small>Random forest</small><strong>{Number(row.advanced).toFixed(3)}</strong></div>)}</div></section>
    <section className="surface-panel feature-panel"><div className="panel-header"><div><span className="section-overline">MODEL INTERPRETATION</span><h2>Feature signals</h2><p>Relative signal within the selected estimator; not evidence of causal effect.</p></div><label className="select-field"><span>Estimator</span><select value={model} onChange={(event)=>setModel(event.target.value)}><option value="advanced">Random forest</option><option value="baseline">Logistic regression</option></select><ChevronDown size={14}/></label></div><div className="feature-bars">{features.map((feature,index)=>{const score=feature.importance??feature.absolute_coefficient??0;const label=feature.feature.replace(/^(num__|cat__)/,'').replaceAll('_',' ');return <div className="feature-row" key={feature.feature}><span className="feature-rank">{String(index+1).padStart(2,'0')}</span><span className="feature-name">{label}</span><span className="feature-track"><i style={{width:`${(score/max)*100}%`,'--feature-color':colors[index%colors.length]}}/></span><strong>{score.toFixed(3)}</strong></div>})}</div><p className="causal-disclaimer"><Info size={15}/> Feature signals summarize model associations and are not evidence of causal effects.</p></section>
    <DataSignal label="Model signal" title="Treat scores as exploratory" body={`Logistic ROC-AUC ${Number(baseline.roc_auc).toFixed(3)}; random forest ROC-AUC ${Number(advanced.roc_auc).toFixed(3)}. The forest's default threshold predicted ${number(advanced.confusion_matrix[0][1]+advanced.confusion_matrix[1][1])} positive cases, so accuracy alone is misleading.`} action="Ask AI to explain model limits" onClick={()=>onAskAI('Explain the current model metrics and why high accuracy may be misleading under class imbalance.')} icon={BrainCircuit}/>
  </div>
}

export function AuditPage({ data }) {
  const [filter,setFilter]=useState('all')
  const [expanded,setExpanded]=useState(null)
  const events=[...data.audit].reverse().filter((event)=>filter==='all'||event.action===filter)
  const iconFor=(action)=>action.includes('scenario')?<FlaskConical size={16}/>:action.includes('login')||action.includes('logout')?<Eye size={16}/>:action.includes('assistant')?<Sparkles size={16}/>:<Activity size={16}/>
  return <div className="page-stack"><PageHeading eyebrow="SYSTEM / AUDIT" title="Activity timeline" description="Recent authentication and sensitive actions recorded by this API process." actions={<label className="select-field"><span>Filter activity</span><select value={filter} onChange={(event)=>setFilter(event.target.value)}><option value="all">All events</option>{[...new Set(data.audit.map((event)=>event.action))].map((action)=><option key={action}>{action}</option>)}</select><ChevronDown size={14}/></label>} />
    <section className="surface-panel audit-panel"><div className="panel-header"><div><span className="section-overline">RECENT EVENTS</span><h2>{events.length} recorded actions</h2><p>Event times are server UTC. This audit stream is process-local and resets on restart.</p></div><span className="context-badge"><span className="mini-live"/> Active process</span></div><div className="audit-timeline">{events.map((event,index)=><article className="audit-event" key={`${event.action}-${event.timestamp||index}`}><span className="timeline-rail"><i className="timeline-node"/></span><span className="audit-icon">{iconFor(event.action)}</span><div className="audit-event-main"><button type="button" className="audit-event-toggle" onClick={()=>setExpanded(expanded===index?null:index)} aria-expanded={expanded===index}><span><strong>{event.action.replaceAll('_',' ')}</strong><small>{event.email||'System action'}</small></span><span className="audit-event-meta"><time>{event.timestamp?new Date(event.timestamp).toLocaleString():'Time unavailable'}</time><span className="status-badge status-success">{event.status}</span><ChevronDown size={14}/></span></button>{expanded===index&&<div className="audit-event-details">{Object.entries(event).filter(([key])=>key!=='action').map(([key,value])=><span key={key}><b>{key.replaceAll('_',' ')}</b> {String(value)}</span>)}</div>}</div></article>)}{!events.length&&<div className="empty-state">No audit events match this filter.</div>}</div></section>
  </div>
}

export function SettingsPage({ data, theme, onTheme, collapsed, onToggleSidebar, user }) {
  return <div className="page-stack"><PageHeading eyebrow="SYSTEM / PREFERENCES" title="Workspace settings" description="Manage this local demonstration workspace and review its connected services." /><section className="settings-grid"><article className="surface-panel settings-card"><div className="settings-card-icon"><UsersRound size={18}/></div><div><span className="section-overline">ACCOUNT</span><h2>{user?.email||'Admissions admin'}</h2><p>Local capstone administrator</p></div><span className="status-badge status-success">Signed in</span></article><article className="surface-panel settings-card"><div className="settings-card-icon"><Sparkles size={18}/></div><div><span className="section-overline">AI PROVIDER</span><h2>{data.assistantStatus.configured?'Groq connected':'Not configured'}</h2><p>{data.assistantStatus.configured?'Questions use aggregate AdmitFlow context.':'Set GROQ_API_KEY on the backend to enable live AI answers.'}</p></div><span className={`status-badge ${data.assistantStatus.configured?'status-success':'status-warning'}`}>{data.assistantStatus.configured?'Ready':'Offline'}</span></article><article className="surface-panel settings-card"><div className="settings-card-icon"><Layers3 size={18}/></div><div><span className="section-overline">APPEARANCE</span><h2>{theme==='dark'?'Midnight':'Daylight'} theme</h2><p>Theme preference is saved in this browser.</p></div><button className="secondary-button" type="button" onClick={onTheme}>Switch theme</button></article><article className="surface-panel settings-card"><div className="settings-card-icon"><BarChart3 size={18}/></div><div><span className="section-overline">LAYOUT</span><h2>{collapsed?'Compact sidebar':'Expanded sidebar'}</h2><p>Navigation density can be adjusted any time.</p></div><button className="secondary-button" type="button" onClick={onToggleSidebar}>Toggle sidebar</button></article></section></div>
}
