/* Typed, same-origin fetch client for the Momentum Claims API.
   Every call resolves to data or throws a friendly Error; the UI wraps
   these with useApi() so it never crashes on empty/error responses. */

/* ---------------- Types (mirror the backend contract) ---------------- */

export interface Health {
  status: string
  app?: string
  db_connected: boolean
  db_message: string
}

export interface InboxClaim {
  claim_no: string
  claim_type: string
  state: string
  province: string
  assessor: string | null
  decision: string | null
  risk_score: number | null
  occupation_mismatch: boolean | null
  early_claim_flag: boolean | null
  reqs_received: number | null
  reqs_total: number | null
  sum_assured: number | null
  benefit_status: string | null
  event_date: string | null
  lodge_date: string | null
  days_in_stage: number | null
  high_risk: boolean | null
}

export interface ClaimRow {
  claim_no: string
  claim_type?: string
  state?: string
  province?: string
  assessor?: string | null
  decision?: string | null
  occupation_at_inception?: string | null
  occupation_at_claim?: string | null
  occupation_mismatch?: boolean | null
  early_claim_flag?: boolean | null
  benefit_type?: string | null
  sum_assured?: number | null
  benefit_status?: string | null
  loadings?: string | null
  exclusions?: string | null
  policy_status?: string | null
  inception_date?: string | null
  event_date?: string | null
  lodge_date?: string | null
  tp_summary?: string | null
  document_ids?: string | null
  reqs_received?: number | null
  reqs_total?: number | null
  outstanding_codes?: string | null
  risk_score?: number | null
  policy_no?: string | null
  [k: string]: unknown
}

export interface Requirement {
  code: string
  description: string
  status: string
  requested_ts: string | null
  received_ts: string | null
}

export interface ClaimDocument {
  doc_id: string
  doc_type: string
  filenet_ref: string | null
  parsed_text: string | null
}

export interface ClaimEvent {
  event: string
  event_ts: string | null
}

export interface ThirdParty {
  source: string
  result_summary: string | null
  checked_ts: string | null
}

export interface ClaimDetail {
  row: ClaimRow | null
  requirements: Requirement[]
  documents: ClaimDocument[]
  events: ClaimEvent[]
  third_party: ThirdParty[]
}

export interface Synopsis {
  claim_no: string
  markdown: string
  discrepancies: string[]
  citations: string[]
  recommendation: string
  source?: string
}

export interface GenieResponse {
  ok: boolean
  text?: string
  sql?: string
  rows?: Record<string, unknown>[]
  conversation_id?: string
  error?: string
}

export interface NtuFunnelRow {
  claim_type: string
  state: string
  n_claims: number
  n_ntu: number
}
export interface AtRiskRow {
  claim_no: string
  policy_no: string
  claim_type: string
  event_date: string | null
  days_outstanding: number | null
  n_outstanding_reqs: number | null
  drop_off_propensity: number | null
}
export interface Ntu {
  funnel: NtuFunnelRow[]
  at_risk: AtRiskRow[]
}

export interface OpsMetric {
  claim_no: string
  claim_type: string
  assessor: string | null
  lodge_ts: string | null
  decided_ts: string | null
  days_lodge_to_decision: number | null
  sla_days: number | null
  sla_breach: boolean | null
}
export interface Throughput {
  assessor: string
  n_decided: number
}
export interface Ops {
  metrics: OpsMetric[]
  throughput: Throughput[]
}

export interface ExecKpis {
  cycle_time_days: number | null
  ntu_rate: number | null
  sla_attainment_pct: number | null
}
export interface DecisionSplit {
  claim_type: string
  decision: string
  n: number
  pct: number
}
export interface ProvinceRow {
  province: string
  n_claims: number
}
export interface Exec {
  kpis: ExecKpis
  decision_split: DecisionSplit[]
  by_province: ProvinceRow[]
}

export interface RequirementAnalytic {
  claim_type: string
  code: string
  description: string
  n_total: number
  n_received: number
  n_outstanding: number
  pct_received: number
  avg_days_to_receive: number | null
}

export interface CatalogItem {
  object: string
  description: string
  row_count: number | null
}

/* ---------------- Fetch helpers ---------------- */

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`${path} → ${res.status} ${res.statusText}`)
  return (await res.json()) as T
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${path} → ${res.status} ${res.statusText}`)
  return (await res.json()) as T
}

export const api = {
  health: () => get<Health>('/api/health'),
  inbox: () => get<{ claims: InboxClaim[] }>('/api/inbox'),
  claim: (no: string) => get<ClaimDetail>(`/api/claim/${encodeURIComponent(no)}`),
  synopsis: (no: string) => get<Synopsis>(`/api/claim/${encodeURIComponent(no)}/synopsis`),
  copilot: (claim_no: string, question: string) =>
    post<{ answer: string }>('/api/copilot', { claim_no, question }),
  genie: (question: string, conversation_id?: string) =>
    post<GenieResponse>('/api/genie', { question, conversation_id }),
  ntu: () => get<Ntu>('/api/ntu'),
  ops: () => get<Ops>('/api/ops'),
  exec: () => get<Exec>('/api/exec'),
  requirements: () => get<{ analytics: RequirementAnalytic[] }>('/api/requirements'),
  assessors: () => get<{ assessors: string[] }>('/api/assessors'),
  catalog: () => get<{ inventory: CatalogItem[] }>('/api/admin/catalog'),
  action: (claim_no: string, user_role: string, action: string, payload = '') =>
    post<{ ok: boolean; error?: string }>('/api/action', {
      claim_no,
      user_role,
      action,
      payload,
    }),
}
