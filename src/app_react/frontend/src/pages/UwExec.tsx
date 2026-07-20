import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api, type UwExec as UwExecData, type UwNtu } from '../lib/api'
import { useApi } from '../lib/useApi'
import { zar, num } from '../lib/format'
import { Page, Card, Async, Kpi, labelize } from '../components/ui'

const NAVY = '#14205a'
const RED = '#e4002b'
const JOURNEY_COLORS: Record<string, string> = {
  auto_requirements: '#14205a',
  refer_underwriter: '#c77700',
  fast_track: '#1e874b',
  tele_underwriting: '#0071bc',
}

/* Underwriting Executive View — portfolio health for exec/portfolio managers.
   Phone-friendly KPI tiles + the NTU value story (recoverable revenue). */
export default function UwExec() {
  const ex = useApi(() => api.uwExec(), [])
  const ntu = useApi(() => api.uwNtu(), [])

  return (
    <Page title="Underwriting — Executive View" sub="New-business portfolio health at a glance — governed, no per-seat licence">
      <Async state={ex} empty="No underwriting data">
        {(e: UwExecData) => (
          <>
            <div className="kpi-grid">
              <Kpi label="Straight-through processing"
                   value={e.stp_rate != null ? (e.stp_rate * 100).toFixed(1) : '—'} unit="%"
                   foot="fast-track + tele — automation depth" />
              <Kpi label="NTU rate"
                   value={e.ntu_rate != null ? (e.ntu_rate * 100).toFixed(1) : '—'} unit="%"
                   foot="new business not taken up" />
              <Kpi label="Avg turnaround"
                   value={e.avg_cycle_days != null ? e.avg_cycle_days.toFixed(1) : '—'} unit="days"
                   foot="first-pass → decision" />
              <Kpi label="Counteroffers"
                   value={num(e.decision_split.find((d) => d.outcome === 'counteroffer')?.n ?? 0)}
                   foot="loadings & exclusions issued" />
            </div>

            <div className="grid-2 mt-lg">
              <Card title="First-pass journey split" sub="How new business is routed">
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={e.journey_split} dataKey="n" nameKey="journey_type"
                         innerRadius={68} outerRadius={108} paddingAngle={2}>
                      {e.journey_split.map((d) => (
                        <Cell key={d.journey_type} fill={JOURNEY_COLORS[d.journey_type] || NAVY} />
                      ))}
                    </Pie>
                    <Legend formatter={(v) => labelize(String(v))} />
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Card>
              <Card title="Decision mix" sub="Underwriter outcomes">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={e.decision_split}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="outcome" tickFormatter={labelize} fontSize={11}
                           interval={0} angle={-12} textAnchor="end" height={54} />
                    <YAxis fontSize={12} />
                    <Tooltip />
                    <Bar dataKey="n" name="Cases" fill={NAVY} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </div>
          </>
        )}
      </Async>

      <Async state={ntu} empty="No NTU data">
        {(n: UwNtu) => {
          const total = n.funnel.reduce((s, b) => s + (b.n || 0), 0)
          const reqBucket = n.funnel.find((b) => b.ntu_bucket === 'requirements_never_returned')
          const recoverable = reqBucket ? Math.round(reqBucket.n * 0.25) : 0
          const recoverableSar = reqBucket ? reqBucket.total_sar * 0.25 : 0
          return (
            <>
              <div className="grid-2 mt-lg">
                <Card title="NTU drop-off — where value leaks" sub="Composition of Not-Taken-Up new business">
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={n.funnel} layout="vertical" margin={{ left: 40 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" fontSize={12} />
                      <YAxis type="category" dataKey="ntu_bucket" tickFormatter={labelize}
                             width={150} fontSize={11} />
                      <Tooltip formatter={(v: number) => [v, 'cases']} />
                      <Bar dataKey="n" name="Cases" radius={[0, 4, 4, 0]}>
                        {n.funnel.map((d, i) => (
                          <Cell key={i} fill={d.ntu_bucket === 'requirements_never_returned' ? RED : NAVY} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
                <Card title="Recoverable new business" sub="The intervention opportunity">
                  <div className="kpi" style={{ boxShadow: 'none', border: 'none', padding: 0 }}>
                    <div className="label">If 25% of “requirements never returned” is saved</div>
                    <div className="value" style={{ color: 'var(--good)' }}>
                      {num(recoverable)}<span className="unit"> cases</span>
                    </div>
                    <div className="foot">
                      ≈ <strong>{zar(recoverableSar)}</strong> of sum-at-risk recovered — the NTU
                      Co-Pilot flags these before they go quiet and triggers intervention.
                    </div>
                  </div>
                  <dl className="kv mt">
                    <dt>Total NTU</dt><dd>{num(total)} cases</dd>
                    <dt>Requirements never returned</dt>
                    <dd>{num(reqBucket?.n ?? 0)} ({reqBucket?.pct ?? 0}%)</dd>
                    <dt>Open at-risk now</dt><dd>{num(n.at_risk.length)} cases</dd>
                  </dl>
                </Card>
              </div>
            </>
          )
        }}
      </Async>
    </Page>
  )
}
