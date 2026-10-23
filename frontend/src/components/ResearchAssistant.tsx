import { useState } from 'react'
import { researchApi, type ResearchReply } from '../api'
import { useAuth } from '../context/AuthContext'

export default function ResearchAssistant() {
  const { user } = useAuth()
  const [question, setQuestion] = useState('')
  const [reply, setReply] = useState<ResearchReply | null>(null)
  const [busy, setBusy] = useState(false)
  const ask = async () => { if (!question.trim()) return; setBusy(true); try { setReply(await researchApi.ask(question)); setQuestion('') } finally { setBusy(false) } }
  return <section className="research-card" aria-labelledby="research-title">
    <div><span className="section-kicker">RESEARCH DESK</span><h2 id="research-title">Ask the PSX research assistant</h2><p className="section-caption">Ask about a company, price context, or stored financial news. Answers show their evidence.</p></div>
    <div className="research-input"><input value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => e.key === 'Enter' && void ask()} placeholder="e.g. What is happening with OGDC?" /><button className="btn prime" onClick={() => void ask()} disabled={busy}>{busy ? 'Researching…' : 'Ask'}</button></div>
    {reply && <div className="research-answer"><p>{reply.answer}</p><small>{user ? 'Saved to your authenticated session when a conversation is selected.' : 'Guest mode: this answer is temporary and is not saved.'}</small><div className="citation-list"><b>Evidence</b>{reply.citations.map((c, i) => <span key={i}>[{i + 1}] {c.title} · {c.date || 'date unavailable'} · {c.provenance}</span>)}</div></div>}
  </section>
}
