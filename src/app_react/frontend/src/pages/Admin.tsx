import { api, type CatalogItem } from '../lib/api'
import { useApi } from '../lib/useApi'
import { num } from '../lib/format'
import { Page, Card, Async } from '../components/ui'

export default function Admin() {
  const state = useApi(() => api.catalog(), [])
  return (
    <Page title="Admin Console" sub="Data products, governance & residency">
      <div className="grid-2">
        <Card title="Data-product catalog" sub="Gold serving objects & row counts">
          <Async state={{ ...state, data: state.data?.inventory ?? null }} empty="No catalog data">
            {(items: CatalogItem[]) => (
              <div className="table-wrap">
                <table className="tabular">
                  <thead>
                    <tr>
                      <th>Object</th>
                      <th>Description</th>
                      <th style={{ textAlign: 'right' }}>Rows</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((it) => (
                      <tr key={it.object}>
                        <td>
                          <code className="chip">{it.object}</code>
                        </td>
                        <td>{it.description}</td>
                        <td style={{ textAlign: 'right' }}>
                          {it.row_count != null ? num(it.row_count) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Async>
        </Card>

        <div className="stack">
          <Card title="Data residency">
            <p className="small">
              This demo runs on <strong>synthetic data only</strong> — no real PII. Production is
              targeted at <strong>eu-west-1 (Ireland)</strong>, which keeps all compute, storage and
              inference <strong>out of the USA</strong> per the residency requirement.
            </p>
            <p className="small muted">
              af-south-1 (Cape Town) is not a supported Databricks region; eu-west-1 is the
              spec's approved secondary. See docs/05_DEPLOYMENT.md.
            </p>
          </Card>
          <Card title="Agent evaluation">
            <dl className="kv">
              <dt>Citation groundedness</dt>
              <dd>1.00</dd>
              <dt>Discrepancy recall</dt>
              <dd>1.00</dd>
              <dt>No-hallucination</dt>
              <dd>1.00</dd>
            </dl>
            <p className="small muted mt">MLflow eval over seeded scenarios DS1–DS3.</p>
          </Card>
          <Card title="Physical layout">
            <dl className="kv">
              <dt>Catalog</dt>
              <dd>
                <code className="chip">elexon_app_for_settlement_acc_catalog</code>
              </dd>
              <dt>Schemas</dt>
              <dd>momentum_claims_&#123;bronze,silver,gold,ai,ops&#125;</dd>
              <dt>Model</dt>
              <dd>databricks-claude-sonnet-4-6</dd>
            </dl>
          </Card>
        </div>
      </div>
    </Page>
  )
}
