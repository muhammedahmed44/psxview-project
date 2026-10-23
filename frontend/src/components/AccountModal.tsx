import { useEffect, useRef, useState } from 'react'
import { authApi } from '../api'
import { useAuth } from '../context/AuthContext'
import type { AccountTab } from '../types'

interface Props {
  open: boolean
  tab: AccountTab
  onClose: () => void
}

// Step 1 = email/password, step 2 = 6-digit email code, step 3 = done.
export default function AccountModal({ open, tab, onClose }: Props) {
  const { setUser } = useAuth()
  const [step, setStep] = useState(1)
  const [curTab, setCurTab] = useState<AccountTab>(tab)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [challenge, setChallenge] = useState('') // token from the server after step 1
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const emailRef = useRef<HTMLInputElement>(null)
  const otpRefs = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => {
    if (open) {
      setStep(1)
      setCurTab(tab)
      setError('')
      setPassword('')
      requestAnimationFrame(() => emailRef.current?.focus())
    }
  }, [open, tab])

  if (!open) return null
  const isSignup = curTab === 'signup'

  async function submitCredentials() {
    setError('')
    setBusy(true)
    try {
      const res = isSignup
        ? await authApi.register(name, email, password)
        : await authApi.login(email, password)
      setChallenge(res.challenge_token)
      setStep(2)
      requestAnimationFrame(() => otpRefs.current[0]?.focus())
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function submitCode() {
    const code = otpRefs.current.map((i) => i?.value ?? '').join('')
    if (code.length !== 6) return setError('Enter all 6 digits')
    setError('')
    setBusy(true)
    try {
      const user = await authApi.verifyOtp(challenge, code)
      setUser(user) // the server already set the login cookie
      setStep(3)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function resend() {
    setError('')
    try {
      const res = await authApi.resendOtp(challenge)
      setChallenge(res.challenge_token)
      setError('New code sent.')
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div
      className="modal open"
      id="modal"
      role="dialog"
      aria-modal="true"
      aria-label="Account"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="card">
        {step === 1 && (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              void submitCredentials()
            }}
          >
            <div className="tabs" role="tablist">
              <button type="button" role="tab" aria-selected={!isSignup} onClick={() => setCurTab('login')}>
                Login
              </button>
              <button type="button" role="tab" aria-selected={isSignup} onClick={() => setCurTab('signup')}>
                Sign up
              </button>
            </div>
            {isSignup && (
              <>
                <label htmlFor="nm">Full name</label>
                <input id="nm" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required />
              </>
            )}
            <label htmlFor="em">Email</label>
            <input
              id="em"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              ref={emailRef}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <label htmlFor="pw">Password</label>
            <input
              id="pw"
              type="password"
              autoComplete={isSignup ? 'new-password' : 'current-password'}
              minLength={isSignup ? 8 : 1}
              maxLength={72}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {error && <p className="hint" role="alert" style={{ color: 'var(--down)' }}>{error}</p>}
            <button className="btn prime" type="submit" disabled={busy}>
              {busy ? 'Please wait…' : isSignup ? 'Create account' : 'Login'}
            </button>
          </form>
        )}

        {step === 2 && (
          <div>
            <h2 style={{ margin: '0 0 4px', fontSize: 20 }}>2-factor verification</h2>
            <p className="hint">Enter the 6-digit code sent to your email.</p>
            <div className="otp">
              {Array.from({ length: 6 }).map((_, i) => (
                <input
                  key={i}
                  maxLength={1}
                  inputMode="numeric"
                  aria-label={`Digit ${i + 1}`}
                  ref={(el) => {
                    otpRefs.current[i] = el
                  }}
                  onChange={(e) => {
                    if (e.target.value && otpRefs.current[i + 1]) otpRefs.current[i + 1]!.focus()
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Backspace' && !e.currentTarget.value && otpRefs.current[i - 1])
                      otpRefs.current[i - 1]!.focus()
                    if (e.key === 'Enter') void submitCode()
                  }}
                />
              ))}
            </div>
            {error && <p className="hint" role="alert" style={{ color: 'var(--down)' }}>{error}</p>}
            <button className="btn prime" onClick={() => void submitCode()} disabled={busy}>
              {busy ? 'Checking…' : 'Verify'}
            </button>
            <button type="button" className="linkbtn" onClick={() => void resend()}>
              Send a new code
            </button>
          </div>
        )}

        {step === 3 && (
          <div style={{ textAlign: 'center' }}>
            <h2 style={{ margin: '0 0 4px', fontSize: 20 }}>Verified</h2>
            <p className="hint">You are logged in.</p>
            <button className="btn prime" onClick={onClose}>
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  )
}