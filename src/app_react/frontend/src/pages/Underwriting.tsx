import { useState } from 'react'
import { api, type UwCase, type UwCaseDetail, type UwSynopsis } from '../lib/api'
import { useApi } from '../lib/useApi'
import { zar, fmtDate } from '../lib/format'
import {
  Page, Card, Async, Pill, Loading, Markdown, RecoLine, DiscrepancyBadge, labelize,
} from '../components/ui'

/* Underwriting Co-Pilot — the new-business risk workbench.
   Left: case queue ranked by NTU propensity. Right: unified case view +
   AI risk synopsis + NTU intervention panel for the selected case. */
export default function Underwriting() {
  const list = useApi(() => api.uwInbox(), [])
  const [selected, setSelected] = useState<string | null>(null)

  return (
    <Page
      title="Underwriting Co-Pilot"
      sub="New-business risk assessment — one governed view across AS400, BPM, notepad & evidence"
    >
      <Async state={{ ...list, data: list.data?.cases ?? null }} empty="No cases">
        {(cases: UwCase[]) => {
          const active = selected ?? cases[0]?.policy_no ?? null
          return (
            <div className="uw-split">
              <Card title={`Case queue · ${cases.length}`} sub="Ranked by NTU propensity" className="uw-queue">
                <div className="uw-list">
                  {cases.slice(0, 60).map((c) => (
                    <button
                      key={c.policy_no}
                      className={'uw-list-item' + (c.policy_no === active ? ' active' : '')}
                      onClick={() => setSelected(c.policy_no)}
                    >
                      <div className="uw-li-top">
                        <strong>{c.policy_no}</strong>
                        <NtuGauge v={Number(c.ntu_propensity ?? 0)} />
                      </div>
                      <div className="uw-li-sub">
                        {labelize(c.benefit_type || '')} · {c.sar_band} ·{' '}
                        {labelize(c.journey_type || '')}
                      </div>
                    </button>
                  ))}
                </div>
              </Card>
              {active && <CaseDetail policyNo={active} />}
            </div>
          )
        }}
      </Async>
    </Page>
  )
}

function CaseDetail({ policyNo }: { policyNo: string }) {
  const state = useApi(() => api.uwCase(policyNo), [policyNo])
  return (
    <div className="uw-detail">
      <Async state={state} empty="Case not found">
        {(d: UwCaseDetail) =>
          d.row == null ? (
            <Card><p className="muted">Case {policyNo} not found.</p></Card>
          ) : (
            <CaseBody policyNo={policyNo} detail={d} />
          )
        }
      </Async>
    </div>
  )
}

function CaseBody({ policyNo, detail }: { policyNo: string; detail: UwCaseDetail }) {
  const r = detail.row!
  const reqs = detail.requirements ?? []
  const notes = detail.notes ?? []
  const prop = Number(r.ntu_propensity ?? 0)

  return (
    <>
      <div className="chip-row">
        <Pill tone="navy">{labelize(String(r.benefit_type))}</Pill>
        <Pill tone="neutral">{labelize(String(r.journey_type))}</Pill>
        <Pill tone="info">{r.sar_band}</Pill>
        {r.smoker_flag && <Pill tone="warn">smoker</Pill>}
        {r.sla_breach && <Pill tone="bad">SLA breach</Pill>}
        {prop >= 0.6 && <Pill tone="red">NTU risk {prop.toFixed(2)}</Pill>}
      </div>

      <div className="detail-cols mt-lg">
        <Card title="Unified Case View" sub="AS400 + BPM + notepad, keyed on policy number">
          <dl className="kv">
            <dt>Policy no</dt><dd>{r.policy_no}</dd>
            <dt>Sum at risk</dt><dd><strong>{zar(r.sum_at_risk)}</strong> ({r.sar_band})</dd>
            <dt>Life</dt><dd>Age {r.age} · {r.occupation_class} · {r.smoker_flag ? 'smoker' : 'non-smoker'}</dd>
            <dt>Risk score</dt><dd>{r.risk_score != null ? Number(r.risk_score).toFixed(2) : '—'}</dd>
            <dt>Channel</dt><dd>{r.channel as string} · {r.broker as string}</dd>
            <dt>Underwriter</dt><dd>{r.underwriter}</dd>
            <dt>Decision</dt>
            <dd>
              {r.decision_outcome ? labelize(r.decision_outcome) : <span className="muted">pending</span>}
              {r.loading_pct ? ` · +${r.loading_pct}% loading` : ''}
              {r.exclusion ? ` · ${r.exclusion} exclusion` : ''}
            </dd>
          </dl>

          <div className="mt">
            <div className="card-sub">Requirements — {r.reqs_returned ?? 0}/{r.reqs_total ?? 0} returned</div>
            <div className="checklist">
              {reqs.map((q) => (
                <div className="check-item" key={q.code}>
                  <span className={'check-mark ' + (q.status === 'returned' ? 'done' : 'miss')}>
                    {q.status === 'returned' ? '✓' : '!'}
                  </span>
                  <span className="desc">{q.description}</span>
                  <span className="code">{q.code}</span>
                </div>
              ))}
              {reqs.length === 0 && <p className="muted small">No requirements — fast-tracked.</p>}
            </div>
          </div>

          <div className="mt">
            <div className="card-sub">Underwriter notepad</div>
            {notes.map((n, i) => (
              <div key={i} className="uw-note">
                <div className="small muted">{n.author} · {fmtDate(n.note_ts)}</div>
                <div>{n.note_text}</div>
              </div>
            ))}
            {notes.length === 0 && <p className="muted small">No notes.</p>}
          </div>
        </Card>

        <div className="stack">
          <UwSynopsisPanel policyNo={policyNo} />
          <NtuPanel row={r} />
        </div>
      </div>
    </>
  )
}

