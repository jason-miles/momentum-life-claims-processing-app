import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, type Ntu, type Ops } from '../lib/api'
import { useApi } from '../lib/useApi'
import { num } from '../lib/format'
import { Page, Card, Async, Kpi, labelize } from '../components/ui'

const NAVY = '#14205a'
const RED = '#e4002b'

export default function NtuOps() {
  const ntu = useApi(() => api.ntu(), [])
  const ops = useApi(() => api.ops(), [])

  return (
    <Page title="NTU / Ops Dashboard" sub="Pre-lodge drop-off leakage & operational throughput">
      <Async state={ntu} empty="No NTU data">
        {(n: Ntu) => {
          const byType = aggregateFunnel(n.funnel)
          return (
            <>
              <div className="grid-2">
                <Card title="Drop-off funnel by claim type" sub="Claims vs Not-Taken-Up (NTU)">
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={byType}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="claim_type" tickFormatter={labelize} fontSize={12} />
                      <YAxis fontSize={12} />
                      <Tooltip />
                      <Bar dataKey="n_claims" name="Claims" fill={NAVY} radius={[4, 4, 0, 0]} />
                      <Bar dataKey="n_ntu" name="NTU" fill={RED} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
                <Card title="At-risk pre-lodge claims" sub="Intervene before drop-off">
                  <div className="table-wrap" style={{ maxHeight: 300, overflowY: 'auto' }}>
                    <table className="tabular">
                      <thead>
                        <tr>
                          <th>Claim</th>
                          <th>Type</th>
                          <th>Days out</th>
                          <th>Outstanding</th>
                          <th>Drop-off risk</th>
                        </tr>
                      </thead>
                      <tbody>
                        {n.at_risk.slice(0, 40).map((c) => (
                          <tr key={c.claim_no}>
                            <td>
                              <strong>{c.claim_no}</strong>
                            </td>
                            <td>{labelize(c.claim_type)}</td>
                            <td>{c.days_outstanding ?? '—'}</td>
                            <td>{c.n_outstanding_reqs ?? '—'}</td>
                            <td>
                              <PropBar v={Number(c.drop_off_propensity ?? 0)} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>

              <Async state={ops} empty="No ops data">
                {(o: Ops) => {
                  const breaches = o.metrics.filter((m) => m.sla_breach === true).length
                  const decided = o.metrics.filter((m) => m.days_lodge_to_decision != null).length
                  return (
                    <>
                      <div className="kpi-grid mt-lg">
                        <Kpi label="SLA breaches" value={num(breaches)} foot="claims over the 20-day SLA" />
                        <Kpi label="Decided claims" value={num(decided)} foot="lodge → decision recorded" />
                        <Kpi label="At-risk pre-lodge" value={num(n.at_risk.length)} foot="quiet > 7 days" />
                      </div>
                      <Card className="mt-lg" title="Throughput per assessor" sub="Claims decided">
                        <ResponsiveContainer width="100%" height={300}>
                          <BarChart data={o.throughput.slice(0, 15)} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                            <XAxis type="number" fontSize={12} />
                            <YAxis
                              type="category"
                              dataKey="assessor"
                              width={90}
                              fontSize={11}
                            />
                            <Tooltip />
                            <Bar dataKey="n_decided" name="Decided" fill={NAVY} radius={[0, 4, 4, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </Card>
                    </>
                  )
                }}
              </Async>
            </>
          )
        }}
      </Async>
    </Page>
  )
}

function PropBar({ v }: { v: number }) {
  const pctv = Math.round(v * 100)
  const color = v >= 0.6 ? RED : v >= 0.35 ? '#c77700' : '#1e874b'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 8, background: '#eef2f7', borderRadius: 999 }}>
        <div style={{ width: `${pctv}%`, height: 8, background: color, borderRadius: 999 }} />
      </div>
      <span className="small" style={{ minWidth: 34, textAlign: 'right' }}>
        {pctv}%
      </span>
    </div>
  )
}

function aggregateFunnel(funnel: Ntu['funnel']) {
  const byType: Record<string, { claim_type: string; n_claims: number; n_ntu: number }> = {}
  for (const r of funnel) {
    const k = r.claim_type
    if (!byType[k]) byType[k] = { claim_type: k, n_claims: 0, n_ntu: 0 }
    byType[k].n_claims += r.n_claims || 0
    byType[k].n_ntu += r.n_ntu || 0
  }
  return Object.values(byType)
}
