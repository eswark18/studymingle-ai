import { useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import './App.css'
import {
  ApiError,
  deleteWorksheet,
  getCurrentUser,
  getQuestionExtraction,
  logout,
  retryQuestionExtraction,
  requestTutorHint,
  startQuestionExtraction,
  startTutorSession,
  submitTutorAttempt,
  updateExtractedQuestion,
  uploadWorksheet,
} from './auth'
import type {
  AuthMode,
  AuthUser,
  ExtractedQuestion,
  OcrJob,
  TutorAttempt,
  TutorHint,
  TutorSession,
  Worksheet,
} from './auth'
import AccountModal from './components/AccountModal'
import AuthModal from './components/AuthModal'

type Track = 'school' | 'engineering'
type Stage = 'setup' | 'processing' | 'questions' | 'tutor'
type TutorConversationEvent =
  | { kind: 'hint'; createdAt: string; value: TutorHint }
  | { kind: 'attempt'; createdAt: string; value: TutorAttempt }

const schoolSubjects = ['Mathematics', 'Physics', 'Chemistry', 'Biology']
const engineeringSubjects = [
  'Engineering Mathematics',
  'Programming Fundamentals',
  'Engineering Physics',
  'Basic Electrical',
  'Engineering Mechanics',
]

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h13M13 6l6 6-6 6" />
    </svg>
  )
}

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2l1.5 5.1L18 9l-4.5 1.9L12 16l-1.5-5.1L6 9l4.5-1.9L12 2Z" />
      <path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z" />
    </svg>
  )
}

