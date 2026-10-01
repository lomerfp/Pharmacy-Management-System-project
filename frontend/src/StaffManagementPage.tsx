import { useEffect, useState, type FormEvent } from 'react'
import { AlertTriangle, Check, LoaderCircle, Plus, Search, ShieldCheck, UserRoundX } from 'lucide-react'
import { apiDelete, apiGet, apiPatch, apiPost, ApiError } from './api'
import './operations.css'

type Role = { id: number; name: string; description: string; permissions: string[]; is_active: boolean }
type Staff = { id: number; username: string; email: string; display_name: string; role: number | null; is_active: boolean; date_joined: string }
type PageData<T> = { count: number; results: T[] }

export default function StaffManagementPage() {
  const [staff, setStaff] = useState<Staff[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [form, setForm] = useState({ username: '', display_name: '', email: '', password: '', role: '', is_active: true })

  async function load() {
    setLoading(true)
    setError('')
    try {
      const params = query ? `?search=${encodeURIComponent(query)}` : ''
      const [staffPage, rolePage] = await Promise.all([
        apiGet<PageData<Staff> | Staff[]>(`/staff/${params}`),
        apiGet<PageData<Role> | Role[]>('/roles/'),
      ])
      setStaff(Array.isArray(staffPage) ? staffPage : staffPage.results)
      setRoles((Array.isArray(rolePage) ? rolePage : rolePage.results).filter((role) => role.is_active))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load staff records.')
    } finally { setLoading(false) }
  }

  useEffect(() => { void load() }, [query])

  async function updateStaff(member: Staff, changes: Partial<Pick<Staff, 'role' | 'is_active'>>) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await apiPatch<Staff>(`/staff/${member.id}/`, changes)
      setNotice(`${member.display_name} updated.`)
      await load()
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.detail : cause instanceof Error ? cause.message : 'Could not update staff account.')
    } finally { setBusy(false) }
  }

  async function deactivate(member: Staff) {
    if (!window.confirm(`Deactivate ${member.display_name}? Their historical transactions will be preserved.`)) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await apiDelete(`/staff/${member.id}/`)
      setNotice(`${member.display_name} deactivated; history is preserved.`)
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not deactivate staff account.')
    } finally { setBusy(false) }
  }

  async function createStaff(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await apiPost<Staff>('/staff/', { ...form, role: Number(form.role) })
      setNotice(`Account for ${form.display_name} created.`)
      setForm({ username: '', display_name: '', email: '', password: '', role: '', is_active: true })
      setCreateOpen(false)
      await load()
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.detail : cause instanceof Error ? cause.message : 'Could not create staff account.')
    } finally { setBusy(false) }
  }

  return (
    <section className="data-page staff-page">
      <div className="staff-toolbar"><label className="search-control"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name, username, or email" aria-label="Search staff" /></label><button className="primary-action" onClick={() => setCreateOpen((open) => !open)}><Plus size={16} /> Add staff</button></div>
      {error && <div className="inline-error" role="alert"><AlertTriangle size={16} />{error}</div>}
      {notice && <div className="staff-notice" role="status"><Check size={15} />{notice}</div>}
      {createOpen && <form className="staff-create-form" onSubmit={createStaff}><h2>Create staff account</h2><div className="staff-form-grid"><label>Username<input value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} required /></label><label>Display name<input value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} required /></label><label>Email<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required /></label><label>Temporary password<input type="password" minLength={12} value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required /></label><label>Role<select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} required><option value="">Select role</option>{roles.map((role) => <option value={role.id} key={role.id}>{role.name}</option>)}</select></label></div><div className="staff-form-actions"><button type="button" className="secondary-action" onClick={() => setCreateOpen(false)}>Cancel</button><button className="primary-action" disabled={busy} type="submit">Create account</button></div></form>}
      {loading ? <div className="data-loading"><LoaderCircle size={19} className="spin" /> Loading staff records</div> : staff.length === 0 ? <div className="data-empty"><ShieldCheck size={21} /><strong>No staff accounts found</strong><span>Public signup requests appear as inactive accounts until an administrator assigns a role and activates access.</span></div> : <div className="table-wrap"><table><thead><tr><th>Staff member</th><th>Role</th><th>Access</th><th>Account actions</th></tr></thead><tbody>{staff.map((member) => <tr key={member.id}><td><strong>{member.display_name}</strong><small>{member.username} · {member.email}</small></td><td><select className="staff-role-select" aria-label={`Role for ${member.display_name}`} value={member.role ?? ''} disabled={busy} onChange={(event) => void updateStaff(member, { role: event.target.value ? Number(event.target.value) : null })}><option value="">No role</option>{roles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}</select></td><td><span className={`status-label ${member.is_active ? 'active' : 'inactive'}`}>{member.is_active ? 'Active' : 'Pending / inactive'}</span></td><td><div className="staff-row-actions"><button className="staff-action" disabled={busy || !member.role || member.is_active} onClick={() => void updateStaff(member, { is_active: true })}><Check size={14} /> Activate</button><button className="staff-action danger" disabled={busy || !member.is_active} onClick={() => void deactivate(member)}><UserRoundX size={14} /> Remove access</button></div></td></tr>)}</tbody></table></div>}
      <p className="staff-footnote"><ShieldCheck size={14} /> Removing staff deactivates sign-in and preserves historical records. Assign each account only the permissions needed for its work.</p>
    </section>
  )
}

