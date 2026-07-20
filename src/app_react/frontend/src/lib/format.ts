/* Formatting + small helpers shared across pages. */

const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

/** ZAR currency, e.g. R1,800,000 */
export function zar(value: number | null | undefined): string {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const n = Math.round(Number(value))
  return 'R' + n.toLocaleString('en-ZA')
}

/** Readable date, e.g. 20 May 2026. Accepts ISO date / timestamp. */
export function fmtDate(value: string | null | undefined): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) {
    // Try bare YYYY-MM-DD
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
    if (m) return `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}`
    return String(value)
  }
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`
}

/** Readable date-time, e.g. 20 May 2026, 14:30 */
export function fmtDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return fmtDate(value)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}, ${hh}:${mm}`
}

export function pct(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const n = Number(value)
  // Accept either 0-1 fractions or 0-100 percentages
  const v = n <= 1 ? n * 100 : n
  return `${v.toFixed(digits)}%`
}

export function num(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(Number(value))) return '—'
  return Number(value).toLocaleString('en-ZA', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

/** Title-case a snake/lower string, e.g. "pre_lodge" -> "Pre Lodge" */
export function titleCase(s: string | null | undefined): string {
  if (!s) return '—'
  return String(s)
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export function isTruthy(v: unknown): boolean {
  if (v === true) return true
  if (typeof v === 'number') return v !== 0
  if (typeof v === 'string') return ['true', 't', '1', 'yes', 'y'].includes(v.toLowerCase())
  return false
}
