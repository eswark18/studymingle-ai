import { useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import './App.css'
import { ApiError, deleteWorksheet, getCurrentUser, logout, uploadWorksheet } from './auth'
import type { AuthMode, AuthUser, Worksheet } from './auth'
import AccountModal from './components/AccountModal'
import AuthModal from './components/AuthModal'

type Track = 'school' | 'engineering'
type Stage = 'setup' | 'questions' | 'tutor'

const schoolSubjects = ['Mathematics', 'Physics', 'Chemistry', 'Biology']
const engineeringSubjects = [
  'Engineering Mathematics',
  'Programming Fundamentals',
  'Engineering Physics',
  'Basic Electrical',
  'Engineering Mechanics',
]

const extractedQuestions = [
  {
    number: 1,
    title: 'Resolve a force into horizontal and vertical components.',
    topic: 'Vectors',
    level: 'Foundation',
  },
  {
    number: 2,
    title: 'Find the resultant of two perpendicular forces of 6 N and 8 N.',
    topic: 'Resultant force',
    level: 'Practice',
  },
  {
    number: 3,
    title: 'Explain why equilibrium requires the net force to equal zero.',
    topic: 'Equilibrium',
    level: 'Concept',
  },
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
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [activeQuestion, setActiveQuestion] = useState(2)
  const [hintCount, setHintCount] = useState(1)
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState(false)
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

  const subjects = track === 'school' ? schoolSubjects : engineeringSubjects
  const levels = track === 'school'
    ? ['Grade 6', 'Grade 7', 'Grade 8', 'Grade 9', 'Grade 10', 'Grade 11', 'Grade 12']
    : ['First year', 'Second year', 'Third year', 'Final year']

  const active = useMemo(
    () => extractedQuestions.find((question) => question.number === activeQuestion) ?? extractedQuestions[0],
    [activeQuestion],
  )

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
      setStage('questions')
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
    setSelectedFile(null)
    setFileName('')
    setStage('setup')
  }

  function openTutor(questionNumber: number) {
    setActiveQuestion(questionNumber)
    setHintCount(1)
    setAnswer('')
    setFeedback(false)
    setStage('tutor')
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
              <span>PDF, PNG, JPG · Nothing stored in this prototype</span>
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
              <span className={stage === 'questions' ? 'active' : ''}>2</span><i />
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
                  <p>This prototype uses sample extraction and tutoring responses. Your selected track shapes the learning experience.</p>
                  <div className="privacy-note"><b>Prototype boundary</b><span>Your file stays in this browser and is not uploaded.</span></div>
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
                    <div><b>{fileName || 'Choose a worksheet'}</b><span>{fileName ? 'Ready for sample extraction' : 'PDF, PNG, JPG or JPEG · maximum 10 MB'}</span></div>
                    <button type="button">Browse</button>
                  </div>
                  {uploadError && <p className="form-alert" role="alert">{uploadError}</p>}
                  <button className="primary-button full" type="button" onClick={extractQuestions} disabled={uploading}>
                    {uploading ? 'Uploading securely…' : 'Upload & extract sample questions'} {!uploading && <ArrowIcon />}
                  </button>
                </div>
              </div>
            )}

            {stage === 'questions' && (
              <div className="questions-layout">
                <div className="questions-header">
                  <div><span className="step-label">STEP 02</span><h3>Three questions found</h3><p>{fileName} · {level} · {subject}</p></div>
                  <div className="question-actions">
                    <button className="text-button" type="button" onClick={() => setStage('setup')}>← Change worksheet</button>
                    {worksheet && <button className="delete-link" type="button" onClick={removeCurrentWorksheet}>Delete stored copy</button>}
                  </div>
                </div>
                <div className="question-list">
                  {extractedQuestions.map((question) => (
                    <button key={question.number} type="button" onClick={() => openTutor(question.number)}>
                      <span className="question-number">0{question.number}</span>
                      <span className="question-copy"><b>{question.title}</b><small>{question.topic} · {question.level}</small></span>
                      <span className="round-arrow"><ArrowIcon /></span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {stage === 'tutor' && (
              <div className="tutor-layout">
                <aside className="question-sidebar">
                  <button className="text-button" type="button" onClick={() => setStage('questions')}>← All questions</button>
                  <span className="step-label">QUESTION 0{active.number}</span>
                  <h3>{active.title}</h3>
                  <div className="topic-row"><span>{active.topic}</span><span>{active.level}</span></div>
                  <div className="diagram-card">
                    <b>Force diagram</b>
                    <div className="vector-sketch"><i className="axis-x" /><i className="axis-y" /><i className="vector" /><span>10 N</span></div>
                  </div>
                  <p className="integrity-note"><b>Learning mode</b> StudyMingle reveals the method progressively and asks you to attempt each step.</p>
                </aside>
                <div className="tutor-panel">
                  <div className="tutor-heading"><div className="avatar"><SparkIcon /></div><div><b>Study coach</b><span>Guiding, not completing</span></div><span className="online">Online</span></div>
                  <div className="conversation" aria-live="polite">
                    <div className="coach-message"><b>Let’s start with what you know.</b><p>Two perpendicular forces form a right-angled triangle. Which theorem connects the three side lengths?</p></div>
                    {hintCount > 1 && <div className="hint-message"><span>HINT 02</span><p>Write the relationship as R² = 6² + 8², then simplify each square.</p></div>}
                    {hintCount > 2 && <div className="hint-message"><span>HINT 03</span><p>36 + 64 = 100. What positive number has a square of 100?</p></div>}
                    {feedback && <div className="success-message"><b>Strong attempt.</b><p>You identified the Pythagorean relationship and reached the correct magnitude: 10 N. Next, explain why direction also matters for a complete vector answer.</p></div>}
                  </div>
                  <div className="answer-box">
                    <label htmlFor="student-answer">Your working or answer</label>
                    <textarea id="student-answer" value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Explain your reasoning here…" />
                    <div>
                      <button className="hint-button" type="button" onClick={() => setHintCount((count) => Math.min(3, count + 1))} disabled={hintCount === 3}>Reveal next hint</button>
                      <button className="primary-button compact" type="button" onClick={() => setFeedback(true)} disabled={answer.trim().length < 4}>Check my attempt <ArrowIcon /></button>
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
