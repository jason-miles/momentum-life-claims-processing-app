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
import { useNavigate } from 'react-router-dom'
import { api, type InboxClaim } from '../lib/api'
import { useApi } from '../lib/useApi'
import { Page, Card, Async, Pill, labelize } from '../components/ui'

const RED = '#e4002b'
const NAVY = '#14205a'

export default function Fraud() {
  const state = useApi(() => api.inbox(), [])
  const nav = useNavigate()

  return (
    <Page title="Fraud Workbench" sub="Risk triage and relationship signals">
      <div className="banner banner-warn">
        <span className="mocked-tag">Mocked</span>
        <span>
          Fraud scores and relationship flags on this page are <strong>synthetic demo data</strong>.
          Production fraud models are Phase 2+.
        </span>
      </div>

      <Async state={{ ...state, data: state.data?.claims ?? null }} empty="No claims">
        {(claims: InboxClaim[]) => {
          const ranked = [...claims].sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))
          const hist = histogram(ranked)
          return (
            <>
              <Card className="mt-lg" title="Risk distribution" sub="Mocked risk scores across the book">
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={hist}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="bucket" fontSize={12} />
                    <YAxis fontSize={12} />
                    <Tooltip />
                    <Bar dataKey="n" name="Claims" radius={[4, 4, 0, 0]}>
                      {hist.map((h, i) => (
                        <Cell key={i} fill={h.hi >= 0.6 ? RED : NAVY} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              <Card className="mt-lg" title="Highest-risk claims">
                <div className="table-wrap">
                  <table className="tabular">
                    <thead>
                      <tr>
                        <th>Claim</th>
                        <th>Type</th>
                        <th>Risk</th>
                        <th>Signals</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ranked.slice(0, 25).map((c) => (
                        <tr key={c.claim_no} className="claim-link" onClick={() => nav(`/claim/${c.claim_no}`)}>
                          <td>
                            <strong>{c.claim_no}</strong>
                          </td>
                          <td>{labelize(c.claim_type)}</td>
                          <td>
                            <span
                              className="dot"
                              style={{ background: (c.risk_score ?? 0) >= 0.6 ? RED : NAVY }}
                            />{' '}
                            {c.risk_score != null ? c.risk_score.toFixed(2) : '—'}
                          </td>
                          <td>
                            <div className="chip-row">
                              {c.early_claim_flag && <Pill tone="warn">early claim</Pill>}
                              {c.occupation_mismatch && <Pill tone="warn">occ mismatch</Pill>}
                              {c.benefit_status && c.benefit_status !== 'in_force' && (
                                <Pill tone="bad">benefit {c.benefit_status}</Pill>
                              )}
                              {(c.risk_score ?? 0) >= 0.6 && <Pill tone="red">elevated</Pill>}
                            </div>
                          </td>
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

function histogram(claims: InboxClaim[]) {
  const buckets = [0, 0.2, 0.4, 0.6, 0.8]
  return buckets.map((lo, i) => {
    const hi = i === buckets.length - 1 ? 1.01 : buckets[i + 1]
    const n = claims.filter((c) => (c.risk_score ?? 0) >= lo && (c.risk_score ?? 0) < hi).length
    return { bucket: `${lo.toFixed(1)}–${(i === buckets.length - 1 ? 1 : hi).toFixed(1)}`, n, hi: lo }
  })
}
