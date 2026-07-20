import type { ReactNode } from 'react'

/* ---- Page scaffold ---- */
export function Page({
  title,
  sub,
  actions,
  children,
}: {
  title: string
  sub?: string
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <main className="page">
      <div className="page-head between">
        <div>
          <h1>{title}</h1>
          {sub && <p className="sub">{sub}</p>}
        </div>
        {actions}
      </div>
      {children}
    </main>
  )
}

export function Card({
  title,
  sub,
  right,
  children,
  className = '',
}: {
  title?: string
  sub?: string
  right?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`card ${className}`}>
      {(title || right) && (
        <div className="card-head between">
          <div>
            {title && <h2>{title}</h2>}
            {sub && <div className="card-sub">{sub}</div>}
          </div>
          {right}
        </div>
      )}
      {children}
    </section>
  )
}

/* ---- Loading / empty / error ---- */
export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="state">
      <div className="spinner" />
      <div>{label}</div>
    </div>
  )
}

export function StatePanel({
  title,
  message,
}: {
  title: string
  message?: string
}) {
  return (
    <div className="state">
      <h3>{title}</h3>
      {message && <p className="muted">{message}</p>}
    </div>
  )
}

/* Render children when loaded; otherwise a friendly state. */
export function Async<T>({
  state,
  empty,
  children,
}: {
  state: { data: T | null; loading: boolean; error: string | null }
  empty?: string
  children: (data: T) => ReactNode
}) {
  if (state.loading) return <Loading />
  if (state.error)
    return (
      <StatePanel
        title="Couldn’t reach Databricks"
        message={state.error + ' — showing an empty view. Check the warehouse connection.'}
      />
    )
  if (state.data == null) return <StatePanel title={empty || 'No data'} />
  return <>{children(state.data)}</>
}

/* ---- Pills ---- */
type PillTone = 'good' | 'warn' | 'bad' | 'info' | 'navy' | 'red' | 'neutral'

export function Pill({ tone = 'neutral', children }: { tone?: PillTone; children: ReactNode }) {
  return <span className={`pill pill-${tone}`}>{children}</span>
}

const STATE_TONE: Record<string, PillTone> = {
  initiated: 'neutral',
  lodged: 'info',
  in_assessment: 'warn',
  decided: 'navy',
  paid: 'good',
}
export function StatePill({ state }: { state: string }) {
  const tone = STATE_TONE[state] || 'neutral'
  return <Pill tone={tone}>{labelize(state)}</Pill>
}

export function labelize(s: string): string {
  return String(s || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/* ---- KPI tile ---- */
export function Kpi({
  label,
  value,
  unit,
  foot,
}: {
  label: string
  value: ReactNode
  unit?: string
  foot?: ReactNode
}) {
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className="value">
        {value}
        {unit && <span className="unit">{unit}</span>}
      </div>
      {foot && <div className="foot">{foot}</div>}
    </div>
  )
}

/* ---- Discrepancy badge ---- */
export function DiscrepancyBadge({ text }: { text: string }) {
  return <span className="pill pill-warn">⚠ {text}</span>
}

/* ---- Recommendation line ---- */
export function RecoLine({ recommendation }: { recommendation: string }) {
  const r = (recommendation || '').toUpperCase()
  let cls = 'reco-line reco-refer'
  if (r.startsWith('PAY') || r.startsWith('APPROVE')) cls = 'reco-line reco-approve'
  else if (r.startsWith('DECLINE') || r.startsWith('REJECT')) cls = 'reco-line reco-decline'
  else if (r.startsWith('INVEST')) cls = 'reco-line reco-investigate'
  else if (r.startsWith('REFER') || r.startsWith('PEND') || r.startsWith('REQUEST'))
    cls = 'reco-line reco-refer'
  return (
    <div className={cls}>
      <span className="small muted">Recommendation</span>
      <strong>{recommendation || 'N/A'}</strong>
    </div>
  )
}

/* Tiny markdown-ish renderer: **bold**, `code`, line breaks. Safe (no HTML injection). */
export function Markdown({ text }: { text: string }) {
  const blocks = (text || '').split(/\n{2,}/)
  return (
    <div className="md">
      {blocks.map((b, i) => (
        <p key={i}>{renderInline(b)}</p>
      ))}
    </div>
  )
}

function renderInline(s: string): ReactNode[] {
  // split on **bold** and `code`
  const parts = s.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) return <strong key={i}>{p.slice(2, -2)}</strong>
    if (p.startsWith('`') && p.endsWith('`'))
      return (
        <code key={i} className="chip">
          {p.slice(1, -1)}
        </code>
      )
    return <span key={i}>{p}</span>
  })
}
