import type { ReactNode } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { RoleProvider, useRole, ROLES, type Role } from './lib/roleContext'
import { useApi } from './lib/useApi'
import { api } from './lib/api'
import Inbox from './pages/Inbox'
import ClaimDetail from './pages/ClaimDetail'
import Copilot from './pages/Copilot'
import NtuOps from './pages/NtuOps'
import ExecView from './pages/ExecView'
import Fraud from './pages/Fraud'
import Admin from './pages/Admin'
import Underwriting from './pages/Underwriting'
import UwAnalytics from './pages/UwAnalytics'

const LOGO = '/momentum_life_logo.png'

interface NavItem {
  to: string
  label: string
  icon: ReactNode
  roles?: Role[]
}

/* Inline stroke icons — 1.75px, currentColor, 18px grid (Lucide-style). */
const I = {
  exec: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v16a2 2 0 0 0 2 2h16" />
      <path d="M7 15l3.5-4 3 2.5L21 7" />
    </svg>
  ),
  inbox: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 12h-6l-2 3h-4l-2-3H2" />
      <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
    </svg>
  ),
  copilot: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3a2 2 0 0 1 2 2v1h3a2 2 0 0 1 2 2v3h1a2 2 0 0 1 0 4h-1v3a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-3H4a2 2 0 0 1 0-4h1V8a2 2 0 0 1 2-2h3V5a2 2 0 0 1 2-2z" />
      <circle cx="9" cy="12" r="1" fill="currentColor" stroke="none" />
      <circle cx="15" cy="12" r="1" fill="currentColor" stroke="none" />
    </svg>
  ),
  ntu: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="M7 14l4-4 3 3 5-6" />
    </svg>
  ),
  fraud: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M12 8v4" />
      <circle cx="12" cy="15.5" r="0.5" fill="currentColor" stroke="currentColor" />
    </svg>
  ),
  admin: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v6c0 1.66 3.58 3 8 3s8-1.34 8-3V5" />
      <path d="M4 11v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6" />
    </svg>
  ),
  uw: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 12l2 2 4-4" />
      <path d="M12 3a2 2 0 0 1 1 .27l6 3.46A2 2 0 0 1 20 8.46v3.54c0 4.5-3 8-8 9.5-5-1.5-8-5-8-9.5V8.46a2 2 0 0 1 1-1.73l6-3.46A2 2 0 0 1 12 3z" />
    </svg>
  ),
  uwChart: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <rect x="7" y="11" width="3" height="6" rx="0.5" />
      <rect x="12" y="7" width="3" height="10" rx="0.5" />
      <rect x="17" y="13" width="3" height="4" rx="0.5" />
    </svg>
  ),
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Co-Pilots',
    items: [
      { to: '/underwriting', label: 'Underwriting Co-Pilot', icon: I.uw },
      { to: '/copilot', label: 'Claims Co-Pilot', icon: I.copilot },
    ],
  },
  {
    label: 'Underwriting',
    items: [{ to: '/uw-analytics', label: 'UW Analytics', icon: I.uwChart }],
  },
  {
    label: 'Claims',
    items: [
      { to: '/exec', label: 'Executive View', icon: I.exec },
      { to: '/', label: 'Claims Inbox', icon: I.inbox },
      { to: '/ntu', label: 'NTU / Ops', icon: I.ntu },
      { to: '/fraud', label: 'Fraud Workbench', icon: I.fraud },
    ],
  },
  {
    label: 'Platform',
    items: [{ to: '/admin', label: 'Admin Console', icon: I.admin }],
  },
]

function ConnDot() {
  const { data } = useApi(() => api.health(), [])
  const ok = data?.db_connected
  const label = data == null ? 'checking…' : ok ? 'Connected' : 'Demo mode'
  const cls = data == null ? 'dot' : ok ? 'dot ok' : 'dot bad'
  return (
    <span className="conn" title={data?.db_message || ''}>
      <span className={cls} />
      {label}
    </span>
  )
}

function RoleSwitch() {
  const { role, setRole } = useRole()
  return (
    <label className="role-switch">
      <span className="role-switch-label">View as</span>
      <select
        className="role-select"
        value={role}
        onChange={(e) => setRole(e.target.value as Role)}
      >
        {ROLES.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
    </label>
  )
}

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-chip">
          <img src={LOGO} alt="Momentum Life" />
        </span>
        <span className="brand-text">
          Momentum Life
          <small>Underwriting & Claims</small>
        </span>
      </div>
      {NAV_GROUPS.map((g) => (
        <nav className="nav-group" key={g.label}>
          <div className="nav-group-label">{g.label}</div>
          {g.items.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === '/'}
              className={({ isActive }) => 'nav-chip' + (isActive ? ' active' : '')}
            >
              <span className="ico" aria-hidden="true">
                {n.icon}
              </span>
              <span className="nav-label">{n.label}</span>
            </NavLink>
          ))}
        </nav>
      ))}
      <div className="sidebar-foot">
        <div className="small">Assessment Analytics Portal</div>
        <div className="small muted">Synthetic data · demo</div>
      </div>
    </aside>
  )
}

function Shell() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main">
        <header className="topbar">
          <div className="title">
            <h1>Momentum Life</h1>
            <div className="small muted">Underwriting & Claims — Intelligence Portal</div>
          </div>
          <div className="topbar-right">
            <ConnDot />
            <RoleSwitch />
          </div>
        </header>
        <Routes>
          <Route path="/" element={<Inbox />} />
          <Route path="/claim/:claimNo" element={<ClaimDetail />} />
          <Route path="/copilot" element={<Copilot />} />
          <Route path="/ntu" element={<NtuOps />} />
          <Route path="/exec" element={<ExecView />} />
          <Route path="/fraud" element={<Fraud />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/underwriting" element={<Underwriting />} />
          <Route path="/uw-analytics" element={<UwAnalytics />} />
        </Routes>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <RoleProvider>
      <Shell />
    </RoleProvider>
  )
}
