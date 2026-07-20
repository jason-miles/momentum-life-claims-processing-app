import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type ClaimDetail as CD, type Synopsis } from '../lib/api'
import { useApi } from '../lib/useApi'
import { zar, fmtDate, fmtDateTime } from '../lib/format'
import { useRole } from '../lib/roleContext'
import {
  Card,
  Async,
  Pill,
  StatePill,
  Loading,
  Markdown,
  RecoLine,
  DiscrepancyBadge,
  labelize,
} from '../components/ui'

export default function ClaimDetail() {
  const { claimNo = '' } = useParams()
  const state = useApi(() => api.claim(claimNo), [claimNo])

  return (
    <main className="page">
      <div className="page-head between">
        <div>
          <Link to="/" className="small muted">
            ← Claims Inbox
          </Link>
          <h1>{claimNo}</h1>
        </div>
      </div>
      <Async state={state} empty="Claim not found">
        {(d: CD) =>
          d.row == null ? (
            <Card>
              <p className="muted">Claim {claimNo} not found in the synthetic dataset.</p>
            </Card>
          ) : (
            <ClaimBody claimNo={claimNo} detail={d} />
          )
        }
      </Async>
    </main>
  )
}

function ClaimBody({ claimNo, detail }: { claimNo: string; detail: CD }) {
  const r = detail.row!
  const mismatch = !!r.occupation_mismatch
  const policyOk = r.policy_status === 'in_force'
  // Defensive: coalesce collections in case the API returns null (no error
  // boundary in the tree, so a null .map would white-screen the whole app).
  const requirements = detail.requirements ?? []
  const documents = detail.documents ?? []
  const events = detail.events ?? []
  const thirdParty = detail.third_party ?? []

  return (
    <>
      <div className="chip-row mt">
        <Pill tone="navy">{labelize(String(r.claim_type))}</Pill>
        <StatePill state={String(r.state)} />
        {mismatch && <Pill tone="warn">⚠ occupation mismatch</Pill>}
        {r.early_claim_flag && <Pill tone="warn">early claim</Pill>}
        {r.benefit_status && r.benefit_status !== 'in_force' && (
          <Pill tone="bad">benefit {r.benefit_status}</Pill>
        )}
      </div>

      <div className="detail-cols mt-lg">
        {/* LEFT — unified case view */}
        <Card title="Unified Case View" sub="Policy, benefit, requirements, third-party & timeline">
          <dl className="kv">
            <dt>Policy</dt>
            <dd>
              {r.policy_no || '—'}{' '}
              {policyOk ? <Pill tone="good">in force ✔</Pill> : <Pill tone="bad">{r.policy_status}</Pill>}
            </dd>
            <dt>Benefit</dt>
            <dd>
              {labelize(String(r.benefit_type))} · <strong>{zar(r.sum_assured)}</strong>{' '}
              {r.benefit_status === 'in_force' ? (
                <Pill tone="good">in force</Pill>
              ) : (
                <Pill tone="bad">{r.benefit_status}</Pill>
              )}
            </dd>
            <dt>Inception</dt>
            <dd>{fmtDate(r.inception_date)}</dd>
            <dt>Event date</dt>
            <dd>{fmtDate(r.event_date)}</dd>
            <dt>Province</dt>
            <dd>{r.province || '—'}</dd>
            <dt>Assessor</dt>
            <dd>{r.assessor || '—'}</dd>
          </dl>

          <div className="mt">
            <div className="card-sub">Occupation</div>
            <div className={'occ-compare' + (mismatch ? ' mismatch' : '')}>
              <div className="occ-box">
                <div className="lbl">At inception</div>
                <div className="val">{r.occupation_at_inception || '—'}</div>
              </div>
              <div className="occ-arrow">{mismatch ? '≠' : '→'}</div>
              <div className="occ-box">
                <div className="lbl">At claim</div>
                <div className="val">{r.occupation_at_claim || '—'}</div>
              </div>
            </div>
            {mismatch && (
              <p className="small" style={{ color: 'var(--red-dark)' }}>
                ⚠ Occupation differs materially — affects the disability definition; verify before payment.
              </p>
            )}
          </div>

          <div className="mt">
            <div className="card-sub between">
              <span>
                Requirements — {r.reqs_received ?? 0}/{r.reqs_total ?? 0} received
              </span>
            </div>
            <div className="checklist">
              {requirements.map((req) => {
                const done = req.status === 'received'
                return (
                  <div className="check-item" key={req.code}>
                    <span className={'check-mark ' + (done ? 'done' : 'miss')}>
                      {done ? '✓' : '!'}
                    </span>
                    <span className="desc">{req.description}</span>
                    <span className="code">{req.code}</span>
                  </div>
                )
              })}
              {requirements.length === 0 && <p className="muted small">No requirements recorded.</p>}
            </div>
          </div>

          <div className="mt">
            <div className="card-sub">Third-party verifications</div>
            <div className="chip-row">
              {thirdParty.map((t) => (
                <Pill key={t.source} tone="info">
                  {t.source}: {t.result_summary || '—'}
                </Pill>
              ))}
              {thirdParty.length === 0 && <span className="muted small">none recorded</span>}
            </div>
          </div>

          <div className="mt">
            <div className="card-sub">Timeline</div>
            <div className="timeline">
              {events.map((e, i) => (
                <div className="tl-item" key={i}>
                  <div className="ev">{labelize(e.event)}</div>
                  <div className="ts">{fmtDateTime(e.event_ts)}</div>
                </div>
              ))}
              {events.length === 0 && <p className="muted small">No events.</p>}
            </div>
          </div>

          <div className="mt">
            <div className="card-sub">Documents ({documents.length})</div>
            {documents.map((doc) => (
              <div className="doc-item" key={doc.doc_id}>
                <span className="doc-ico">📎</span>
                <span>{labelize(doc.doc_type)}</span>
                <span className="doc-id">{doc.doc_id}</span>
              </div>
            ))}
            {documents.length === 0 && <p className="muted small">No documents.</p>}
          </div>
        </Card>

        {/* RIGHT — AI synopsis + copilot */}
        <div className="stack">
          <SynopsisPanel claimNo={claimNo} />
          <CopilotPanel claimNo={claimNo} />
        </div>
      </div>

      <ActionBar claimNo={claimNo} riskScore={Number(r.risk_score ?? 0)} />
    </>
  )
}

