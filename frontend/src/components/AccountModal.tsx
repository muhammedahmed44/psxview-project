import { useEffect, useRef, useState } from 'react'
import { authApi, type AuthenticatorSetup } from '../api'
import { useAuth } from '../context/AuthContext'
import type { AccountTab } from '../types'

interface Props {
  open: boolean
  tab: AccountTab
  onClose: () => void
}

// Step 1 = password, step 2 = authenticator setup/check, step 3 = signed in.
export default function AccountModal({ open, tab, onClose }: Props) {
  const { setUser } = useAuth()
  const [step, setStep] = useState(1)
  const [curTab, setCurTab] = useState<AccountTab>(tab)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [challenge, setChallenge] = useState('')
  const [setup, setSetup] = useState<AuthenticatorSetup | null>(null)
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([])
  const [useRecovery, setUseRecovery] = useState(false)
  const [recoveryCode, setRecoveryCode] = useState('')
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
      setChallenge('')
      setSetup(null)
      setRecoveryCodes([])
      setUseRecovery(false)
      setRecoveryCode('')
      requestAnimationFrame(() => emailRef.current?.focus())
    }
  }, [open, tab])

  if (!open) return null
  const isSignup = curTab === 'signup'

  async function submitCredentials() {
    setError('')
    setBusy(true)
    try {
      const result = isSignup
        ? await authApi.register(name, email, password)
        : await authApi.login(email, password)
      setChallenge(result.challenge_token)
      setSetup(result.setup)
      setUseRecovery(false)
      setStep(2)
      requestAnimationFrame(() => otpRefs.current[0]?.focus())
    } catch (caught) {
      setError((caught as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function submitCode() {
    const code = useRecovery
      ? recoveryCode.trim()
      : otpRefs.current.map((input) => input?.value ?? '').join('')
    if ((!useRecovery && code.length !== 6) || (useRecovery && code.length < 10)) {
      setError(useRecovery ? 'Enter a complete recovery code' : 'Enter all 6 digits')
      return
    }
    setError('')
    setBusy(true)
    try {
      const result = await authApi.verifyTotp(challenge, code)
      setUser({ id: result.id, name: result.name, email: result.email })
      setRecoveryCodes(result.recovery_codes ?? [])
      setStep(3)
    } catch (caught) {
      setError((caught as Error).message)
    } finally {
      setBusy(false)
    }
  }

  function pasteAuthenticatorCode(value: string) {
    const digits = value.replace(/\D/g, '').slice(0, 6)
    if (digits.length !== 6) return
    otpRefs.current.forEach((input, index) => {
      if (input) input.value = digits[index]
    })
    otpRefs.current[5]?.focus()
  }

  async function copyText(value: string) {
    try {
      await navigator.clipboard.writeText(value)
    } catch {
      setError('Could not copy automatically. Select and copy it manually.')
    }
  }

  return (
    <div
      className="modal open"
      id="modal"
      role="dialog"
      aria-modal="true"
      aria-label="Account"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className={`card${setup && step === 2 ? ' authenticator-card' : ''}`}>
        {step === 1 && (
          <form
            onSubmit={(event) => {
              event.preventDefault()
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
                <input id="nm" autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} required />
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
              onChange={(event) => setEmail(event.target.value)}
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
              onChange={(event) => setPassword(event.target.value)}
              required
            />
            {error && <p className="hint auth-error" role="alert">{error}</p>}
            <button className="btn prime" type="submit" disabled={busy}>
              {busy ? 'Please wait…' : isSignup ? 'Create account' : 'Login'}
            </button>
          </form>
        )}

        {step === 2 && (
          <div>
            <h2 className="auth-title">
              {setup ? 'Set up Google Authenticator' : 'Authenticator verification'}
            </h2>
            {setup ? (
              <div className="auth-setup">
                <p className="hint">Scan this QR code with Google Authenticator, then enter the current 6-digit code.</p>
                <img className="auth-qr" src={setup.qr_code_data_url} alt="Google Authenticator setup QR code" />
                <p className="hint">Cannot scan it? Enter this setup key manually:</p>
                <div className="manual-key">
                  <code>{setup.manual_key}</code>
                  <button type="button" onClick={() => void copyText(setup.manual_key)}>Copy</button>
                </div>
              </div>
            ) : (
              <p className="hint">
                Enter the current 6-digit code from Google Authenticator.
              </p>
            )}

            {!useRecovery ? (
              <div className="otp">
                {Array.from({ length: 6 }).map((_, index) => (
                  <input
                    key={index}
                    maxLength={1}
                    inputMode="numeric"
                    autoComplete={index === 0 ? 'one-time-code' : 'off'}
                    aria-label={`Digit ${index + 1}`}
                    ref={(element) => {
                      otpRefs.current[index] = element
                    }}
                    onPaste={(event) => {
                      const pasted = event.clipboardData.getData('text')
                      if (pasted.replace(/\D/g, '').length >= 6) {
                        event.preventDefault()
                        pasteAuthenticatorCode(pasted)
                      }
                    }}
                    onChange={(event) => {
                      event.target.value = event.target.value.replace(/\D/g, '').slice(-1)
                      if (event.target.value && otpRefs.current[index + 1]) otpRefs.current[index + 1]!.focus()
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Backspace' && !event.currentTarget.value && otpRefs.current[index - 1])
                        otpRefs.current[index - 1]!.focus()
                      if (event.key === 'Enter') void submitCode()
                    }}
                  />
                ))}
              </div>
            ) : (
              <>
                <label htmlFor="recovery">Recovery code</label>
                <input
                  id="recovery"
                  autoComplete="one-time-code"
                  placeholder="XXXXX-XXXXX"
                  value={recoveryCode}
                  onChange={(event) => setRecoveryCode(event.target.value.toUpperCase())}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') void submitCode()
                  }}
                />
              </>
            )}

            {error && <p className="hint auth-error" role="alert">{error}</p>}
            <button className="btn prime" onClick={() => void submitCode()} disabled={busy}>
              {busy ? 'Checking…' : setup ? 'Confirm and sign in' : 'Verify'}
            </button>
            {!setup && (
              <button
                type="button"
                className="linkbtn"
                onClick={() => {
                  setUseRecovery((current) => !current)
                  setError('')
                }}
              >
                {useRecovery ? 'Use authenticator code' : 'Use a recovery code'}
              </button>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="auth-complete">
            <h2 className="auth-title">Verified</h2>
            {recoveryCodes.length > 0 ? (
              <>
                <p className="hint">
                  Save these recovery codes now. Each code works once if you lose access to your authenticator.
                </p>
                <div className="recovery-codes" aria-label="Recovery codes">
                  {recoveryCodes.map((code) => <code key={code}>{code}</code>)}
                </div>
                <button type="button" className="linkbtn" onClick={() => void copyText(recoveryCodes.join('\n'))}>
                  Copy all recovery codes
                </button>
              </>
            ) : (
              <p className="hint">You are logged in.</p>
            )}
            <button className="btn prime" onClick={onClose}>
              {recoveryCodes.length > 0 ? 'I saved the codes' : 'Close'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
