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

const LOGO = './momentum_life_logo.png'

interface NavItem {
  to: string
  label: string
  roles?: Role[]
}

const NAV: NavItem[] = [
  { to: '/', label: 'Claims Inbox' },
  { to: '/copilot', label: 'AI Copilot' },
  { to: '/ntu', label: 'NTU / Ops' },
  { to: '/exec', label: 'Executive View' },
  { to: '/fraud', label: 'Fraud Workbench' },
  { to: '/admin', label: 'Admin Console' },
]

function ConnDot() {
  const { data } = useApi(() => api.health(), [])
  const ok = data?.db_connected
  const label = data == null ? 'checking…' : ok ? 'Connected' : 'Demo mode'
  const cls = data == null ? 'dot' : ok ? 'dot dot-good' : 'dot dot-warn'
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
    <div className="role-switch">
      <span className="small muted">View as</span>
      <select
        className="select"
        value={role}
        onChange={(e) => setRole(e.target.value as Role)}
      >
        {ROLES.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
    </div>
  )
}

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src={LOGO} alt="Momentum Life" />
      </div>
      <nav className="nav-group">
        <div className="nav-group-label">Claims</div>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.to === '/'}
            className={({ isActive }) => 'nav-chip' + (isActive ? ' active' : '')}
          >
            {n.label}
          </NavLink>
        ))}
      </nav>
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
            <h1>Claims Processing</h1>
            <div className="small muted">Momentum Life — Assessment Analytics Portal</div>
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