function SynopsisPanel({ claimNo }: { claimNo: string }) {
  const state = useApi(() => api.synopsis(claimNo), [claimNo])
  return (
    <Card title="AI Synopsis" sub="Draft — review before use. Advisory only; never a final decision.">
      {state.loading ? (
        <Loading label="Drafting synopsis…" />
      ) : state.error || !state.data ? (
        <p className="muted small">Synopsis unavailable — {state.error || 'no data'}.</p>
      ) : (
        <SynopsisBody s={state.data} />
      )}
    </Card>
  )
}

function SynopsisBody({ s }: { s: Synopsis }) {
  // Defensive: the real agent (ai.agents.synopsis_agent) may omit these arrays;
  // there is no error boundary, so a null .length/.map would white-screen the app.
  const discrepancies = s.discrepancies ?? []
  const citations = s.citations ?? []
  return (
    <>
      <RecoLine recommendation={s.recommendation} />
      {discrepancies.length > 0 && (
        <div className="chip-row mt">
          {discrepancies.map((d, i) => (
            <DiscrepancyBadge key={i} text={d} />
          ))}
        </div>
      )}
      <div className="mt">
        <Markdown text={s.markdown || ''} />
      </div>
      {citations.length > 0 && (
        <div className="mt">
          <div className="card-sub">Sources</div>
          <div className="chip-row">
            {citations.map((c, i) => (
              <code key={i} className="chip">
                [{c}]
              </code>
            ))}
          </div>
        </div>
      )}
      {s.similar_cases && s.similar_cases.length > 0 && (
        <div className="mt">
          <div className="card-sub">Similar prior claims (Vector Search over documents)</div>
          {s.similar_cases.map((c, i) => (
            <div key={i} className="uw-note">
              <div className="small muted">
                {c.claim_no} · {labelize(c.doc_type)} · score {c.score?.toFixed(2)}
              </div>
              <div className="small">{c.chunk_text}</div>
            </div>
          ))}
        </div>
      )}
      {s.source && (
        <div className="small muted mt">
          Generated by: <strong>{s.source}</strong>
        </div>
      )}
    </>
  )
}

