import { useState } from 'react'
import { api, type GenieResponse } from '../lib/api'
import { Page, Card } from '../components/ui'

const SUGGESTS = [
  'Which claims have an occupation mismatch?',
  'Show me pre-lodge claims at risk of drop-off',
  "What's the average cycle time for disability claims?",
  'How many death claims were declined?',
  'List outstanding requirements for CLM-DISAB-DISCREP',
  'Which assessor has the highest throughput?',
  'What is the NTU rate by claim type?',
  'Show SLA breaches',
]

interface Turn {
  q: string
  res?: GenieResponse
  pending?: boolean
}

export default function Copilot() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [input, setInput] = useState('')
  const [convId, setConvId] = useState<string | undefined>(undefined)
  const [busy, setBusy] = useState(false)

  async function ask(question: string) {
    const q = question.trim()
    if (!q || busy) return
    setInput('')
    setBusy(true)
    setTurns((t) => [...t, { q, pending: true }])
    try {
      const res = await api.genie(q, convId)
      if (res.conversation_id) setConvId(res.conversation_id)
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { q, res } : x)))
    } catch {
      setTurns((t) =>
        t.map((x, i) =>
          i === t.length - 1 ? { q, res: { ok: false, error: 'Genie unavailable.' } } : x,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <Page
      title="AI Copilot"
      sub="Ask questions across all claims — powered by the Momentum Claims Analyst Genie space"
    >
      <Card>
        <div className="suggest-chips">
          {SUGGESTS.map((s) => (
            <button key={s} className="chip" onClick={() => ask(s)} disabled={busy}>
              {s}
            </button>
          ))}
        </div>
        <div className="chat">
          <div className="chat-log">
            {turns.length === 0 && (
              <p className="muted small">
                Ask a question above, or pick a suggestion. Answers are grounded in the gold
                tables via Genie.
              </p>
            )}
            {turns.map((t, i) => (
              <div key={i}>
                <div className="msg user">{t.q}</div>
                {t.pending ? (
                  <div className="msg bot">…thinking</div>
                ) : (
                  <GenieAnswer res={t.res!} />
                )}
              </div>
            ))}
          </div>
          <div className="chat-input">
            <input
              className="input"
              placeholder="Ask about claims, NTU, SLA, cycle time…"
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
    </Page>
  )
}

function GenieAnswer({ res }: { res: GenieResponse }) {
  if (!res.ok) {
    return <div className="msg bot">{res.error || 'No answer.'}</div>
  }
  const cols = res.rows && res.rows.length > 0 ? Object.keys(res.rows[0]) : []
  return (
    <div className="msg bot">
      {res.text && <div style={{ marginBottom: res.rows?.length ? 12 : 0 }}>{res.text}</div>}
      {res.rows && res.rows.length > 0 && (
        <div className="table-wrap">
          <table className="tabular">
            <thead>
              <tr>
                {cols.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {res.rows.slice(0, 50).map((row, i) => (
                <tr key={i}>
                  {cols.map((c) => (
                    <td key={c}>{String(row[c] ?? '')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {res.sql && (
        <details className="sql-block">
          <summary>Generated SQL</summary>
          <pre>{res.sql}</pre>
        </details>
      )}
    </div>
  )
}
