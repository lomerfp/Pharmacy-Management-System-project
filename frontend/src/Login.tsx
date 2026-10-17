import { useState, type FormEvent } from 'react'
import { ArrowLeft, ArrowRight, LockKeyhole, Pill } from 'lucide-react'
import { ApiError, confirmPasswordReset, login, requestPasswordReset, submitSignup, type StaffSummary } from './api'
import './login.css'

type Props = { onLogin: (staff: StaffSummary) => void }

export default function Login({ onLogin }: Props) {
  const [email, setEmail] = useState('')
  const [signupUsername, setSignupUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [resetMode, setResetMode] = useState<'login' | 'request' | 'confirm' | 'signup'>('login')
  const [resetEmail, setResetEmail] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [notice, setNotice] = useState('')
  const [signupEmail, setSignupEmail] = useState('')
  const [signupName, setSignupName] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      onLogin(await login(email.trim(), password))
    } catch (cause) {
      setError(cause instanceof ApiError && cause.status === 401 ? 'That email or password is not correct.' : cause instanceof Error ? cause.message : 'Sign-in failed. Check that the API is available.')
    } finally {
      setBusy(false)
    }
  }

  async function requestReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await requestPasswordReset(resetEmail.trim())
      setNotice('If an active account matches that address, reset instructions have been sent.')
      setResetMode('confirm')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Password reset request failed.')
    } finally { setBusy(false) }
  }

  async function confirmReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await confirmPasswordReset(resetToken.trim(), newPassword)
      setNotice('Password reset. Sign in with your new password.')
      setResetMode('login')
      setPassword('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Password reset could not be confirmed.')
    } finally { setBusy(false) }
  }

  async function signUp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const result = await submitSignup({ username: signupUsername.trim(), email: signupEmail.trim(), display_name: signupName.trim(), password })
      setNotice(result.detail)
      setResetMode('login')
      setPassword('')
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.detail : cause instanceof Error ? cause.message : 'Could not submit the signup request.')
    } finally { setBusy(false) }
  }

  return (
    <main className="login-screen">
      <div className="login-left">
        <div className="login-brand"><span className="brand-mark"><Pill size={19} /></span><span><strong>Goodwell</strong><small>PHARMACY MANAGEMENT SYSTEM</small></span></div>
        <div className="login-title"><span className="eyebrow">SINGLE LOCATION · KAMPALA</span><h1>Good to have<br />you back.</h1><p>Sign in with your account, or request staff access for administrator approval.</p></div>
        <div className="login-context"><span className="login-context-mark"><LockKeyhole size={18} /></span><span><strong>Protected staff workspace</strong><small>Access is controlled by your assigned role.</small></span></div>
        <footer>UGX <i>·</i> Africa/Kampala <span>Academic project · 2026/27</span><span>© Group 8 Members · 2026</span></footer>
      </div>
      <section className="login-panel" aria-labelledby="login-heading">
        <div className="login-form-wrap">
          {resetMode !== 'login' && <button className="login-back" onClick={() => { setResetMode('login'); setError(''); setNotice('') }}><ArrowLeft size={14} /> Back to sign in</button>}
          <span className="eyebrow">{resetMode === 'login' ? 'STAFF ACCESS' : resetMode === 'signup' ? 'NEW STAFF REQUEST' : 'ACCOUNT RECOVERY'}</span>
          <h2 id="login-heading">{resetMode === 'login' ? 'Sign in' : resetMode === 'request' ? 'Reset password' : resetMode === 'confirm' ? 'Choose a new password' : 'Request an account'}</h2>
          <p className="login-subtitle">{resetMode === 'login' ? 'Use your pharmacy account credentials.' : resetMode === 'request' ? 'We will send reset instructions to your staff email.' : resetMode === 'confirm' ? 'Enter the single-use code from your reset email.' : 'An administrator must assign your role and activate access.'}</p>
          {notice && <p className="login-notice" role="status">{notice}</p>}
          {resetMode === 'login' && <form onSubmit={submit}>
            <label htmlFor="email">Staff email</label>
            <input autoComplete="email" id="email" name="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoFocus />
            <div className="password-label"><label htmlFor="password">Password</label><button type="button" onClick={() => { setResetMode('request'); setResetEmail(''); setError(''); setNotice('') }}>Forgot password?</button></div>
            <input autoComplete="current-password" id="password" name="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            {error && <p className="login-error" role="alert">{error}</p>}
            <button className="login-submit" type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}{!busy && <ArrowRight size={17} />}</button>
          </form>}
          {resetMode === 'request' && <form onSubmit={requestReset}>
            <label htmlFor="reset-email">Staff email</label><input autoComplete="email" id="reset-email" type="email" value={resetEmail} onChange={(event) => setResetEmail(event.target.value)} required />
            {error && <p className="login-error" role="alert">{error}</p>}
            <button className="login-submit" type="submit" disabled={busy}>{busy ? 'Sending…' : 'Send reset instructions'}{!busy && <ArrowRight size={17} />}</button>
          </form>}
          {resetMode === 'confirm' && <form onSubmit={confirmReset}>
            <label htmlFor="reset-token">Single-use reset code</label><input id="reset-token" value={resetToken} onChange={(event) => setResetToken(event.target.value)} required />
            <label htmlFor="new-password">New password</label><input id="new-password" type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={12} required />
            {error && <p className="login-error" role="alert">{error}</p>}
            <button className="login-submit" type="submit" disabled={busy}>{busy ? 'Updating…' : 'Set new password'}{!busy && <ArrowRight size={17} />}</button>
          </form>}
          {resetMode === 'signup' && <form onSubmit={signUp}>
            <label htmlFor="signup-username">Username</label><input autoComplete="username" id="signup-username" value={signupUsername} onChange={(event) => setSignupUsername(event.target.value)} required />
            <label htmlFor="signup-name">Full name</label><input id="signup-name" value={signupName} onChange={(event) => setSignupName(event.target.value)} required />
            <label htmlFor="signup-email">Staff email</label><input id="signup-email" type="email" autoComplete="email" value={signupEmail} onChange={(event) => setSignupEmail(event.target.value)} required />
            <label htmlFor="signup-password">Password</label><input id="signup-password" type="password" autoComplete="new-password" minLength={12} value={password} onChange={(event) => setPassword(event.target.value)} required />
            {error && <p className="login-error" role="alert">{error}</p>}
            <button className="login-submit" type="submit" disabled={busy}>{busy ? 'Submitting…' : 'Request access'}{!busy && <ArrowRight size={17} />}</button>
          </form>}
          {resetMode === 'login' && <p className="login-help">Need access? <button type="button" className="text-action" onClick={() => { setResetMode('signup'); setError(''); setNotice('') }}>Request an account</button>. Password reset is also available above.</p>}
        </div>
      </section>
    </main>
  )
}