interface Msg {
  role: 'user' | 'bot'
  text: string
}
const SUGGESTS = [
  'Has this life claimed elsewhere in the last 3 years?',
  'Summarise the outstanding requirements.',
  'Is the occupation change material to this claim?',
]

function CopilotPanel({ claimNo }: { claimNo: string }) {
  const [log, setLog] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)

  async function ask(question: string) {
    const q = question.trim()
    if (!q || busy) return
    setLog((l) => [...l, { role: 'user', text: q }])
    setInput('')
    setBusy(true)
    try {
      const res = await api.copilot(claimNo, q)
      setLog((l) => [...l, { role: 'bot', text: res.answer }])
    } catch (e) {
      setLog((l) => [...l, { role: 'bot', text: 'Copilot unavailable right now.' }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card title="Copilot" sub="Ask about this claim">
      <div className="suggest-chips">
        {SUGGESTS.map((s) => (
          <button key={s} className="chip" onClick={() => ask(s)} disabled={busy}>
            {s}
          </button>
        ))}
      </div>
      <div className="chat">
        {log.length > 0 && (
          <div className="chat-log">
            {log.map((m, i) => (
              <div key={i} className={'msg ' + m.role}>
                {m.text}
              </div>
            ))}
            {busy && <div className="msg bot">…</div>}
          </div>
        )}
        <div className="chat-input">
          <input
            className="input"
            placeholder="Ask a question about this claim…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && ask(input)}
          />
          <button className="btn btn-primary" onClick={() => ask(input)} disabled={busy}>
            Ask
          </button>
        </div>
      </div>
    </Card>
  )
}

function ActionBar({ claimNo, riskScore }: { claimNo: string; riskScore: number }) {
  const { role } = useRole()
  const assessors = useApi(() => api.assessors(), [])
  const [assignee, setAssignee] = useState('')
  const [comment, setComment] = useState('')
  const [msg, setMsg] = useState('')

  async function record(action: string) {
    setMsg('')
    const payload = JSON.stringify({ assignee, comment })
    try {
      const res = await api.action(claimNo, role, action, payload)
      setMsg(res.ok ? `✓ ${action} recorded` : `Could not record: ${res.error || 'error'}`)
    } catch (e) {
      // api.action throws on any non-2xx; surface it instead of a dead button.
      setMsg(`Could not record: ${e instanceof Error ? e.message : 'request failed'}`)
    }
  }

  return (
    <Card className="mt-lg" title="Referral & actions">
      <div className="action-bar">
        <div className="field">
          <label className="small muted">Assign to</label>
          <select className="select" value={assignee} onChange={(e) => setAssignee(e.target.value)}>
            <option value="">— select assessor —</option>
            {(assessors.data?.assessors ?? []).map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label className="small muted">Comment</label>
          <input
            className="input"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Optional note…"
          />
        </div>
        <div className="fraud-score">
          <div>
            <div className="small muted">Fraud score</div>
            <div className="num" style={{ color: riskScore >= 0.6 ? 'var(--red)' : 'var(--navy)' }}>
              {riskScore.toFixed(2)}
            </div>
          </div>
          <span className="mocked-tag">Mocked</span>
        </div>
      </div>
      <div className="action-bar">
        <div className="btns">
          <button className="btn btn-primary" onClick={() => record('accept_synopsis')}>
            Accept synopsis
          </button>
          <button className="btn btn-outline" onClick={() => record('edit_synopsis')}>
            Edit
          </button>
          <button className="btn btn-danger" onClick={() => record('record_referral')}>
            Record referral
          </button>
        </div>
        {msg && (
          <span
            className="small"
            style={{ color: msg.startsWith('✓') ? 'var(--good)' : 'var(--bad)' }}
          >
            {msg}
          </span>
        )}
      </div>
    </Card>
  )
}
