import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api, type UwExec, type UwNtu } from '../lib/api'
import { useApi } from '../lib/useApi'
import { zar } from '../lib/format'
import { Page, Card, Async, Kpi, labelize } from '../components/ui'

const NAVY = '#14205a'
const RED = '#e4002b'
const JOURNEY_COLORS: Record<string, string> = {
  auto_requirements: '#14205a',
  refer_underwriter: '#c77700',
  fast_track: '#1e874b',
  tele_underwriting: '#0071bc',
}

/* Underwriting analytics — journey split, decision split, NTU funnel, requirements.
   The Power BI displacement + NTU worked-example story. */
export default function UwAnalytics() {
  const ex = useApi(() => api.uwExec(), [])
  const ntu = useApi(() => api.uwNtu(), [])
  const reqs = useApi(() => api.uwRequirements(), [])

  return (
    <Page title="Underwriting Analytics" sub="Journey split · decision split · NTU drop-off · requirements — governed, no per-seat licence">
      <Async state={ex} empty="No underwriting data">
        {(e: UwExec) => (
          <>
            <div className="kpi-grid">
              <Kpi label="Straight-through processing"
                   value={e.stp_rate != null ? (e.stp_rate * 100).toFixed(1) : '—'} unit="%"
                   foot="fast-track + tele of all applications" />
              <Kpi label="NTU rate"
                   value={e.ntu_rate != null ? (e.ntu_rate * 100).toFixed(1) : '—'} unit="%"
                   foot="applications not taken up" />
              <Kpi label="Avg turnaround"
                   value={e.avg_cycle_days != null ? e.avg_cycle_days.toFixed(1) : '—'} unit="days"
                   foot="first-pass → decision" />
            </div>

            <div className="grid-2 mt-lg">
              <Card title="First-pass journey split" sub="Decision Manager routing of new business">
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
              <Card title="Manual decision split" sub="Underwriter outcomes + counteroffers">
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
        {(n: UwNtu) => (
          <div className="grid-2 mt-lg">
            <Card title="NTU drop-off — where applications leak" sub="Composition of Not-Taken-Up cases">
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
              <p className="small muted mt">
                Almost two-thirds of NTU is requirements that never come back — a single,
                addressable failure mode, not random churn.
              </p>
            </Card>
            <Card title="At-risk open cases" sub="Requirements set, no result — ranked by NTU propensity × sum-at-risk">
              <div className="table-wrap" style={{ maxHeight: 280, overflowY: 'auto' }}>
                <table className="tabular">
                  <thead>
                    <tr><th>Policy</th><th>SAR</th><th>Days out</th><th>NTU risk</th></tr>
                  </thead>
                  <tbody>
                    {n.at_risk.slice(0, 30).map((c) => (
                      <tr key={c.policy_no}>
                        <td><strong>{c.policy_no}</strong></td>
                        <td>{zar(c.sum_at_risk)}</td>
                        <td>{c.days_req_outstanding}</td>
                        <td style={{ color: c.ntu_propensity >= 0.6 ? RED : NAVY, fontWeight: 600 }}>
                          {(c.ntu_propensity * 100).toFixed(0)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}
      </Async>

      <Async state={reqs} empty="No requirement data">
        {(rq: { analytics: import('../lib/api').UwReqAnalytic[] }) => (
          <Card className="mt-lg" title="Requirements analytics" sub="Which evidence is asked for, return rate, and turnaround">
            <div className="table-wrap">
              <table className="tabular">
                <thead>
                  <tr>
                    <th>Requirement</th><th>Requested</th><th>Returned</th>
                    <th>Outstanding</th><th>Return %</th><th>Avg days</th>
                  </tr>
                </thead>
                <tbody>
                  {rq.analytics.map((a) => (
                    <tr key={a.code}>
                      <td>{a.description} <span className="muted small">({a.code})</span></td>
                      <td>{a.n_requested}</td>
                      <td>{a.n_returned}</td>
                      <td>{a.n_outstanding}</td>
                      <td>{a.pct_returned}%</td>
                      <td>{a.avg_days_to_return ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </Async>
    </Page>
  )
}
