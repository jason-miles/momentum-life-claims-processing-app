import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, type Exec } from '../lib/api'
import { useApi } from '../lib/useApi'
import { num } from '../lib/format'
import { Page, Card, Async, Kpi, labelize } from '../components/ui'

const NAVY = '#14205a'
const DECISION_COLORS: Record<string, string> = {
  pay: '#1e874b',
  refer: '#c77700',
  decline: '#c0392b',
}

export default function ExecView() {
  const state = useApi(() => api.exec(), [])
  return (
    <Page title="Executive View" sub="Portfolio health at a glance — governed, no per-seat licence">
      <Async state={state} empty="No executive data">
        {(e: Exec) => {
          const decisions = aggregateDecisions(e.decision_split)
          return (
            <>
              <div className="kpi-grid">
                <Kpi
                  label="Avg cycle time"
                  value={e.kpis.cycle_time_days != null ? e.kpis.cycle_time_days.toFixed(1) : '—'}
                  unit="days"
                  foot="lodge → decision"
                />
                <Kpi
                  label="NTU rate"
                  value={e.kpis.ntu_rate != null ? (e.kpis.ntu_rate * 100).toFixed(1) : '—'}
                  unit="%"
                  foot="pre-lodge drop-off"
                />
                <Kpi
                  label="SLA attainment"
                  value={e.kpis.sla_attainment_pct != null ? e.kpis.sla_attainment_pct.toFixed(1) : '—'}
                  unit="%"
                  foot="within 20-day SLA"
                />
              </div>

              <div className="grid-2 mt-lg">
                <Card title="Decision split" sub="Pay / refer / decline across decided claims">
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={decisions}
                        dataKey="n"
                        nameKey="decision"
                        innerRadius={70}
                        outerRadius={110}
                        paddingAngle={2}
                      >
                        {decisions.map((d) => (
                          <Cell key={d.decision} fill={DECISION_COLORS[d.decision] || NAVY} />
                        ))}
                      </Pie>
                      <Legend formatter={(v) => labelize(String(v))} />
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Card>
                <Card title="Claims by province" sub="Geographic distribution">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={e.by_province}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="province" fontSize={11} interval={0} angle={-15} textAnchor="end" height={60} />
                      <YAxis fontSize={12} />
                      <Tooltip />
                      <Bar dataKey="n_claims" name="Claims" fill={NAVY} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </div>

              <Card className="mt-lg" title="Decision detail">
                <div className="table-wrap">
                  <table className="tabular">
                    <thead>
                      <tr>
                        <th>Claim type</th>
                        <th>Decision</th>
                        <th>Count</th>
                        <th>Share</th>
                      </tr>
                    </thead>
                    <tbody>
                      {e.decision_split.map((d, i) => (
                        <tr key={i}>
                          <td>{labelize(d.claim_type)}</td>
                          <td>{labelize(d.decision)}</td>
                          <td>{num(d.n)}</td>
                          <td>{d.pct != null ? d.pct.toFixed(1) + '%' : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </>
          )
        }}
      </Async>
    </Page>
  )
}

function aggregateDecisions(rows: Exec['decision_split']) {
  const by: Record<string, { decision: string; n: number }> = {}
  for (const r of rows) {
    if (!r.decision) continue
    by[r.decision] = by[r.decision] || { decision: r.decision, n: 0 }
    by[r.decision].n += r.n || 0
  }
  return Object.values(by)
}
