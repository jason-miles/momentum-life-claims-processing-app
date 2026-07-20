import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type InboxClaim } from '../lib/api'
import { useApi } from '../lib/useApi'
import { zar } from '../lib/format'
import { Page, Card, Async, StatePill, Pill, labelize } from '../components/ui'

const PAGE_SIZE = 25

export default function Inbox() {
  const state = useApi(() => api.inbox(), [])
  const [q, setQ] = useState('')
  const [type, setType] = useState('all')
  const [claimState, setClaimState] = useState('all')
  const [page, setPage] = useState(0)
  const nav = useNavigate()

  // Reset to the first page whenever a filter changes.
  const onFilter = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v)
    setPage(0)
  }

  return (
    <Page title="Claims Inbox" sub="Assessment queue — synthetic claims across all states">
      <Async state={{ ...state, data: state.data?.claims ?? null }} empty="No claims">
        {(claims: InboxClaim[]) => {
          const types = ['all', ...uniq(claims.map((c) => c.claim_type))]
          const states = ['all', ...uniq(claims.map((c) => c.state))]
          const rows = claims.filter((c) => {
            if (type !== 'all' && c.claim_type !== type) return false
            if (claimState !== 'all' && c.state !== claimState) return false
            if (q && !c.claim_no.toLowerCase().includes(q.toLowerCase())) return false
            return true
          })
          const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE))
          const safePage = Math.min(page, pageCount - 1)
          const pageRows = rows.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE)
          return (
            <Card
              title={`${rows.length} claims`}
              right={
                <div className="filter-bar">
                  <input
                    className="input search"
                    placeholder="Search claim no…"
                    value={q}
                    onChange={(e) => onFilter(setQ)(e.target.value)}
                  />
                  <select className="select" value={type} onChange={(e) => onFilter(setType)(e.target.value)}>
                    {types.map((t) => (
                      <option key={t} value={t}>
                        {t === 'all' ? 'All types' : labelize(t)}
                      </option>
                    ))}
                  </select>
                  <select
                    className="select"
                    value={claimState}
                    onChange={(e) => onFilter(setClaimState)(e.target.value)}
                  >
                    {states.map((s) => (
                      <option key={s} value={s}>
                        {s === 'all' ? 'All states' : labelize(s)}
                      </option>
                    ))}
                  </select>
                </div>
              }
            >
              <div className="table-wrap">
                <table className="tabular">
                  <thead>
                    <tr>
                      <th>Claim</th>
                      <th>Type</th>
                      <th>State</th>
                      <th>Days</th>
                      <th>Flags</th>
                      <th>Reqs</th>
                      <th style={{ textAlign: 'right' }}>Sum assured</th>
                      <th>Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageRows.map((c) => (
                      <tr
                        key={c.claim_no}
                        className="claim-link"
                        onClick={() => nav(`/claim/${encodeURIComponent(c.claim_no)}`)}
                      >
                        <td>
                          <strong>{c.claim_no}</strong>
                        </td>
                        <td>{labelize(c.claim_type)}</td>
                        <td>
                          <StatePill state={c.state} />
                        </td>
                        <td>{c.days_in_stage ?? '—'}</td>
                        <td>
                          <div className="chip-row">
                            {c.occupation_mismatch && <Pill tone="warn">⚠ occ</Pill>}
                            {c.early_claim_flag && <Pill tone="warn">early</Pill>}
                            {c.benefit_status && c.benefit_status !== 'in_force' && (
                              <Pill tone="bad">{c.benefit_status}</Pill>
                            )}
                          </div>
                        </td>
                        <td>
                          {c.reqs_received ?? '—'}/{c.reqs_total ?? '—'}
                        </td>
                        <td style={{ textAlign: 'right' }}>{zar(c.sum_assured)}</td>
                        <td>
                          <span
                            className={'dot ' + (c.high_risk ? 'dot-bad' : 'dot-good')}
                            title={c.risk_score != null ? c.risk_score.toFixed(2) : ''}
                          />{' '}
                          {c.risk_score != null ? c.risk_score.toFixed(2) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {rows.length > PAGE_SIZE && (
                <div className="pager">
                  <span>
                    Showing {safePage * PAGE_SIZE + 1}–
                    {Math.min(safePage * PAGE_SIZE + PAGE_SIZE, rows.length)} of {rows.length}
                  </span>
                  <div className="pager-btns">
                    <button disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>
                      ← Prev
                    </button>
                    <span style={{ padding: '5px 4px' }}>
                      Page {safePage + 1} of {pageCount}
                    </span>
                    <button
                      disabled={safePage >= pageCount - 1}
                      onClick={() => setPage(safePage + 1)}
                    >
                      Next →
                    </button>
                  </div>
                </div>
              )}
            </Card>
          )
        }}
      </Async>
    </Page>
  )
}

function uniq(xs: string[]): string[] {
  return Array.from(new Set(xs.filter(Boolean))).sort()
}