function App() {
  const [track, setTrack] = useState<Track>('engineering')
  const [level, setLevel] = useState('First year')
  const [subject, setSubject] = useState('Engineering Mechanics')
  const [stage, setStage] = useState<Stage>('setup')
  const [fileName, setFileName] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [worksheet, setWorksheet] = useState<Worksheet | null>(null)
  const [ocrJob, setOcrJob] = useState<OcrJob | null>(null)
  const [questions, setQuestions] = useState<ExtractedQuestion[]>([])
  const [questionDrafts, setQuestionDrafts] = useState<Record<string, string>>({})
  const [savingQuestion, setSavingQuestion] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [activeQuestion, setActiveQuestion] = useState<string | null>(null)
  const [answer, setAnswer] = useState('')
  const [tutorSession, setTutorSession] = useState<TutorSession | null>(null)
  const [tutorLoading, setTutorLoading] = useState(false)
  const [tutorError, setTutorError] = useState('')
  const [user, setUser] = useState<AuthUser | null>(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [authMode, setAuthMode] = useState<AuthMode | null>(null)
  const [accountOpen, setAccountOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch((error) => {
        if (!(error instanceof ApiError) || error.status !== 401) {
          console.error('Unable to restore the StudyMingle session.', error)
        }
      })
      .finally(() => setAuthLoading(false))
  }, [])

  useEffect(() => {
    if (!ocrJob || !['queued', 'retrying', 'processing'].includes(ocrJob.status)) return
    let cancelled = false
    const timer = window.setTimeout(async () => {
      try {
        const latest = await getQuestionExtraction(ocrJob.id)
        if (cancelled) return
        setOcrJob(latest)
        if (latest.status === 'completed') {
          setQuestions(latest.questions)
          setQuestionDrafts(Object.fromEntries(latest.questions.map((item) => [item.id, item.edited_text ?? item.extracted_text])))
          setActiveQuestion(latest.questions[0]?.id ?? null)
          setStage('questions')
        }
      } catch (error) {
        if (!cancelled) setUploadError(error instanceof Error ? error.message : 'Question extraction failed.')
      }
    }, 1200)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [ocrJob])

  const subjects = track === 'school' ? schoolSubjects : engineeringSubjects
  const levels = track === 'school'
    ? ['Grade 6', 'Grade 7', 'Grade 8', 'Grade 9', 'Grade 10', 'Grade 11', 'Grade 12']
    : ['First year', 'Second year', 'Third year', 'Final year']

  const active = useMemo(
    () => questions.find((question) => question.id === activeQuestion) ?? questions[0],
    [activeQuestion, questions],
  )

  const tutorConversation = useMemo<TutorConversationEvent[]>(() => {
    if (!tutorSession) return []
    return [
      ...tutorSession.hints.map((hint) => ({
        kind: 'hint' as const,
        createdAt: hint.created_at,
        value: hint,
      })),
      ...tutorSession.attempts.map((attempt) => ({
        kind: 'attempt' as const,
        createdAt: attempt.created_at,
        value: attempt,
      })),
    ].sort((left, right) => left.createdAt.localeCompare(right.createdAt))
  }, [tutorSession])

  function switchTrack(nextTrack: Track) {
    setTrack(nextTrack)
    setLevel(nextTrack === 'school' ? 'Grade 10' : 'First year')
    setSubject(nextTrack === 'school' ? 'Mathematics' : 'Engineering Mechanics')
  }

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    if (file.size > 10 * 1024 * 1024) {
      setUploadError('Choose a worksheet smaller than 10 MB.')
      event.target.value = ''
      return
    }
    setSelectedFile(file)
    setFileName(file.name)
    setUploadError('')
  }

  async function extractQuestions() {
    if (!selectedFile) {
      setUploadError('Choose a PDF, PNG, or JPEG worksheet first.')
      return
    }
    setUploading(true)
    setUploadError('')
    try {
      const uploaded = await uploadWorksheet(selectedFile)
      setWorksheet(uploaded)
      const job = await startQuestionExtraction(uploaded.id)
      setOcrJob(job)
      setStage('processing')
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Worksheet upload failed.')
    } finally {
      setUploading(false)
    }
  }

  async function removeCurrentWorksheet() {
    if (!worksheet) return
    await deleteWorksheet(worksheet.id)
    setWorksheet(null)
    setOcrJob(null)
    setQuestions([])
    setQuestionDrafts({})
    setSelectedFile(null)
    setFileName('')
    setStage('setup')
  }

  async function retryExtraction() {
    if (!ocrJob) return
    setUploadError('')
    try {
      const retried = await retryQuestionExtraction(ocrJob.id)
      setOcrJob(retried)
      setStage('processing')
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Question extraction could not be retried.')
    }
  }

  async function saveQuestion(question: ExtractedQuestion) {
    const editedText = questionDrafts[question.id]?.trim()
    if (!editedText || editedText.length < 3) return
    setSavingQuestion(question.id)
    try {
      const updated = await updateExtractedQuestion(question.id, editedText)
      setQuestions((items) => items.map((item) => item.id === updated.id ? updated : item))
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'The question could not be saved.')
    } finally {
      setSavingQuestion(null)
    }
  }

  async function openTutor(questionId: string) {
    setActiveQuestion(questionId)
    setAnswer('')
    setTutorSession(null)
    setTutorError('')
    setStage('tutor')
    setTutorLoading(true)
    try {
      const session = await startTutorSession(questionId, {
        education_track: track,
        grade_or_year: level,
        subject,
      })
      setTutorSession(session)
    } catch (error) {
      setTutorError(error instanceof Error ? error.message : 'The study coach could not start.')
    } finally {
      setTutorLoading(false)
    }
  }

  async function revealHint() {
    if (!tutorSession || tutorLoading) return
    setTutorLoading(true)
    setTutorError('')
    try {
      setTutorSession(await requestTutorHint(tutorSession.id))
    } catch (error) {
      setTutorError(error instanceof Error ? error.message : 'The next hint could not be loaded.')
    } finally {
      setTutorLoading(false)
    }
  }

  async function checkAttempt() {
    if (!tutorSession || answer.trim().length < 3 || tutorLoading) return
    setTutorLoading(true)
    setTutorError('')
    try {
      setTutorSession(await submitTutorAttempt(tutorSession.id, answer))
      setAnswer('')
    } catch (error) {
      setTutorError(error instanceof Error ? error.message : 'Your attempt could not be checked.')
    } finally {
      setTutorLoading(false)
    }
  }

  async function signOut() {
    try {
      await logout()
    } finally {
      setUser(null)
      setAccountOpen(false)
      setStage('setup')
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="StudyMingle home">
          <span className="brand-mark"><SparkIcon /></span>
          <span>Study<span>Mingle</span></span>
          <small>AI</small>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#workspace">Workspace</a>
          <a href="#how-it-works">How it works</a>
          <a href="#principles">Learning principles</a>
        </nav>
        <div className="account-actions">
          {authLoading ? (
            <span className="session-loading">Checking session…</span>
          ) : user ? (
            <>
              <button className="user-button" type="button" onClick={() => setAccountOpen(true)}>
                <span>{(user.display_name ?? user.email).slice(0, 1).toUpperCase()}</span>
                {user.display_name ?? user.email}
              </button>
              <button className="quiet-button" type="button" onClick={signOut}>Sign out</button>
            </>
          ) : (
            <>
              <button className="quiet-button" type="button" onClick={() => setAuthMode('login')}>Sign in</button>
              <button className="header-cta" type="button" onClick={() => setAuthMode('register')}>Create account</button>
            </>
          )}
        </div>
      </header>

      <main id="top">
        <section className="hero-section">
          <div className="hero-copy">
            <div className="eyebrow"><span /> Guided learning for school & engineering</div>
            <h1>Understand the method.<br /><em>Own the answer.</em></h1>
            <p>
              Upload a worksheet, choose a question, and work through it with progressive hints,
              visual explanations, and feedback on your own attempt.
            </p>
            <div className="hero-actions">
              <button className="primary-button" type="button" onClick={() => document.querySelector('#workspace')?.scrollIntoView({ behavior: 'smooth' })}>
                Try the learning workspace <ArrowIcon />
              </button>
              <span>PDF, PNG, JPG · Private storage with deletion controls</span>
            </div>
          </div>
          <div className="concept-card" aria-label="Example guided learning conversation">
            <div className="concept-topline"><span>LIVE LEARNING FLOW</span><b>Question 2 of 3</b></div>
            <div className="mini-diagram">
              <span className="force horizontal">6 N</span>
              <span className="force vertical">8 N</span>
              <span className="force resultant">?</span>
              <i className="origin" />
            </div>
            <div className="tutor-bubble"><SparkIcon /><p>What shape do the two perpendicular forces make?</p></div>
            <div className="student-bubble">A right-angled triangle.</div>
            <div className="progress-line"><span style={{ width: '58%' }} /></div>
            <small>Good. Now choose the relationship between all three sides.</small>
          </div>
        </section>

        <section className="trust-strip" aria-label="Product principles">
          <span>01 <b>Attempt first</b></span>
          <span>02 <b>Hints before solutions</b></span>
          <span>03 <b>Feedback that explains why</b></span>
          <span>04 <b>Practice for real understanding</b></span>
        </section>

        <section className="workspace-section" id="workspace">
          <div className="section-heading">
            <div>
              <span className="kicker">INTERACTIVE PROTOTYPE</span>
              <h2>Your guided learning workspace</h2>
            </div>
            <div className="stage-indicator" aria-label={`Current stage: ${stage}`}>
              <span className={stage === 'setup' ? 'active' : ''}>1</span><i />
              <span className={stage === 'processing' || stage === 'questions' ? 'active' : ''}>2</span><i />
              <span className={stage === 'tutor' ? 'active' : ''}>3</span>
            </div>
          </div>

          {authLoading ? (
            <div className="workspace-card auth-gate" aria-live="polite">
              <div className="auth-gate-mark"><SparkIcon /></div>
              <span className="kicker">RESTORING YOUR SESSION</span>
              <h3>Preparing your learning workspace…</h3>
            </div>
          ) : !user ? (
            <div className="workspace-card auth-gate">
              <div className="auth-gate-mark"><SparkIcon /></div>
              <span className="kicker">PRIVATE LEARNING WORKSPACE</span>
              <h3>Sign in to begin your guided session</h3>
              <p>Your account keeps worksheets, learning preferences, attempts, and future tutor history attached only to you.</p>
              <div>
                <button className="primary-button" type="button" onClick={() => setAuthMode('register')}>Create free account <ArrowIcon /></button>
                <button className="secondary-button" type="button" onClick={() => setAuthMode('login')}>I already have an account</button>
              </div>
              <small>Secure HTTP-only sessions · Privacy controls · Delete your account anytime</small>
            </div>
          ) : (
          <div className="workspace-card">
            {stage === 'setup' && (
              <div className="setup-layout">
                <aside className="setup-intro">
                  <span className="step-label">STEP 01</span>
                  <h3>Tell us what you’re learning</h3>
                  <p>Your worksheet is uploaded privately and processed to find reviewable questions. Your selected track shapes the learning experience.</p>
                  <div className="privacy-note"><b>Private by design</b><span>Only your account can access or delete the original worksheet and extracted questions.</span></div>
                </aside>
                <div className="setup-form">
                  <fieldset>
                    <legend>Learning track</legend>
                    <div className="segmented-control">
                      <button className={track === 'school' ? 'selected' : ''} onClick={() => switchTrack('school')} type="button">
                        <b>School</b><span>Grades 6–12</span>
                      </button>
                      <button className={track === 'engineering' ? 'selected' : ''} onClick={() => switchTrack('engineering')} type="button">
                        <b>Engineering</b><span>University</span>
                      </button>
                    </div>
                  </fieldset>
                  <div className="select-grid">
                    <label><span>{track === 'school' ? 'Grade' : 'Year'}</span><select value={level} onChange={(event) => setLevel(event.target.value)}>{levels.map((item) => <option key={item}>{item}</option>)}</select></label>
                    <label><span>Subject</span><select value={subject} onChange={(event) => setSubject(event.target.value)}>{subjects.map((item) => <option key={item}>{item}</option>)}</select></label>
                  </div>
                  <div className="upload-zone" onClick={() => inputRef.current?.click()}>
                    <input ref={inputRef} type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={handleFile} />
                    <span className="upload-icon">↑</span>
                    <div><b>{fileName || 'Choose a worksheet'}</b><span>{fileName ? 'Ready for secure extraction' : 'PDF, PNG, JPG or JPEG · maximum 10 MB'}</span></div>
                    <button type="button">Browse</button>
                  </div>
                  {uploadError && <p className="form-alert" role="alert">{uploadError}</p>}
                  <button className="primary-button full" type="button" onClick={extractQuestions} disabled={uploading}>
                    {uploading ? 'Uploading securely…' : 'Upload & extract questions'} {!uploading && <ArrowIcon />}
                  </button>
                </div>
              </div>
            )}

            {stage === 'processing' && (
              <div className="processing-layout" aria-live="polite">
                <div className="processing-spinner" aria-hidden="true" />
                <span className="step-label">STEP 02 · OCR</span>
                <h3>{ocrJob?.status === 'failed' ? 'We could not read this worksheet' : 'Finding questions in your worksheet…'}</h3>
                <p>{ocrJob?.status === 'failed' ? ocrJob.error_message : 'We try native PDF text first, then use image OCR when needed.'}</p>
                {ocrJob?.status === 'failed' && <button className="primary-button" type="button" onClick={retryExtraction}>Try extraction again <ArrowIcon /></button>}
                {uploadError && <p className="form-alert" role="alert">{uploadError}</p>}
              </div>
            )}

            {stage === 'questions' && (
              <div className="questions-layout">
                <div className="questions-header">
                  <div><span className="step-label">STEP 02</span><h3>{questions.length} question{questions.length === 1 ? '' : 's'} found</h3><p>{fileName} · {level} · {subject} · Review before tutoring</p></div>
                  <div className="question-actions">
                    <button className="text-button" type="button" onClick={() => setStage('setup')}>← Change worksheet</button>
                    {worksheet && <button className="delete-link" type="button" onClick={removeCurrentWorksheet}>Delete stored copy</button>}
                  </div>
                </div>
                {uploadError && <p className="form-alert" role="alert">{uploadError}</p>}
                <div className="question-list">
                  {questions.map((question) => (
                    <article key={question.id} className="question-review-card">
                      <span className="question-number">{String(question.question_number).padStart(2, '0')}</span>
                      <label className="question-copy">
                        <span className="sr-only">Review question {question.question_number}</span>
                        <textarea value={questionDrafts[question.id] ?? ''} onChange={(event) => setQuestionDrafts((items) => ({ ...items, [question.id]: event.target.value }))} />
                        <small>{question.page_number ? `Page ${question.page_number} · ` : ''}{question.confidence === null ? 'Native text' : `${Math.round(question.confidence * 100)}% OCR confidence`}</small>
                      </label>
                      <div className="review-actions">
                        <button type="button" onClick={() => saveQuestion(question)} disabled={savingQuestion === question.id}>{savingQuestion === question.id ? 'Saving…' : 'Save edit'}</button>
                        <button className="round-arrow" type="button" aria-label={`Open tutor for question ${question.question_number}`} onClick={() => openTutor(question.id)}><ArrowIcon /></button>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            )}

            {stage === 'tutor' && (
              <div className="tutor-layout">
                <aside className="question-sidebar">
                  <button className="text-button" type="button" onClick={() => setStage('questions')}>← All questions</button>
                  <span className="step-label">QUESTION {String(active?.question_number ?? 1).padStart(2, '0')}</span>
                  <h3>{active?.edited_text ?? active?.extracted_text}</h3>
                  <div className="topic-row"><span>{subject}</span><span>{level}</span></div>
                  <div className="diagram-card">
                    <b>Force diagram</b>
                    <div className="vector-sketch"><i className="axis-x" /><i className="axis-y" /><i className="vector" /><span>10 N</span></div>
                  </div>
                  <p className="integrity-note"><b>Learning mode</b> StudyMingle reveals the method progressively and asks you to attempt each step.</p>
                </aside>
                <div className="tutor-panel">
                  <div className="tutor-heading"><div className="avatar"><SparkIcon /></div><div><b>Study coach</b><span>Guiding, not completing</span></div><span className="online">Online</span></div>
                  <div className="conversation" aria-live="polite">
                    {tutorLoading && !tutorSession && <div className="coach-message"><b>Preparing your first step…</b><p>The local open-source tutor is reading the reviewed question.</p></div>}
                    {tutorConversation.map((event) => {
                      if (event.kind === 'hint') {
                        const hint = event.value
                        return (
                          <div className={hint.sequence_number === 1 ? 'coach-message' : 'hint-message'} key={`hint-${hint.id}`}>
                            {hint.sequence_number === 1 ? <b>Let’s start with what you know.</b> : <span>HINT {String(hint.sequence_number).padStart(2, '0')}</span>}
                            <p>{hint.hint_text}</p>
                          </div>
                        )
                      }
                      const attempt = event.value
                      return (
                        <div className={attempt.is_correct ? 'success-message' : 'coach-message'} key={`attempt-${attempt.id}`}>
                          <b>{attempt.is_correct ? 'Strong attempt.' : 'Feedback on your attempt.'}</b>
                          <blockquote className="student-attempt">You wrote: “{attempt.attempt_text}”</blockquote>
                          <p>{attempt.feedback_text}</p>
                        </div>
                      )
                    })}
                    {tutorError && <p className="form-alert" role="alert">{tutorError}</p>}
                  </div>
                  <div className="answer-box">
                    <label htmlFor="student-answer">Your working or answer</label>
                    <textarea id="student-answer" value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Explain your reasoning here…" />
                    <div>
                      <button className="hint-button" type="button" onClick={revealHint} disabled={!tutorSession?.can_request_hint || tutorLoading}>{tutorLoading ? 'Coach is thinking…' : 'Reveal next hint'}</button>
                      <button className="primary-button compact" type="button" onClick={checkAttempt} disabled={!tutorSession || tutorSession.status === 'completed' || answer.trim().length < 3 || tutorLoading}>Check my attempt <ArrowIcon /></button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
          )}
        </section>

        <section className="how-section" id="how-it-works">
          <div className="section-heading simple"><div><span className="kicker">BUILT AROUND LEARNING</span><h2>From worksheet to understanding</h2></div></div>
          <div className="feature-grid">
            <article><span>01</span><div className="feature-icon">⌁</div><h3>Bring the question</h3><p>Upload a worksheet or image and review the extracted questions before learning begins.</p></article>
            <article><span>02</span><div className="feature-icon">✦</div><h3>Think with support</h3><p>Use progressive hints, diagrams, and short guiding questions instead of instant solutions.</p></article>
            <article><span>03</span><div className="feature-icon">✓</div><h3>Prove the learning</h3><p>Submit your reasoning, receive feedback, and try a similar practice question.</p></article>
          </div>
        </section>

        <section className="principles-section" id="principles">
          <span className="kicker">THE STUDYMINGLE PROMISE</span>
          <blockquote>“AI should make the learner’s thinking <em>stronger</em>—not replace it.”</blockquote>
          <div><span>Age-aware guidance</span><span>No permanent uploads</span><span>Honest uncertainty</span><span>Practice over shortcuts</span></div>
        </section>
      </main>
      {authMode && (
        <AuthModal
          initialMode={authMode}
          onClose={() => setAuthMode(null)}
          onAuthenticated={(authenticatedUser) => {
            setUser(authenticatedUser)
            setAuthMode(null)
            document.querySelector('#workspace')?.scrollIntoView({ behavior: 'smooth' })
          }}
        />
      )}
      {accountOpen && user && (
        <AccountModal
          user={user}
          onClose={() => setAccountOpen(false)}
          onDeleted={() => {
            setUser(null)
            setAccountOpen(false)
            setStage('setup')
          }}
        />
      )}

      <footer><a className="brand" href="#top"><span className="brand-mark"><SparkIcon /></span><span>Study<span>Mingle</span></span></a><p>A ThoughtMingle learning prototype · Grades 6–12 & engineering</p><span>Frontend prototype · v0.1</span></footer>
    </div>
  )
}

export default App
