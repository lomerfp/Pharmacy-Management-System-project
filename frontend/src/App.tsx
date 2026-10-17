import { useEffect, useState } from 'react'
import {
  Activity, Boxes, ClipboardList, FileBarChart2, LayoutDashboard,
  LogOut, Menu, Pill, Settings, ShieldCheck, ShoppingCart, Truck, Users, X,
} from 'lucide-react'
import { getCurrentStaff, logout, type StaffSummary } from './api'
import Login from './Login'
import { DashboardPage, InventoryPage, PointOfSalePage, ReportsPage } from './OperationsPages'
import StaffManagementPage from './StaffManagementPage'
import './page-navigation.css'

type Page = 'Overview' | 'Inventory' | 'Purchasing' | 'Prescriptions' | 'Point of sale' | 'Reports' | 'Staff & access' | 'Settings'

const navigation: { label: Page; icon: typeof LayoutDashboard }[] = [
  { label: 'Overview', icon: LayoutDashboard }, { label: 'Inventory', icon: Boxes },
  { label: 'Purchasing', icon: Truck }, { label: 'Prescriptions', icon: ClipboardList },
  { label: 'Point of sale', icon: ShoppingCart }, { label: 'Reports', icon: FileBarChart2 },
  { label: 'Staff & access', icon: Users }, { label: 'Settings', icon: Settings },
]

const pagePermission: Partial<Record<Page, string>> = {
  Overview: 'dashboard.read',
  Inventory: 'inventory.read', Purchasing: 'purchasing.read',
  Prescriptions: 'prescriptions.read', 'Point of sale': 'sales.checkout',
  Reports: 'reports.read', 'Staff & access': 'staff.manage', Settings: 'settings.manage',
}

export default function App() {
  const [page, setPage] = useState<Page>('Overview')
  const [menuOpen, setMenuOpen] = useState(false)
  const [staff, setStaff] = useState<StaffSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    getCurrentStaff().then((current) => {
      if (mounted) setStaff(current)
    }).finally(() => {
      if (mounted) setLoading(false)
    })
    return () => { mounted = false }
  }, [])

  useEffect(() => {
    if (!staff) return
    if (!staff.permissions.includes('dashboard.read') && page === 'Overview') {
      const landingPage = staff.permissions.includes('sales.checkout') ? 'Point of sale' : staff.permissions.includes('inventory.read') ? 'Inventory' : 'Staff & access'
      setPage(landingPage)
    }
  }, [staff, page])

  if (loading) return <div className="app-loading"><span className="loading-mark"><Pill size={19} /></span><span>Connecting to pharmacy workspace</span></div>
  if (!staff) return <Login onLogin={setStaff} />

  const visibleNavigation = navigation.filter(({ label }) => !pagePermission[label] || staff.permissions.includes(pagePermission[label]!))
  const initials = staff.display_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
  const today = new Intl.DateTimeFormat('en-UG', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric', timeZone: 'Africa/Kampala' }).format(new Date()).toUpperCase()

  async function signOut() {
    try { await logout() } finally { setStaff(null); setPage('Overview') }
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`} aria-label="Main navigation">
        <div className="brand-lockup">
          <div className="brand-mark"><Pill size={19} strokeWidth={2.2} /></div>
          <div><strong>{import.meta.env.VITE_PHARMACY_NAME || 'Goodwell'}</strong><span>PHARMACY MANAGEMENT SYSTEM</span></div>
          <button className="icon-button close-menu" aria-label="Close navigation" onClick={() => setMenuOpen(false)}><X size={19} /></button>
        </div>
        <div className="location-label">SINGLE LOCATION <span className="online-dot" /></div>
        <nav className="nav-list">
          {visibleNavigation.map(({ label, icon: Icon }) => (
            <button key={label} className={`nav-item ${page === label ? 'active' : ''}`} onClick={() => { setPage(label); setMenuOpen(false) }}>
              <Icon size={18} strokeWidth={1.9} /><span>{label}</span>
              {label === 'Point of sale' && <span className="nav-shortcut">F2</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="access-note"><ShieldCheck size={16} /><span>Access is role-controlled</span></div>
          <button className="profile-button" onClick={signOut} aria-label="Sign out">
            <span className="avatar">{initials}</span><span className="profile-text"><strong>{staff.display_name}</strong><small>{staff.role || 'Staff'}</small></span><LogOut size={16} />
          </button>
        </div>
      </aside>
      {menuOpen && <button className="scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
      <main className="main-area">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMenuOpen(true)}><Menu size={21} /></button>
          <div className="crumbs">Workspace <span>/</span> <strong>{page}</strong></div>
          <div className="topbar-right"><span className="date-label">{today}</span><span className="avatar top-avatar">{initials}</span></div>
        </header>
        <div className="page-content">
          <div className="page-heading">
            <div><span className="eyebrow">PHARMACY CONTROL ROOM</span><h1>{page}</h1><p>Goodwell Community Pharmacy <span className="heading-divider">/</span> Kampala</p></div>
            {staff.permissions.includes('sales.checkout') && <button className="primary-action" onClick={() => setPage('Point of sale')}><ShoppingCart size={17} /> New sale</button>}
          </div>
          <nav className="page-section-nav" aria-label="Workspace pages">
            {visibleNavigation.map(({ label, icon: Icon }) => (
              <button
                key={label}
                type="button"
                className={page === label ? 'page-section-active' : ''}
                aria-current={page === label ? 'page' : undefined}
                onClick={() => { setPage(label); setMenuOpen(false) }}
              >
                <Icon size={15} strokeWidth={1.9} />
                <span>{label}</span>
              </button>
            ))}
          </nav>
          {page === 'Inventory' ? <InventoryPage /> : page === 'Point of sale' ? <PointOfSalePage /> : page === 'Reports' ? <ReportsPage /> : page === 'Staff & access' ? <StaffManagementPage /> : page === 'Overview' ? (
            <DashboardPage onNavigate={(target) => setPage(target)} />
          ) : (
            <section className="module-empty"><div className="empty-glyph"><Pill size={23} /></div><span className="eyebrow">MODULE FOUNDATION</span><h2>{page}</h2><p>This module is part of the implementation sequence. No sample business records are shown; this page will connect to persisted API data as its workflow is built.</p><button className="secondary-action" onClick={() => setPage('Overview')}>Back to overview</button></section>
          )}
          <footer className="page-footer"><span><ShieldCheck size={14} /> Signed in as {staff.role || 'staff'}</span><span><Activity size={14} /> UGX <i>·</i> Africa/Kampala</span><span>Academic project <i>·</i> 2026/27</span><span>© Group 8 Members · 2026</span></footer>
        </div>
      </main>
    </div>
  )
}
