import React, { useState, useEffect } from 'react'
import {
  FaLightbulb, FaSpinner, FaRedo, FaCheck, FaTimes,
  FaArrowLeft, FaArrowRight, FaEye, FaPlus, FaDatabase, FaRandom
} from 'react-icons/fa'
import { getFlashcards, generateMoreFlashcards, getFlashcardPool } from '../utils/api'
import './Flashcards.css'

function Flashcards() {
  const [numCards, setNumCards] = useState(6)
  const [cards, setCards] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [showHint, setShowHint] = useState(false)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)
  const [results, setResults] = useState({ known: 0, unknown: 0 })
  const [isStudying, setIsStudying] = useState(false)
  const [poolInfo, setPoolInfo] = useState(null)

  // Load pool info on mount
  useEffect(() => {
    loadPoolInfo()
  }, [])

  const loadPoolInfo = async () => {
    try {
      const data = await getFlashcardPool()
      setPoolInfo(data)
    } catch (e) {
      console.error('Failed to load pool info:', e)
    }
  }

  const handleStart = async () => {
    setLoading(true)
    setError(null)
    setCards([])
    setResults({ known: 0, unknown: 0 })

    try {
      const data = await getFlashcards(numCards)
      if (data.flashcards?.length > 0) {
        setCards(data.flashcards)
        setCurrentIndex(0)
        setFlipped(false)
        setShowHint(false)
        setIsStudying(true)
        setPoolInfo(prev => ({ ...prev, pool_size: data.pool_size }))
      } else {
        setError('Няма флашкарти в пула. Натисни "Генерирай нови" за да създадеш.')
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Грешка при зареждане')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateMore = async () => {
    setGenerating(true)
    setError(null)
    try {
      const data = await generateMoreFlashcards(10)
      await loadPoolInfo()
      setError(null)
      alert(`✅ ${data.message}`)
    } catch (e) {
      setError(e.response?.data?.detail || 'Грешка при генериране')
    } finally {
      setGenerating(false)
    }
  }

  const handleFlip = () => {
    setFlipped(!flipped)
    setShowHint(false)
  }

  const handleKnow = () => {
    setResults(r => ({ ...r, known: r.known + 1 }))
    nextCard()
  }

  const handleDontKnow = () => {
    setResults(r => ({ ...r, unknown: r.unknown + 1 }))
    nextCard()
  }

  const nextCard = () => {
    setFlipped(false)
    setShowHint(false)
    if (currentIndex < cards.length - 1) {
      setCurrentIndex(currentIndex + 1)
    } else {
      setIsStudying(false)
    }
  }

  const prevCard = () => {
    if (currentIndex > 0) {
      setFlipped(false)
      setShowHint(false)
      setCurrentIndex(currentIndex - 1)
    }
  }

  const restart = () => {
    setCurrentIndex(0)
    setFlipped(false)
    setShowHint(false)
    setResults({ known: 0, unknown: 0 })
    setIsStudying(true)
  }

  const shuffleAndRestart = async () => {
    await handleStart()
  }

  const currentCard = cards[currentIndex]
  const progress = cards.length > 0 ? ((currentIndex + 1) / cards.length) * 100 : 0
  const totalAnswered = results.known + results.unknown

  // ── Results Screen ──
  if (cards.length > 0 && !isStudying) {
    const score = totalAnswered > 0 ? Math.round((results.known / totalAnswered) * 100) : 0
    return (
      <div className="flashcards-container">
        <div className="results-screen fade-in">
          <div className="results-emoji">
            {score >= 80 ? '🏆' : score >= 50 ? '👍' : '📚'}
          </div>
          <h2 className="results-title">
            {score >= 80 ? 'Отлично!' : score >= 50 ? 'Добре!' : 'Продължавай да учиш!'}
          </h2>
          <div className="results-score">
            <div className="score-circle">
              <span className="score-number">{score}%</span>
              <span className="score-label">верни</span>
            </div>
          </div>
          <div className="results-stats">
            <div className="stat-item known">
              <FaCheck />
              <span>{results.known} знам</span>
            </div>
            <div className="stat-item unknown">
              <FaTimes />
              <span>{results.unknown} не знам</span>
            </div>
          </div>
          <div className="results-actions">
            <button className="action-btn restart" onClick={restart}>
              <FaRedo /> Отново (същите)
            </button>
            <button className="action-btn shuffle" onClick={shuffleAndRestart}>
              <FaRandom /> Нови карти
            </button>
            <button className="action-btn new" onClick={() => { setCards([]); setIsStudying(false) }}>
              <FaArrowLeft /> Начало
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Setup Screen ──
  if (cards.length === 0) {
    return (
      <div className="flashcards-container">
        <div className="flashcards-header">
          <div className="flashcards-header-icon">
            <FaLightbulb />
          </div>
          <div>
            <h2>Флашкарти</h2>
            <p className="flashcards-subtitle">Учи с въпроси от учебния материал</p>
          </div>
        </div>

        {/* Pool Status */}
        <div className="pool-status">
          <div className="pool-info">
            <FaDatabase className="pool-icon" />
            <div className="pool-text">
              <span className="pool-count">{poolInfo?.pool_size || 0} карти в пула</span>
              {poolInfo?.categories?.length > 0 && (
                <span className="pool-categories">
                  {poolInfo.categories.map(c => `${c.category} (${c.count})`).join(' · ')}
                </span>
              )}
            </div>
          </div>
          <button
            className="generate-pool-btn"
            onClick={handleGenerateMore}
            disabled={generating}
          >
            {generating ? (
              <><FaSpinner className="spin" /> Генериране...</>
            ) : (
              <><FaPlus /> Генерирай нови</>
            )}
          </button>
        </div>

        <div className="flashcards-setup">
          <div className="setup-field">
            <label>Брой карти:</label>
            <div className="cards-count-selector">
              {[4, 6, 8, 10, 15].map(n => (
                <button
                  key={n}
                  className={`count-btn ${numCards === n ? 'active' : ''}`}
                  onClick={() => setNumCards(n)}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          <button className="start-btn" onClick={handleStart} disabled={loading}>
            {loading ? (
              <><FaSpinner className="spin" /> Зареждане...</>
            ) : (
              <><FaLightbulb /> Започни</>
            )}
          </button>

          {error && <div className="flashcards-error">⚠️ {error}</div>}
        </div>

        {/* How it works */}
        <div className="how-it-works">
          <h3>Как работи?</h3>
          <div className="how-steps">
            <div className="how-step">
              <span className="step-num">1</span>
              <span>Въпросите се извличат от генерираните тестове</span>
            </div>
            <div className="how-step">
              <span className="step-num">2</span>
              <span>Натисни картата за да видиш отговора</span>
            </div>
            <div className="how-step">
              <span className="step-num">3</span>
              <span>Оцени знанието си: "Знам" или "Не знам"</span>
            </div>
            <div className="how-step">
              <span className="step-num">4</span>
              <span>Генерирай нови карти за повече въпроси</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Study Screen ──
  return (
    <div className="flashcards-container">
      <div className="study-header">
        <div className="progress-info">
          <span className="progress-text">{currentIndex + 1} / {cards.length}</span>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="progress-score">
            <span className="score-known">✓ {results.known}</span>
            <span className="score-unknown">✗ {results.unknown}</span>
          </div>
        </div>
      </div>

      <div className="card-wrapper" onClick={handleFlip}>
        <div className={`flashcard ${flipped ? 'flipped' : ''}`}>
          <div className="card-front">
            <div className="card-label">❓ Въпрос</div>
            <p className="card-text">{currentCard?.front}</p>
            {currentCard?.section && (
              <div className="card-source-front">
                📖 {currentCard.section}
              </div>
            )}
            <p className="card-tap-hint">Натисни за отговор →</p>
          </div>
          <div className="card-back">
            <div className="card-label">💡 Отговор</div>
            <div className="card-answer">
              {currentCard?.back?.split('\n').map((line, i) => (
                <p key={i} className={
                  line.startsWith('✅') ? 'answer-correct' :
                  line.startsWith('📝') ? 'answer-explanation' :
                  line.startsWith('🔑') ? 'answer-keypoints' :
                  line.startsWith('•') ? 'answer-point' : ''
                }>{line}</p>
              ))}
            </div>
            {currentCard?.page > 0 && (
              <div className="card-source">
                📄 Стр. {currentCard.page}
                {currentCard.section && ` · ${currentCard.section}`}
              </div>
            )}
          </div>
        </div>
      </div>

      {!flipped && currentCard?.hint && (
        <div className="hint-area">
          {showHint ? (
            <p className="hint-text fade-in">💡 {currentCard.hint}</p>
          ) : (
            <button className="hint-btn" onClick={(e) => { e.stopPropagation(); setShowHint(true) }}>
              <FaEye /> Покажи подсказка
            </button>
          )}
        </div>
      )}

      {flipped && (
        <div className="card-actions fade-in">
          <button className="card-action-btn dont-know" onClick={handleDontKnow}>
            <FaTimes /> Не знам
          </button>
          <button className="card-action-btn know" onClick={handleKnow}>
            <FaCheck /> Знам
          </button>
        </div>
      )}

      <div className="nav-arrows">
        <button className="nav-arrow" onClick={prevCard} disabled={currentIndex === 0}>
          <FaArrowLeft />
        </button>
        <button className="nav-arrow" onClick={nextCard} disabled={currentIndex === cards.length - 1}>
          <FaArrowRight />
        </button>
      </div>
    </div>
  )
}

export default Flashcards