function UwSynopsisPanel({ policyNo }: { policyNo: string }) {
  const state = useApi(() => api.uwSynopsis(policyNo), [policyNo])
  return (
    <Card title="AI Risk Synopsis" sub="Draft — review before use. Advisory only; never a bind/decline.">
      {state.loading ? (
        <Loading label="Assessing risk…" />
      ) : state.error || !state.data ? (
        <p className="muted small">Synopsis unavailable — {state.error || 'no data'}.</p>
      ) : (
        <UwSynopsisBody s={state.data} />
      )}
    </Card>
  )
}

function UwSynopsisBody({ s }: { s: UwSynopsis }) {
  const flags = s.flags ?? []
  const citations = s.citations ?? []
  return (
    <>
      <RecoLine recommendation={s.recommendation} />
      {flags.length > 0 && (
        <div className="chip-row mt">
          {flags.map((f, i) => <DiscrepancyBadge key={i} text={f} />)}
        </div>
      )}
      <div className="mt"><Markdown text={s.markdown || ''} /></div>
      {citations.length > 0 && (
        <div className="mt">
          <div className="card-sub">Sources</div>
          <div className="chip-row">
            {citations.map((c, i) => <code key={i} className="chip">[{c}]</code>)}
          </div>
        </div>
      )}
      {s.similar_cases && s.similar_cases.length > 0 && (
        <div className="mt">
          <div className="card-sub">Similar prior cases (Vector Search over notepad)</div>
          {s.similar_cases.map((c, i) => (
            <div key={i} className="uw-note">
              <div className="small muted">{c.policy_no} · score {c.score?.toFixed(2)}</div>
              <div className="small">{c.chunk_text}</div>
            </div>
          ))}
        </div>
      )}
      {s.source && <div className="small muted mt">Generated by: <strong>{s.source}</strong></div>}
    </>
  )
}

function NtuPanel({ row }: { row: UwCase }) {
  const prop = Number(row.ntu_propensity ?? 0)
  const outstanding = Number(row.reqs_outstanding ?? 0)
  const interventions =
    prop >= 0.6
      ? ['Nudge the broker', 'Switch to nurse home visit', 'Simplify / sequence requirements', 'Proactive client call']
      : ['Monitor — low NTU risk']
  return (
    <Card title="NTU Intervention" sub="Predict → act, before the case goes quiet">
      <div className="ntu-hero">
        <div className="ntu-hero-num" style={{ color: prop >= 0.6 ? 'var(--red)' : prop >= 0.35 ? 'var(--warn)' : 'var(--good)' }}>
          {(prop * 100).toFixed(0)}%
        </div>
        <div className="small muted">NTU propensity</div>
      </div>
      <dl className="kv mt">
        <dt>Outstanding reqs</dt><dd>{outstanding}</dd>
        <dt>Days outstanding</dt><dd>{row.days_req_outstanding ?? '—'}</dd>
        <dt>Bucket risk</dt><dd>{row.ntu_bucket ? labelize(row.ntu_bucket) : 'not yet NTU'}</dd>
      </dl>
      <div className="mt">
        <div className="card-sub">Recommended interventions</div>
        <ul className="uw-interventions">
          {interventions.map((x, i) => <li key={i}>{x}</li>)}
        </ul>
      </div>
    </Card>
  )
}

function NtuGauge({ v }: { v: number }) {
  const pctv = Math.round(v * 100)
  const color = v >= 0.6 ? 'var(--red)' : v >= 0.35 ? 'var(--warn)' : 'var(--good)'
  return <span className="ntu-gauge" style={{ color }}>{pctv}%</span>
}
