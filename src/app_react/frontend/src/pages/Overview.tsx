import { Link } from 'react-router-dom'
import { api, type Exec, type UwExec } from '../lib/api'
import { useApi } from '../lib/useApi'
import { Page, Card, Kpi } from '../components/ui'

/* Cross-domain Executive Overview — the app's front door. Underwriting and
   Claims portfolio health side by side, each linking into its domain. */
export default function Overview() {
  const claims = useApi(() => api.exec(), [])
  const uw = useApi(() => api.uwExec(), [])

  const c = claims.data
  const u = uw.data as UwExec | null
  const cx = c as Exec | null

  const pct = (v: number | null | undefined) => (v != null ? (v * 100).toFixed(1) : '—')
  const day = (v: number | null | undefined) => (v != null ? v.toFixed(1) : '—')

  // Per-domain status so a warehouse outage reads as an outage, not real zeros.
  const statusNote = (s: { loading: boolean; error: string | null }) =>
    s.loading ? (
      <span className="small muted">loading…</span>
    ) : s.error ? (
      <span className="pill pill-bad">⚠ couldn’t reach Databricks</span>
    ) : null

  return (
    <Page
      title="Executive Overview"
      sub="Momentum Life — new business & claims at a glance. Synthetic data · demo."
    >
      <div className="grid-2">
        {/* Underwriting */}
        <Card
          title="Underwriting — new business"
          right={
            <span className="chip-row" style={{ alignItems: 'center' }}>
              {statusNote(uw)}
              <Link to="/uw-exec" className="btn btn-outline btn-sm">Open →</Link>
            </span>
          }
        >
          <div className="kpi-grid">
            <Kpi label="Straight-through" value={pct(u?.stp_rate)} unit="%" foot="fast-track + tele" />
            <Kpi label="NTU rate" value={pct(u?.ntu_rate)} unit="%" foot="not taken up" />
            <Kpi label="Avg turnaround" value={day(u?.avg_cycle_days)} unit="days" foot="first-pass → decision" />
          </div>
          <div className="mt">
            <Link to="/underwriting" className="btn btn-primary btn-sm">Underwriting Co-Pilot</Link>{' '}
            <Link to="/uw-analytics" className="btn btn-ghost btn-sm">UW Analytics</Link>
          </div>
        </Card>

        {/* Claims */}
        <Card
          title="Claims — assessment"
          right={
            <span className="chip-row" style={{ alignItems: 'center' }}>
              {statusNote(claims)}
              <Link to="/exec" className="btn btn-outline btn-sm">Open →</Link>
            </span>
          }
        >
          <div className="kpi-grid">
            <Kpi label="Avg cycle time" value={day(cx?.kpis?.cycle_time_days)} unit="days" foot="lodge → decision" />
            <Kpi label="NTU rate" value={pct(cx?.kpis?.ntu_rate)} unit="%" foot="pre-lodge drop-off" />
            <Kpi label="SLA attainment"
                 value={cx?.kpis?.sla_attainment_pct != null ? cx.kpis.sla_attainment_pct.toFixed(1) : '—'}
                 unit="%" foot="within 20-day SLA" />
          </div>
          <div className="mt">
            <Link to="/copilot" className="btn btn-primary btn-sm">Claims Co-Pilot</Link>{' '}
            <Link to="/inbox" className="btn btn-ghost btn-sm">Claims Inbox</Link>
          </div>
        </Card>
      </div>

      <Card className="mt-lg" title="One platform" sub="Governed lakehouse · Mosaic AI · AI/BI · Apps">
        <p className="small">
          Both domains run on one Unity Catalog–governed lakehouse: a unified case view keyed
          on policy number, agentic AI assistants with Vector Search retrieval over unstructured
          notes and documents, natural-language Genie, and governed AI/BI reporting — no per-seat
          licence. Underwriting and claims share the same substrate.
        </p>
      </Card>
    </Page>
  )
}
