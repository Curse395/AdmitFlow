import { useEffect, useRef } from 'react'
import { ArrowUp, Check, CircleAlert, Sparkles, X } from 'lucide-react'

const prompts = [
  'Where is the largest funnel drop-off?',
  'Which programme has the strongest enrolment rate?',
  'How many enrolments are forecast at H4?',
  'Which campaign source has the most applications?',
]

export default function AssistantPanel({ configured, question, setQuestion, answer, loading, error, onAsk, onClose }) {
  const inputRef = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  return (
    <div className="assistant-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <aside className="assistant-drawer" role="dialog" aria-modal="true" aria-labelledby="assistant-title">
        <header className="assistant-drawer-header">
          <div className="assistant-heading-mark"><Sparkles size={18} /></div>
          <div><p className="eyebrow">Admission intelligence</p><h2 id="assistant-title">Ask AdmitFlow</h2></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Close AI assistant"><X size={18} /></button>
        </header>

        <div className="assistant-provider-status">
          <span className={`status-dot ${configured ? 'is-live' : 'is-idle'}`} />
          <span>{configured ? 'Groq provider connected' : 'AI provider not configured'}</span>
          <span className="provider-lock">Server-side</span>
        </div>

        <div className="assistant-drawer-content" aria-live="polite">
          {!answer && !loading && !error && (
            <div className="assistant-welcome">
              <span className="assistant-orb"><Sparkles size={24} /></span>
              <h3>Make your next decision with context.</h3>
              <p>Ask about funnel performance, programme outcomes, campaigns, cohorts, forecasts, or scenarios.</p>
              {!configured && <div className="assistant-config-note"><CircleAlert size={16} /><span>Set <code>GROQ_API_KEY</code> in the backend environment to enable live answers. No question is sent until configured.</span></div>}
              <div className="assistant-prompts">
                {prompts.map((prompt) => <button key={prompt} type="button" onClick={() => onAsk(prompt)} disabled={!configured}>{prompt}<ArrowUp size={14} /></button>)}
              </div>
            </div>
          )}
          {loading && <div className="assistant-thinking"><span className="thinking-spark"><Sparkles size={17} /></span><div><strong>Reading the admission data</strong><p>Checking relevant aggregates and preparing a sourced answer.</p></div><span className="thinking-dots"><i /><i /><i /></span></div>}
          {error && <div className="assistant-error" role="alert"><CircleAlert size={18} /><div><strong>Couldn’t complete that answer</strong><p>{error}</p>{!configured && <small>Configure the backend provider key and restart the API.</small>}</div></div>}
          {answer && <article className="assistant-answer-card">
            <div className="answer-badge"><Check size={13} /> Grounded response</div>
            <p className="assistant-answer-text">{answer.answer}</p>
            <div className="answer-sources"><span>Data references</span><div>{answer.data_used.map((source) => <span className="source-chip" key={source}>{source}</span>)}</div></div>
            {answer.follow_up_questions?.length > 0 && <div className="answer-followups"><span>Continue exploring</span>{answer.follow_up_questions.map((followup) => <button key={followup} type="button" onClick={() => onAsk(followup)}>{followup}<ArrowUp size={13} /></button>)}</div>}
          </article>}
        </div>

        <form className="assistant-composer" onSubmit={(event) => { event.preventDefault(); onAsk(question) }}>
          <label className="sr-only" htmlFor="assistant-question">Ask AdmitFlow a question</label>
          <textarea ref={inputRef} id="assistant-question" rows="2" maxLength="800" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about your admission data..." disabled={!configured || loading} />
          <div className="composer-footer"><span>Answers use aggregate data only</span><button className="send-button" type="submit" aria-label="Send question" disabled={!configured || loading || question.trim().length < 3}><ArrowUp size={18} /></button></div>
        </form>
      </aside>
    </div>
  )
}
